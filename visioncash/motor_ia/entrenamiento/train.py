"""
Entrenamiento OPTIMIZADO al máximo para clasificación de billetes colombianos.
═══════════════════════════════════════════════════════════════════════════════
Hardware objetivo : RTX 5060 Ti (CUDA 12.8) | Ryzen 5 5600 | 32 GB RAM
Framework         : PyTorch 2.11 + torchvision (GPU funcional en Windows)
Arquitectura      : EfficientNetV2-S preentrenado en ImageNet-21k (torchvision)
Técnicas          :
  · Mixed Precision (torch.amp BF16/FP16) → hasta 2× velocidad en RTX
  · FASE 1 – Transfer Learning: solo cabeza, 20 épocas, lr=1e-3
  · FASE 2 – Fine-Tuning total: todas las capas, 40 épocas, lr=5e-5
  · Cosine Annealing LR con warm-up
  · Label Smoothing (0.1)
  · Mixup augmentation en training
  · Gradient clipping (max_norm=1.0)
  · Mejor modelo guardado automáticamente por val_accuracy
  · Estadísticas de entrenamiento exportadas a JSON
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import shutil
import random
import numpy as np
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, random_split
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
import torchvision
from torchvision import datasets, transforms
from torchvision.models import efficientnet_v2_s, EfficientNet_V2_S_Weights

# ─── Metadatos de billetes colombianos ─────────────────────────────────────
BANKNOTE_METADATA = {
    "2.000":   {"denomination": "$2.000 COP",   "character": "Débora Arango",            "color": "#3b82f6"},
    "5.000":   {"denomination": "$5.000 COP",   "character": "José Asunción Silva",      "color": "#9333ea"},
    "10.000":  {"denomination": "$10.000 COP",  "character": "Virginia Gutiérrez",       "color": "#ea580c"},
    "20.000":  {"denomination": "$20.000 COP",  "character": "Alfonso López Michelsen",  "color": "#0d9488"},
    "50000":   {"denomination": "$50.000 COP",  "character": "Gabriel García Márquez",   "color": "#2563eb"},
    "50.000":  {"denomination": "$50.000 COP",  "character": "Gabriel García Márquez",   "color": "#2563eb"},
    "100.000": {"denomination": "$100.000 COP", "character": "Carlos Lleras Restrepo",   "color": "#16a34a"},
}

# ─── Semillas ───────────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.backends.cudnn.benchmark = True   # acelera convoluciones en RTX


# ═══════════════════════════════════════════════════════════════════════════
# Modelo
# ═══════════════════════════════════════════════════════════════════════════

def build_model(num_classes: int, freeze_backbone: bool = True):
    """
    EfficientNetV2-S con cabeza personalizada.
    - freeze_backbone=True  → FASE 1 (solo entrena la cabeza)
    - freeze_backbone=False → FASE 2 (fine-tuning completo)
    """
    model = efficientnet_v2_s(weights=EfficientNet_V2_S_Weights.IMAGENET1K_V1)

    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False

    # Reemplazar clasificador final
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.35, inplace=True),
        nn.Linear(in_features, 512),
        nn.SiLU(),
        nn.Dropout(p=0.25),
        nn.Linear(512, num_classes),
    )
    return model


def unfreeze_top_layers(model, n_blocks_to_unfreeze: int = 4):
    """Descongela las últimas N capas del backbone para fine-tuning."""
    for param in model.parameters():
        param.requires_grad = False
    # Siempre entrenar la cabeza
    for param in model.classifier.parameters():
        param.requires_grad = True
    # Descongelar bloques finales del encoder
    blocks = list(model.features.children())
    for block in blocks[-n_blocks_to_unfreeze:]:
        for param in block.parameters():
            param.requires_grad = True


# ═══════════════════════════════════════════════════════════════════════════
# Mixup augmentation
# ═══════════════════════════════════════════════════════════════════════════

def mixup_data(x, y, alpha=0.3):
    if alpha <= 0:
        return x, y, y, 1.0
    lam = np.random.beta(alpha, alpha)
    batch_size = x.size(0)
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


# ═══════════════════════════════════════════════════════════════════════════
# Warm-up scheduler
# ═══════════════════════════════════════════════════════════════════════════

def get_scheduler(optimizer, warmup_epochs: int, total_epochs: int):
    def lr_lambda(epoch):
        if epoch < warmup_epochs:
            return float(epoch + 1) / float(warmup_epochs)
        progress = (epoch - warmup_epochs) / (total_epochs - warmup_epochs)
        return 0.5 * (1.0 + np.cos(np.pi * progress))
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


# ═══════════════════════════════════════════════════════════════════════════
# Loop de entrenamiento
# ═══════════════════════════════════════════════════════════════════════════

def train_epoch(model, loader, optimizer, criterion, scaler, device, use_mixup=True):
    model.train()
    running_loss, correct, total = 0.0, 0, 0
    for imgs, labels in loader:
        imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)

        if use_mixup:
            imgs, y_a, y_b, lam = mixup_data(imgs, labels)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type='cuda', dtype=torch.bfloat16):
            logits = model(imgs)
            if use_mixup:
                loss = mixup_criterion(criterion, logits, y_a, y_b, lam)
            else:
                loss = criterion(logits, labels)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item() * imgs.size(0)
        preds = logits.argmax(dim=1)
        if use_mixup:
            correct += (lam * (preds == y_a).float() + (1 - lam) * (preds == y_b).float()).sum().item()
        else:
            correct += (preds == labels).sum().item()
        total += imgs.size(0)

    return running_loss / total, correct / total


@torch.no_grad()
def eval_epoch(model, loader, criterion, device):
    model.eval()
    running_loss, correct, total = 0.0, 0, 0
    for imgs, labels in loader:
        imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
        with torch.amp.autocast(device_type='cuda', dtype=torch.bfloat16):
            logits = model(imgs)
            loss   = criterion(logits, labels)
        running_loss += loss.item() * imgs.size(0)
        correct += (logits.argmax(1) == labels).sum().item()
        total   += imgs.size(0)
    return running_loss / total, correct / total


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline principal
# ═══════════════════════════════════════════════════════════════════════════

def train(
    augmented_dir="D:/proyecto/Lo que hay en google/augmented_dataset",
    output_dir="D:/proyecto/Lo que hay en google/models",
):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # ── GPU / CPU ──────────────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"\n[HW] GPU: {gpu_name} | VRAM: {vram:.1f} GB")
    else:
        print("\n[HW] CUDA no disponible, usando CPU (será lento)")

    # ── Transforms ────────────────────────────────────────────────────────
    # EfficientNetV2-S espera 384×384 pero 224×224 también funciona bien
    IMG_SIZE = 224
    BATCH    = 48   # ajustar si hay OOM (bajar a 32 o 24)

    mean = [0.485, 0.456, 0.406]
    std  = [0.229, 0.224, 0.225]

    train_tf = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.15),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
        transforms.RandomErasing(p=0.15, scale=(0.02, 0.15)),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])

    # ── Dataset ───────────────────────────────────────────────────────────
    print(f"\n[DATA] Cargando dataset desde: {augmented_dir}")
    full_ds = datasets.ImageFolder(augmented_dir, transform=train_tf)
    class_names = full_ds.classes
    num_classes  = len(class_names)
    print(f"[DATA] Clases ({num_classes}): {class_names}")
    print(f"[DATA] Total imágenes: {len(full_ds)}")

    val_n   = int(0.15 * len(full_ds))
    train_n = len(full_ds) - val_n
    train_ds_raw, val_ds_raw = random_split(full_ds, [train_n, val_n],
                                             generator=torch.Generator().manual_seed(SEED))

    # Validación con transforms limpios
    val_ds_raw.dataset = datasets.ImageFolder(augmented_dir, transform=val_tf)

    train_loader = DataLoader(train_ds_raw, batch_size=BATCH, shuffle=True,
                              num_workers=4, pin_memory=True, persistent_workers=True)
    val_loader   = DataLoader(val_ds_raw,   batch_size=BATCH, shuffle=False,
                              num_workers=4, pin_memory=True, persistent_workers=True)

    # ── Guardar metadatos de clases ───────────────────────────────────────
    class_map = {}
    for idx, name in enumerate(class_names):
        meta = BANKNOTE_METADATA.get(name, {
            "denomination": f"${name} COP",
            "character": "Desconocido",
            "color": "#2563eb",
        })
        class_map[idx] = {"index": idx, "raw_name": name, **meta}
    with open(out_path / "classes.json", "w", encoding="utf-8") as f:
        json.dump(class_map, f, indent=2, ensure_ascii=False)
    print(f"[OK] classes.json guardado ({num_classes} clases)")

    model_path = str(out_path / "banknote_efficientnetv2s.pt")
    criterion  = nn.CrossEntropyLoss(label_smoothing=0.1)
    scaler     = torch.amp.GradScaler('cuda')
    best_acc   = 0.0
    history    = []

    # ══════════════════════════════════════════════════════════════════
    # FASE 1: Transfer Learning — solo cabeza (20 épocas)
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "="*65)
    print(">>> FASE 1 — Transfer Learning (backbone congelado, 20 épocas)")
    print("="*65)

    model = build_model(num_classes, freeze_backbone=True).to(device)
    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                                  lr=1e-3, weight_decay=1e-4)
    scheduler = get_scheduler(optimizer, warmup_epochs=3, total_epochs=20)

    EPOCHS_P1 = 20
    patience_p1, no_improve = 8, 0

    for epoch in range(1, EPOCHS_P1 + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_epoch(model, train_loader, optimizer, criterion, scaler, device, use_mixup=True)
        vl_loss, vl_acc = eval_epoch(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        lr_now = optimizer.param_groups[0]['lr']
        print(f"  P1 Ep {epoch:02d}/{EPOCHS_P1} | "
              f"tr_loss={tr_loss:.4f} tr_acc={tr_acc*100:.2f}% | "
              f"val_loss={vl_loss:.4f} val_acc={vl_acc*100:.2f}% | "
              f"lr={lr_now:.2e} | {elapsed:.1f}s")
        history.append({"fase": 1, "epoch": epoch, "tr_loss": tr_loss, "tr_acc": tr_acc,
                        "val_loss": vl_loss, "val_acc": vl_acc})

        if vl_acc > best_acc:
            best_acc = vl_acc
            torch.save(model.state_dict(), model_path)
            print(f"  [OK] Nuevo mejor modelo guardado (val_acc={best_acc*100:.2f}%)")
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience_p1:
                print(f"  Early stopping FASE 1 (sin mejora en {patience_p1} épocas).")
                break

    # ══════════════════════════════════════════════════════════════════
    # FASE 2: Fine-Tuning — descongelar capas superiores (40 épocas)
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "="*65)
    print(">>> FASE 2 — Fine-Tuning (capas superiores + cabeza, 40 épocas, lr=5e-5)")
    print("="*65)

    # Cargar el mejor modelo de Fase 1
    model.load_state_dict(torch.load(model_path, map_location=device))
    unfreeze_top_layers(model, n_blocks_to_unfreeze=5)

    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                                  lr=5e-5, weight_decay=5e-5)
    scheduler = get_scheduler(optimizer, warmup_epochs=4, total_epochs=40)

    EPOCHS_P2 = 40
    patience_p2, no_improve = 10, 0

    for epoch in range(1, EPOCHS_P2 + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_epoch(model, train_loader, optimizer, criterion, scaler, device, use_mixup=True)
        vl_loss, vl_acc = eval_epoch(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        lr_now = optimizer.param_groups[0]['lr']
        print(f"  P2 Ep {epoch:02d}/{EPOCHS_P2} | "
              f"tr_loss={tr_loss:.4f} tr_acc={tr_acc*100:.2f}% | "
              f"val_loss={vl_loss:.4f} val_acc={vl_acc*100:.2f}% | "
              f"lr={lr_now:.2e} | {elapsed:.1f}s")
        history.append({"fase": 2, "epoch": epoch, "tr_loss": tr_loss, "tr_acc": tr_acc,
                        "val_loss": vl_loss, "val_acc": vl_acc})

        if vl_acc > best_acc:
            best_acc = vl_acc
            torch.save(model.state_dict(), model_path)
            print(f"  [OK] Nuevo mejor modelo guardado (val_acc={best_acc*100:.2f}%)")
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience_p2:
                print(f"  Early stopping FASE 2 (sin mejora en {patience_p2} épocas).")
                break

    # ─── Resultados finales ───────────────────────────────────────────────
    model.load_state_dict(torch.load(model_path, map_location=device))
    final_loss, final_acc = eval_epoch(model, val_loader, criterion, device)
    print(f"\n{'='*65}")
    print(f"[FINAL] Pérdida val: {final_loss:.4f} | Precisión val: {final_acc*100:.2f}%")
    print(f"[OK]    Modelo guardado en: {model_path}")

    with open(out_path / "training_history.json", "w") as f:
        json.dump({"best_val_acc": best_acc, "history": history}, f, indent=2)
    print(f"[OK]    Historial guardado en: {out_path / 'training_history.json'}")

    return model_path


if __name__ == "__main__":
    train()

