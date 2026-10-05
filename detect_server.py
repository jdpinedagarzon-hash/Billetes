"""
Servidor de inferencia en tiempo real para BilletIA.
═══════════════════════════════════════════════════
· Recibe fotogramas base64 de la cámara vía POST /predict
· Carga EfficientNetV2-S desde models/banknote_efficientnetv2s.pt
· Devuelve JSON con denominación, confianza y metadatos del billete
· Cabeceras CORS incluidas para llamadas desde el HTML local
· Puerto: 5050

Uso:
    python detect_server.py
"""

import io
import json
import base64
import logging
from pathlib import Path

import torch
import torch.nn as nn
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS
from torchvision import transforms
from torchvision.models import efficientnet_v2_s, EfficientNet_V2_S_Weights

# ─── Configuración ──────────────────────────────────────────────────────────
MODEL_PATH  = Path("D:/proyecto/Lo que hay en google/models/banknote_efficientnetv2s.pt")
CLASSES_JSON= Path("D:/proyecto/Lo que hay en google/models/classes.json")
IMG_SIZE    = 224
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CONF_THRESH = 0.60   # confianza mínima para mostrar resultado

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("BilletIA")

app = Flask(__name__)
CORS(app)   # permite peticiones desde cualquier origen (archivo local HTML)

# ─── Transforms de inferencia ────────────────────────────────────────────────
infer_tf = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


# ─── Carga del modelo ────────────────────────────────────────────────────────

def load_model_and_classes():
    """Carga el modelo entrenado y los metadatos de clases."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modelo no encontrado: {MODEL_PATH}\n"
            "Ejecuta primero: python augment.py && python train.py"
        )
    if not CLASSES_JSON.exists():
        raise FileNotFoundError(f"classes.json no encontrado: {CLASSES_JSON}")

    with open(CLASSES_JSON, encoding="utf-8") as f:
        class_map = json.load(f)   # {str(idx): {...}}

    num_classes = len(class_map)
    log.info(f"Cargando modelo con {num_classes} clases en {DEVICE}...")

    # Construir arquitectura idéntica a train.py
    model = efficientnet_v2_s(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.35, inplace=True),
        nn.Linear(in_features, 512),
        nn.SiLU(),
        nn.Dropout(p=0.25),
        nn.Linear(512, num_classes),
    )
    state = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()

    log.info(f"Modelo cargado correctamente. GPU: {DEVICE.type == 'cuda'}")
    return model, class_map


# Cargar al inicio
try:
    MODEL, CLASS_MAP = load_model_and_classes()
    MODEL_READY = True
except FileNotFoundError as e:
    log.warning(str(e))
    MODEL, CLASS_MAP = None, {}
    MODEL_READY = False


# ─── Endpoint de predicción ──────────────────────────────────────────────────

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "ready": MODEL_READY,
        "device": str(DEVICE),
        "classes": len(CLASS_MAP),
        "model": str(MODEL_PATH),
    })


@app.route("/predict", methods=["POST"])
def predict():
    if not MODEL_READY:
        return jsonify({
            "error": "Modelo no cargado. Ejecuta python augment.py && python train.py primero.",
            "ready": False
        }), 503

    data = request.get_json(force=True)
    if not data or "image" not in data:
        return jsonify({"error": "Falta el campo 'image' en el JSON"}), 400

    # ── Decodificar imagen base64 ──────────────────────────────────────────
    try:
        img_b64 = data["image"]
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(img_b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        return jsonify({"error": f"Error decodificando imagen: {e}"}), 400

    # ── Inferencia ────────────────────────────────────────────────────────
    tensor = infer_tf(img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        with torch.amp.autocast(device_type=DEVICE.type):
            logits = MODEL(tensor)
        probs = torch.softmax(logits, dim=1)[0]

    top_conf, top_idx = probs.topk(3)
    top_conf = top_conf.cpu().tolist()
    top_idx  = top_idx.cpu().tolist()

    best_idx  = str(top_idx[0])
    best_conf = top_conf[0]
    meta      = CLASS_MAP.get(best_idx, {})

    # ── Respuesta ─────────────────────────────────────────────────────────
    top3 = [
        {
            "index":       top_idx[i],
            "raw_name":    CLASS_MAP.get(str(top_idx[i]), {}).get("raw_name", "?"),
            "denomination":CLASS_MAP.get(str(top_idx[i]), {}).get("denomination", "?"),
            "confidence":  round(top_conf[i] * 100, 2),
        }
        for i in range(len(top_idx))
    ]

    return jsonify({
        "detected":    best_conf >= CONF_THRESH,
        "confidence":  round(best_conf * 100, 2),
        "denomination":meta.get("denomination", "Desconocido"),
        "character":   meta.get("character", ""),
        "color":       meta.get("color", "#2563eb"),
        "raw_name":    meta.get("raw_name", ""),
        "top3":        top3,
    })


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 55)
    log.info("  BilletIA · Servidor de detección en tiempo real")
    log.info(f"  Device: {DEVICE}  |  Puerto: 5050")
    log.info("=" * 55)
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)

