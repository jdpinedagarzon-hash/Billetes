"""
Pipeline de augmentación EXTREMA para clasificación de billetes colombianos.
Optimizado para RTX 5060 Ti / Ryzen 5 5600 / 32 GB RAM.

De ~20-35 fotos por clase genera 1200+ imágenes con:
  - Orientación completa (rotaciones, espejos)
  - Perspectiva / distorsión geométrica (OpenCV)
  - Iluminación (brillo, contraste, gamma, sombras locales)
  - Color (saturación, tinte, temperatura de color)
  - Ruido (Gaussian, salt-and-pepper)
  - Blur (Gaussian, motion blur simulado)
  - Recortes aleatorios (distintos encuadres)
  - Combinaciones aleatorias de múltiples técnicas
"""

import os
import shutil
import random
import warnings
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from multiprocessing import Pool, cpu_count

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("[AVISO] OpenCV no disponible; se omiten transformaciones de perspectiva.")

warnings.filterwarnings("ignore")
random.seed(42)
np.random.seed(42)

TARGET_SIZE = (224, 224)
WORKING_SIZE = (480, 320)


# ─── Transformaciones geométricas ───────────────────────────────────────────

def apply_perspective_warp(img_np, intensity=0.14):
    if not HAS_CV2:
        return img_np
    h, w = img_np.shape[:2]
    m = int(min(h, w) * intensity)
    src = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    rng = lambda: random.randint(0, m)
    dst = np.float32([
        [rng(), rng()], [w - rng(), rng()],
        [rng(), h - rng()], [w - rng(), h - rng()]
    ])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img_np, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def apply_elastic_distortion(img_np, alpha=18, sigma=4):
    """Distorsión elástica suave (simula papel arrugado/doblado)."""
    if not HAS_CV2:
        return img_np
    h, w = img_np.shape[:2]
    dx = cv2.GaussianBlur(
        (np.random.rand(h, w).astype(np.float32) * 2 - 1), (0, 0), sigma
    ) * alpha
    dy = cv2.GaussianBlur(
        (np.random.rand(h, w).astype(np.float32) * 2 - 1), (0, 0), sigma
    ) * alpha
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    map_x = np.clip(x + dx, 0, w - 1).astype(np.float32)
    map_y = np.clip(y + dy, 0, h - 1).astype(np.float32)
    return cv2.remap(img_np, map_x, map_y, interpolation=cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REFLECT)


# ─── Transformaciones de color / luz ────────────────────────────────────────

def apply_gamma(img_np, gamma):
    lut = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)],
                   dtype=np.uint8)
    return lut[img_np]


def add_gaussian_noise(img_np, sigma=15):
    noise = np.random.normal(0, sigma, img_np.shape).astype(np.int16)
    return np.clip(img_np.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def add_salt_pepper(img_np, amount=0.015):
    out = img_np.copy()
    n = int(amount * img_np.size // img_np.shape[2])
    h, w = img_np.shape[:2]
    ry = np.random.randint(0, h, n)
    rx = np.random.randint(0, w, n)
    out[ry[:n//2], rx[:n//2]] = 255
    out[ry[n//2:], rx[n//2:]] = 0
    return out


def apply_shadow(img_np):
    """Sombra triangular que simula oclusión parcial."""
    out = img_np.copy().astype(np.float32)
    h, w = out.shape[:2]
    x1, x2 = sorted(random.sample(range(w), 2))
    mask = np.zeros((h, w), dtype=np.float32)
    if HAS_CV2:
        pts = np.array([[x1, 0], [x2, 0], [w, h], [0, h]] if random.random() > 0.5
                       else [[x1, h], [x2, h], [w, 0], [0, 0]])
        cv2.fillPoly(mask, [pts], 1.0)
    factor = random.uniform(0.4, 0.75)
    out[mask == 1] *= factor
    return np.clip(out, 0, 255).astype(np.uint8)


def color_jitter_np(img_np, hue_shift=5):
    """Cambio SUAVE de tinte y saturación en espacio HSV.
    Reducido a ±5° para preservar el color dominante del billete."""
    if not HAS_CV2:
        return img_np
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + random.uniform(-hue_shift, hue_shift)) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * random.uniform(0.80, 1.20), 0, 255)
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB)


def simulate_temperature(img_pil, temp):
    """temp > 1 → más cálido (tonos anaranjados), < 1 → más frío (azulado)."""
    r, g, b = img_pil.split()
    r = ImageEnhance.Brightness(r).enhance(temp)
    b = ImageEnhance.Brightness(b).enhance(2.0 - temp)
    return Image.merge('RGB', (r, g, b))


def random_crop_resize(img_pil, ratio=(0.70, 0.95)):
    w, h = img_pil.size
    cr = random.uniform(*ratio)
    cw, ch = int(w * cr), int(h * cr)
    left = random.randint(0, w - cw)
    top  = random.randint(0, h - ch)
    return img_pil.crop((left, top, left + cw, top + ch)).resize(TARGET_SIZE, Image.Resampling.BILINEAR)


# ─── Generador principal por imagen ─────────────────────────────────────────

def augment_single_image(img_pil):
    """Recibe PIL y devuelve lista de variantes aumentadas."""
    variants = []

    img_pil = ImageOps.exif_transpose(img_pil)
    if img_pil.height > img_pil.width:
        img_pil = img_pil.rotate(90, expand=True)

    base = img_pil.resize(WORKING_SIZE, Image.Resampling.BILINEAR)
    base_np = np.array(base)

    def pil(arr):
        return Image.fromarray(arr)

    # BLOQUE 1: rotaciones × espejos (8)
    for angle in [0, 90, 180, 270]:
        rot = base.rotate(angle, expand=True).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        variants += [rot, ImageOps.mirror(rot)]

    # BLOQUE 2: brillo × contraste (96)
    for mirror in [base, ImageOps.mirror(base)]:
        for brightness in [0.5, 0.65, 0.8, 0.95, 1.1, 1.25, 1.45, 1.65]:
            b_img = ImageEnhance.Brightness(mirror).enhance(brightness)
            for contrast in [0.75, 1.0, 1.35]:
                variants.append(
                    ImageEnhance.Contrast(b_img).enhance(contrast)
                    .resize(TARGET_SIZE, Image.Resampling.BILINEAR)
                )

    # BLOQUE 3: saturación — rango REDUCIDO para preservar color del billete (10)
    for mirror in [base, ImageOps.mirror(base)]:
        for sat in [0.75, 0.88, 1.0, 1.15, 1.35]:
            variants.append(
                ImageEnhance.Color(mirror).enhance(sat)
                .resize(TARGET_SIZE, Image.Resampling.BILINEAR)
            )

    # BLOQUE 4: gamma (14)
    for gamma in [0.45, 0.65, 0.85, 1.1, 1.4, 1.75, 2.2]:
        g_pil = pil(apply_gamma(base_np, gamma)).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        variants += [g_pil, ImageOps.mirror(g_pil)]

    # BLOQUE 5: ruido gaussiano (6)
    for sigma in [8, 18, 32]:
        n_pil = pil(add_gaussian_noise(base_np, sigma)).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        variants += [n_pil, ImageOps.mirror(n_pil)]

    # BLOQUE 6: salt & pepper (2)
    for amt in [0.01, 0.025]:
        variants.append(pil(add_salt_pepper(base_np, amt)).resize(TARGET_SIZE, Image.Resampling.BILINEAR))

    # BLOQUE 7: blur (6)
    for r in [1, 2, 3]:
        bl = base.filter(ImageFilter.GaussianBlur(radius=r)).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        variants += [bl, ImageOps.mirror(bl)]

    # BLOQUE 8: perspectiva (50)
    if HAS_CV2:
        for _ in range(25):
            wp = pil(apply_perspective_warp(base_np.copy())).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
            variants += [wp, ImageOps.mirror(wp)]

    # BLOQUE 9: distorsión elástica (16)
    if HAS_CV2:
        for _ in range(8):
            el = pil(apply_elastic_distortion(base_np.copy())).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
            variants += [el, ImageOps.mirror(el)]

    # BLOQUE 10: sombra (6)
    for _ in range(6):
        variants.append(pil(apply_shadow(base_np.copy())).resize(TARGET_SIZE, Image.Resampling.BILINEAR))

    # BLOQUE 11: color jitter HSV (8)
    if HAS_CV2:
        for _ in range(8):
            variants.append(pil(color_jitter_np(base_np.copy())).resize(TARGET_SIZE, Image.Resampling.BILINEAR))

    # BLOQUE 12: temperatura de color SUAVE (4) — cambios pequeños para preservar matiz
    for temp in [0.92, 0.96, 1.04, 1.08]:
        variants.append(simulate_temperature(base, temp).resize(TARGET_SIZE, Image.Resampling.BILINEAR))

    # BLOQUE 13: recortes aleatorios (100)
    for _ in range(50):
        cr = random_crop_resize(base)
        variants += [cr, ImageOps.mirror(cr)]

    # BLOQUE 14: rotaciones diagonales + brillo (12)
    for angle in [30, 60, 120, 150]:
        rot = base.rotate(angle, expand=False, fillcolor=(128, 128, 128)).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        for brightness in [0.7, 1.0, 1.35]:
            variants.append(ImageEnhance.Brightness(rot).enhance(brightness))

    # BLOQUE 15: combinaciones aleatorias (25)
    for _ in range(25):
        img_c = base.copy()
        img_np_c = base_np.copy()
        ops_pool = [
            lambda i, n: (ImageEnhance.Brightness(i).enhance(random.uniform(0.6, 1.5)), n),
            lambda i, n: (i, add_gaussian_noise(n, random.randint(5, 25))),
            lambda i, n: (i, apply_perspective_warp(n) if HAS_CV2 else n),
            lambda i, n: (ImageOps.mirror(i), np.fliplr(n)),
            lambda i, n: (i, apply_gamma(n, random.uniform(0.5, 2.0))),
            lambda i, n: (random_crop_resize(i), n),
        ]
        for op in random.sample(ops_pool, k=random.randint(2, 4)):
            img_c, img_np_c = op(img_c, img_np_c)
        try:
            final = img_c.resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        except Exception:
            final = Image.fromarray(np.clip(img_np_c, 0, 255).astype(np.uint8)).resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        variants.append(final)

    return variants


# ─── Worker para multiprocessing ────────────────────────────────────────────

def _process_folder(args):
    folder_path, dst_path = args
    folder = Path(folder_path)
    class_dst = Path(dst_path) / folder.name
    class_dst.mkdir(parents=True, exist_ok=True)

    imgs = list(folder.glob("*.jpg")) + list(folder.glob("*.png")) + list(folder.glob("*.jpeg"))
    count = 0
    for img_path in imgs:
        try:
            img = Image.open(img_path).convert("RGB")
            for v in augment_single_image(img):
                v.save(class_dst / f"aug_{count:06d}.jpg", quality=90)
                count += 1
        except Exception as e:
            print(f"  [ERROR] {img_path.name}: {e}")

    print(f"  Clase '{folder.name}': {count} imagenes de {len(imgs)} originales.")
    return count


# ─── Entry point ────────────────────────────────────────────────────────────

def generate_dataset(
    src_dir="D:/proyecto/Fotos billetes",
    dst_dir="D:/proyecto/Lo que hay en google/augmented_dataset",
    workers=None,
):
    """Genera el dataset augmentado completo usando todos los nucleos disponibles."""
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)

    if dst_path.exists():
        print(f"[INFO] Borrando dataset anterior en {dst_path} ...")
        shutil.rmtree(dst_path)
    dst_path.mkdir(parents=True)

    folders = [f for f in sorted(src_path.iterdir()) if f.is_dir()]
    if not folders:
        raise RuntimeError(f"No se encontraron subcarpetas en {src_dir}")

    n_workers = workers or min(cpu_count(), len(folders))
    print(f"\n[INFO] Augmentando {len(folders)} clases con {n_workers} proceso(s)...\n")

    args = [(str(f), str(dst_path)) for f in folders]
    with Pool(processes=n_workers) as pool:
        totals = pool.map(_process_folder, args)

    total = sum(totals)
    print(f"\n[OK] Dataset generado -> {total} imagenes totales en {dst_path}")
    return dst_path


if __name__ == "__main__":
    generate_dataset()
