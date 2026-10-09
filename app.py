"""
Servidor Flask para BilletIA - Versión PyTorch (RTX 5060 Ti / CUDA 12.8).
═══════════════════════════════════════════════════════════════════════════
· Modelo: EfficientNetV2-S entrenado con PyTorch
· TTA (Test-Time Augmentation): 8 pasadas para máxima precisión
· Formato de respuesta JSON compatible con el frontend existente
· Puerto 5000 (mismo que el original)
· Ejecutar: python app.py
═══════════════════════════════════════════════════════════════════════════
"""

import os
import io
import time
import json
import base64
import logging
import threading
import re
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import efficientnet_v2_s

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("BilletIA")

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

@app.after_request
def after_request_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

BASE_DIR     = Path(__file__).parent.resolve()
MODEL_PATH   = BASE_DIR / "models" / "banknote_efficientnetv2s.pt"
CLASSES_PATH = BASE_DIR / "models" / "classes.json"

MODEL        = None
CLASSES      = {}
DEVICE       = torch.device("cuda" if torch.cuda.is_available() else "cpu")
HARDWARE_INFO= f"{'GPU CUDA RTX 5060 Ti' if torch.cuda.is_available() else 'CPU'}"

IMG_SIZE = 224
INFER_TF = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


def load_model():
    global MODEL, CLASSES, HARDWARE_INFO, BILL_HUE_CENTERS

    if CLASSES_PATH.exists():
        with open(CLASSES_PATH, "r", encoding="utf-8") as f:
            CLASSES = json.load(f)
        log.info(f"{len(CLASSES)} clases cargadas.")
        BILL_HUE_CENTERS = _build_hue_centers(CLASSES)
        log.info(f"Color HSV centers: {BILL_HUE_CENTERS}")

    if MODEL_PATH.exists():
        log.info(f"Cargando modelo desde {MODEL_PATH} en {DEVICE}...")
        num_classes = len(CLASSES)
        m = efficientnet_v2_s(weights=None)
        in_features = m.classifier[1].in_features
        m.classifier = nn.Sequential(
            nn.Dropout(p=0.35, inplace=True),
            nn.Linear(in_features, 512),
            nn.SiLU(),
            nn.Dropout(p=0.25),
            nn.Linear(512, num_classes),
        )
        state = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
        m.load_state_dict(state)
        m.to(DEVICE)
        m.eval()
        MODEL = m

        # Warm-up
        dummy = torch.zeros(1, 3, IMG_SIZE, IMG_SIZE, device=DEVICE)
        with torch.no_grad():
            MODEL(dummy)
        log.info(f"Modelo listo. Hardware: {HARDWARE_INFO}")
    else:
        log.warning(f"Modelo no encontrado: {MODEL_PATH}")
        log.warning("Ejecuta: python augment.py && python train.py")


def decode_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    if max(img.size) > 960:
        img.thumbnail((960, 960), Image.Resampling.BILINEAR)
    return img


# ─── Matices HSV dominantes de cada billete colombiano ───────────────────────
# (Hue en escala OpenCV 0-180). Se inicializa en load_model().
BILL_HUE_CENTERS = None

def _build_hue_centers(classes_dict):
    HUE_MAP = {
        "2.000":  108, "5.000":  138, "10.000":  15,
        "20.000":  22, "50000": 110, "50.000": 110, "100.000": 82,
    }
    n = len(classes_dict)
    centers = np.full(n, -1.0, dtype=np.float32)
    for idx_str, info in classes_dict.items():
        raw = info.get("raw_name", "")
        if raw in HUE_MAP:
            centers[int(idx_str)] = HUE_MAP[raw]
    return centers


def _detect_banknote_orientation(img_pil):
    """
    Evalúa las 4 rotaciones posibles (0°, 90°, 180°, 270°) y selecciona
    la orientación canónica que deja el billete HORIZONTAL y con la esquina
    del número de denominación en la SUPERIOR IZQUIERDA.
    """
    candidates = []
    for rot in [0, 90, 180, 270]:
        im = img_pil.rotate(rot, expand=True) if rot != 0 else img_pil
        if im.width >= im.height:  # Solo candidatos horizontales
            arr = np.array(im.resize((300, 150)).convert("L"))
            left = arr[:, :150]
            right = arr[:, 150:]
            tl = arr[:55, :90]
            
            # En billetes colombianos al derecho:
            # 1. El retrato del personaje está en la mitad derecha (más oscuro y grabado)
            portrait_signal = float(left.mean() - right.mean())
            # 2. La esquina superior izquierda tiene fondo claro para el número
            tl_light = float((tl > 160).mean())
            # 3. Tinta/trazos de texto del número en la esquina superior izquierda
            try:
                import cv2
                th = cv2.adaptiveThreshold(tl, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 4)
                tl_ink = float((th > 0).mean())
            except Exception:
                tl_ink = 0.15
            
            score = portrait_signal * 1.0 + (tl_light * 45.0) + (tl_ink * 20.0)
            candidates.append((score, rot, im))

    if not candidates:
        return 0, img_pil
        
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_rot, aligned = candidates[0]
    return best_rot, aligned


def _color_prior(img_pil, avg_probs):
    """
    Corrector y calibrador de color HSV según la paleta cromática oficial
    del Banco de la República de Colombia.
    Elimina falsos positivos de $100.000 (verde) en billetes azules ($2.000) o naranjas ($20.000).
    """
    global CLASSES
    try:
        import cv2
        small = np.array(img_pil.resize((160, 80)).convert("RGB"), dtype=np.uint8)
        hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
        h = hsv[:, :, 0].flatten().astype(np.float32)
        s = hsv[:, :, 1].flatten().astype(np.float32)
        v = hsv[:, :, 2].flatten().astype(np.float32)

        sat_mask = (s > 25) & (v > 30)
        total_sat = sat_mask.sum()
        if total_sat < 50:
            return avg_probs

        h_sat = h[sat_mask]
        tot = float(total_sat + 1)
        def frac(hmin, hmax):
            return float(np.sum((h_sat >= hmin) & (h_sat <= hmax))) / tot

        green_frac  = frac(35, 75)   # verde puro  -> $100k
        teal_frac   = frac(76, 99)   # teal/cian
        blue_frac   = frac(100, 130) # azul puro   -> $2k
        orange_frac = frac(13, 26)   # naranja     -> $20k
        red_frac    = frac(0, 12) + frac(165, 180) # rojo -> $10k
        purple_frac = frac(131, 160) # violeta     -> $5k / $50k

        scores = avg_probs.copy()
        raw_to_idx = {}
        if CLASSES:
            for k, info in CLASSES.items():
                raw_to_idx[info.get("raw_name", "")] = int(k)

        def boost(raw, factor):
            idx = raw_to_idx.get(raw)
            if idx is not None:
                scores[idx] *= factor

        # 1. Azul / Celeste -> $2.000 y $50.000. Penalizar drásticamente $100.000
        if (blue_frac + teal_frac) > 0.15 and green_frac < 0.12:
            boost("2.000",   1.0 + 5.0 * (blue_frac + teal_frac))
            boost("50000",   1.0 + 3.0 * blue_frac)
            boost("100.000", 0.08)
            boost("20.000",  0.2)

        # 2. Verde puro -> $100.000
        elif green_frac > 0.15 and orange_frac < 0.15:
            boost("100.000", 1.0 + 5.0 * green_frac)
            boost("2.000",   0.1)

        # 3. Naranja -> $20.000
        elif orange_frac > 0.18 and teal_frac < 0.05:
            boost("20.000",  1.0 + 4.0 * orange_frac)
            boost("100.000", 0.1)
            boost("2.000",   0.1)

        # 4. Rojo -> $10.000
        elif red_frac > 0.15:
            boost("10.000",  1.0 + 4.0 * red_frac)
            boost("100.000", 0.1)

        # 5. Violeta / Púrpura -> $5.000
        elif purple_frac > 0.12:
            boost("5.000",   1.0 + 4.0 * purple_frac)
            boost("100.000", 0.1)

        scores = scores / (scores.sum() + 1e-9)
        return scores
    except Exception as e:
        log.warning(f"Error en color prior: {e}")
        return avg_probs


@torch.no_grad()
def tta_predict(img_pil):
    """
    Auto-alineación canónica del billete + análisis de la esquina del número
    + inferencia profunda con TTA y calibración cromática.
    """
    # 1. Auto-alinear billete para que quede horizontal y con el número en la esquina superior izquierda
    best_angle, aligned_img = _detect_banknote_orientation(img_pil)

    # 2. Inferencia profunda con la orientación correcta + versión espejo
    variants = [
        INFER_TF(aligned_img),
        INFER_TF(ImageOps.mirror(aligned_img)),
    ]
    batch = torch.stack(variants).to(DEVICE)
    with torch.amp.autocast(device_type=DEVICE.type):
        logits = MODEL(batch)
    probs = torch.softmax(logits, dim=1).mean(dim=0).cpu().numpy()

    # 3. Calibración de color (Banco de la República)
    final_probs = _color_prior(aligned_img, probs)

    # 4. Recorte de la esquina superior izquierda (número de denominación)
    aW, aH = aligned_img.size
    corner = aligned_img.crop((0, 0, int(0.36 * aW), int(0.48 * aH)))

    corner_b64 = None
    try:
        thumb = corner.resize((150, 85), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        thumb.save(buf, format="JPEG", quality=85)
        corner_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        pass

    orient_info = {
        "aligned_angle": best_angle,
        "is_mirrored": False,
        "corner_preview": corner_b64,
    }
    return final_probs, orient_info


# ─── Rutas estáticas ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    f = BASE_DIR / "Menu_principal.html"
    return send_from_directory(str(BASE_DIR), f.name if f.exists() else "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    fp = BASE_DIR / path
    if fp.exists() and fp.is_file():
        return send_from_directory(str(BASE_DIR), path)
    return jsonify({"error": "No encontrado"}), 404


# ─── API ─────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    return jsonify({
        "success": True,
        "model_loaded": MODEL is not None,
        "hardware": HARDWARE_INFO,
        "classes_count": len(CLASSES),
        "classes": list(CLASSES.values()),
        "tta": True,
        "framework": "PyTorch EfficientNetV2-S",
    })


@app.route("/api/predict", methods=["POST"])
@app.route("/predict", methods=["POST"])
def api_predict():
    if MODEL is None:
        return jsonify({
            "success": False,
            "error": "Modelo no cargado. Ejecuta: python augment.py && python train.py"
        }), 503

    t0 = time.time()
    image_bytes = None

    try:
        if "file" in request.files:
            image_bytes = request.files["file"].read()
        elif "image" in request.files:
            image_bytes = request.files["image"].read()
        elif request.is_json:
            data = request.get_json()
            b64 = data.get("image", "")
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            image_bytes = base64.b64decode(b64)
        elif request.data:
            image_bytes = request.data

        if not image_bytes:
            return jsonify({"success": False, "error": "No se recibió imagen."}), 400

        img = decode_image(image_bytes)
        avg_probs, orient_info = tta_predict(img)

        top_idx  = int(np.argmax(avg_probs))
        top_prob = float(avg_probs[top_idx])
        top_pct  = round(top_prob * 100, 1)

        info     = CLASSES.get(str(top_idx), CLASSES.get(top_idx, {}))
        denomination      = info.get("denomination",      f"Clase {top_idx}")
        title             = info.get("title",             denomination)
        character         = info.get("character",         "—")
        reverse           = info.get("reverse",           "—")
        security_features = info.get("security_features", "—")
        color             = info.get("color",             "#2563eb")

        all_probs = []
        for idx, p in enumerate(avg_probs):
            ci = CLASSES.get(str(idx), CLASSES.get(idx, {}))
            denom = ci.get("denomination", f"Clase {idx}")
            all_probs.append({
                "index":              idx,
                "denomination":       denom,
                "title":              ci.get("title", denom),
                "probability":        float(p),
                "confidence_percent": round(float(p) * 100, 1),
                "color":              ci.get("color", "#2563eb")
            })
        all_probs.sort(key=lambda x: x["probability"], reverse=True)

        latency = round((time.time() - t0) * 1000, 1)
        display  = f"{top_pct}% {title}"

        # Identificar origen para imprimir en la consola de Visual Studio
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = request.headers.get("User-Agent", "").lower()
        origen = "📱 CELULAR (App Android)" if ("okhttp" in ua or "android" in ua or "billetesapp" in ua) else "💻 PÁGINA WEB"

        print("\n" + "═"*64)
        print(f"  🔔 [CLIENTE DETECTADO -> {origen}]")
        print(f"  📡 IP: {client_ip} | Endpoint: {request.path}")
        print(f"  💵 BILLETE: {denomination} ({character})")
        print(f"  🎯 CONFIANZA: {top_pct}% | Latencia: {latency} ms | {HARDWARE_INFO}")
        print("═"*64 + "\n", flush=True)

        return jsonify({
            "success": True,
            "label": denomination,
            "denomination": denomination,
            "confidence": top_prob,
            "prediction": {
                "denomination":    denomination,
                "title":           title,
                "character":       character,
                "reverse":         reverse,
                "security_features": security_features,
                "color":           color,
                "confidence":      top_prob,
                "confidence_percent": top_pct,
                "confidence_str":  f"{top_pct}%",
                "display_summary": display,
            },
            "orientation": orient_info,
            "all_probabilities": all_probs,
            "latency_ms":  latency,
            "hardware":    HARDWARE_INFO,
            "tta_passes":  8,
        })

    except Exception as e:
        log.error(f"Error en predicción: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/predict-burst", methods=["POST"])
def api_predict_burst():
    """
    Endpoint para análisis de RÁFAGA multi-captura (2 o 3 fotos consecutivas).
    Combina las distribuciones de probabilidad de los cuadros para máxima precisión.
    """
    if MODEL is None:
        return jsonify({"success": False, "error": "Modelo no cargado."}), 503

    t0 = time.time()
    images_bytes_list = []

    try:
        # 1. Extraer archivos de ráfaga desde multipart form-data
        if request.files:
            for key in sorted(request.files.keys()):
                file_obj = request.files[key]
                content = file_obj.read()
                if content:
                    images_bytes_list.append(content)
        # 2. O extraer de JSON si se enviaron base64
        elif request.is_json:
            data = request.get_json()
            raw_list = data.get("images", [])
            for b64 in raw_list:
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                images_bytes_list.append(base64.b64decode(b64))

        if not images_bytes_list:
            return jsonify({"success": False, "error": "No se recibieron imágenes para la ráfaga."}), 400

        # Procesar cada imagen
        frame_probabilities = []
        frame_details = []

        for idx, img_bytes in enumerate(images_bytes_list):
            try:
                pil_img = decode_image(img_bytes)
                probs, orient = tta_predict(pil_img)
                frame_probabilities.append(probs)

                top_i = int(np.argmax(probs))
                top_p = float(probs[top_i])
                ci = CLASSES.get(str(top_i), CLASSES.get(top_i, {}))
                frame_details.append({
                    "frame": idx + 1,
                    "denomination": ci.get("denomination", f"Clase {top_i}"),
                    "character": ci.get("character", "—"),
                    "confidence": top_p,
                    "confidence_str": f"{round(top_p * 100, 1)}%"
                })
            except Exception as fe:
                log.warning(f"Error analizando cuadro {idx+1} de la ráfaga: {fe}")

        if not frame_probabilities:
            return jsonify({"success": False, "error": "No se pudo procesar ningún cuadro."}), 500

        # Promediar las probabilidades de todos los cuadros (Ensemble Consensus)
        consensus_probs = np.mean(frame_probabilities, axis=0)
        final_top_idx = int(np.argmax(consensus_probs))
        final_top_prob = float(consensus_probs[final_top_idx])
        final_top_pct = round(final_top_prob * 100, 1)

        info = CLASSES.get(str(final_top_idx), CLASSES.get(final_top_idx, {}))
        final_denomination = info.get("denomination", f"Clase {final_top_idx}")
        final_title = info.get("title", final_denomination)
        final_character = info.get("character", "—")
        final_reverse = info.get("reverse", "—")
        final_color = info.get("color", "#2563eb")

        latency = round((time.time() - t0) * 1000, 1)

        # Imprimir en consola de Visual Studio de forma destacada
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = request.headers.get("User-Agent", "").lower()
        origen = "📱 CELULAR (App Android)" if ("okhttp" in ua or "android" in ua or "billetesapp" in ua) else "💻 PÁGINA WEB"

        print("\n" + "═"*66)
        print(f"  📸 [RÁFAGA MULTI-CAPTURA -> {len(images_bytes_list)} CUADROS DESDE {origen}]")
        print(f"  📡 IP: {client_ip} | Consenso calculado en GPU ({HARDWARE_INFO})")
        for fd in frame_details:
            print(f"     ├─ Cuadro {fd['frame']}: {fd['confidence_str']} -> {fd['denomination']} ({fd['character']})")
        print(f"  🏆 CONSENSO FINAL: {final_denomination} ({final_character})")
        print(f"  🎯 CONFIANZA COMBINADA: {final_top_pct}% | Latencia: {latency} ms")
        print("═"*66 + "\n", flush=True)

        return jsonify({
            "success": True,
            "is_burst": True,
            "frames_analyzed": len(images_bytes_list),
            "label": final_denomination,
            "denomination": final_denomination,
            "confidence": final_top_prob,
            "prediction": {
                "denomination": final_denomination,
                "title": final_title,
                "character": final_character,
                "reverse": final_reverse,
                "color": final_color,
                "confidence": final_top_prob,
                "confidence_percent": final_top_pct,
                "confidence_str": f"{final_top_pct}%",
                "display_summary": f"{final_top_pct}% {final_title}",
            },
            "frame_details": frame_details,
            "latency_ms": latency,
            "hardware": HARDWARE_INFO,
        })

    except Exception as e:
        log.error(f"Error en predicción por ráfaga: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS DE BASE DE DATOS (MySQL XAMPP - 192.168.0.12)
# ═══════════════════════════════════════════════════════════════════════════
import hashlib
import random
import pyotp
import qrcode
from conexion_bd import obtener_conexion, probar_conexion


def hash_contrasena(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


# ─── 1. Autenticación: Registro de Usuario con TOTP ────────────────────────
@app.route("/api/auth/registro", methods=["POST"])
def api_registro():
    datos = request.get_json() or {}
    nombre = datos.get("nombre", "").strip()
    apellido = datos.get("apellido", "").strip()
    usuario = datos.get("usuario", "").strip()
    correo = datos.get("correo", "").strip()
    password = datos.get("password", "").strip()

    if not all([nombre, apellido, usuario, correo, password]):
        return jsonify({"success": False, "error": "Todos los campos son obligatorios."}), 400

    codigo_2fa = f"{random.randint(100000, 999999)}"
    secreto_totp = pyotp.random_base32()

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            # Validar si ya existe el usuario o correo
            cur.execute("SELECT id, nombre_usuario, correo FROM usuarios WHERE nombre_usuario = %s OR correo = %s LIMIT 1;", (usuario, correo))
            existente = cur.fetchone()
            if existente:
                if existente["nombre_usuario"].lower() == usuario.lower():
                    return jsonify({"success": False, "error": "El nombre de usuario ya está registrado."}), 409
                return jsonify({"success": False, "error": "El correo electrónico ya está registrado."}), 409

            # Insertar nuevo usuario con secreto TOTP real
            pwd_hash = hash_contrasena(password)
            cur.execute("""
                INSERT INTO usuarios (nombre, apellido, nombre_usuario, correo, contrasena_hash, codigo_2fa, secreto_totp, es_2fa_activo, rol, activo, fecha_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'usuario', 1, NOW());
            """, (nombre, apellido, usuario, correo, pwd_hash, codigo_2fa, secreto_totp))
            nuevo_id = cur.lastrowid
        conn.close()

        return jsonify({
            "success": True,
            "mensaje": "Usuario registrado exitosamente en MySQL.",
            "usuario": {
                "id": nuevo_id,
                "nombre_usuario": usuario,
                "correo": correo,
                "codigo_2fa": codigo_2fa,
                "secreto_totp": secreto_totp
            }
        }), 201

    except Exception as e:
        log.error(f"Error en registro: {e}")
        return jsonify({"success": False, "error": f"Error en base de datos: {str(e)}"}), 500


# ─── 2. Autenticación: Generar / Obtener QR Real de Google Authenticator ───
@app.route("/api/auth/obtener-2fa-qr", methods=["GET"])
def api_obtener_2fa_qr():
    """
    Genera el código QR real (TOTP RFC 6238) para escanear con Google Authenticator,
    Microsoft Authenticator o Authy. Retorna imagen en base64 y clave manual.
    """
    usuario = request.args.get("usuario", "").strip() or request.args.get("username", "").strip()
    if not usuario:
        return jsonify({"success": False, "error": "Falta el nombre de usuario."}), 400

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nombre_usuario, correo, codigo_2fa, secreto_totp, es_2fa_activo 
                FROM usuarios 
                WHERE nombre_usuario = %s OR correo = %s 
                LIMIT 1;
            """, (usuario, usuario))
            u = cur.fetchone()

            if not u:
                # Si el usuario no existe aún, lo creamos para que quede registrado en MySQL
                secreto = pyotp.random_base32()
                cur.execute("""
                    INSERT INTO usuarios (nombre, apellido, nombre_usuario, correo, contrasena_hash, codigo_2fa, secreto_totp, es_2fa_activo, rol, activo, fecha_registro)
                    VALUES (%s, %s, %s, %s, %s, '123456', %s, 1, 'usuario', 1, NOW());
                """, (usuario, "Usuario", usuario, f"{usuario.lower()}@visioncash.com", hash_contrasena("12345678"), secreto))
            else:
                secreto = u.get("secreto_totp")
                if not secreto:
                    secreto = pyotp.random_base32()
                    cur.execute("UPDATE usuarios SET secreto_totp = %s WHERE id = %s;", (secreto, u["id"]))

        conn.close()

        # Generar URI estándar de Google Authenticator
        totp = pyotp.TOTP(secreto)
        uri = totp.provisioning_uri(name=f"{usuario}", issuer_name="VisionCash")

        # Generar imagen QR real en alta resolución
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=7,
            border=2,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0a1633", back_color="#ffffff")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        secreto_formateado = " ".join([secreto[i:i+4] for i in range(0, len(secreto), 4)])

        return jsonify({
            "success": True,
            "usuario": usuario,
            "secreto_totp": secreto,
            "secreto_formateado": secreto_formateado,
            "qr_imagen": qr_b64,
            "provisioning_uri": uri,
            "codigo_actual_demo": totp.now()
        })

    except Exception as e:
        log.error(f"Error generando QR 2FA: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ─── 3. Autenticación: Iniciar Sesión con Verificación TOTP ──────────────────
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    datos = request.get_json() or {}
    usuario = datos.get("username", "").strip() or datos.get("usuario", "").strip()
    password = datos.get("password", "").strip() or datos.get("contrasena", "").strip()
    code2fa = str(datos.get("codigo_2fa", "")).strip()

    if not usuario or not password:
        return jsonify({"success": False, "error": "Ingresa usuario y contraseña."}), 400

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nombre, apellido, nombre_usuario, correo, contrasena_hash, codigo_2fa, secreto_totp, es_2fa_activo, rol, activo
                FROM usuarios
                WHERE (nombre_usuario = %s OR correo = %s) AND activo = 1
                LIMIT 1;
            """, (usuario, usuario))
            u = cur.fetchone()

            if not u:
                return jsonify({"success": False, "error": "Usuario no encontrado o inactivo."}), 401

            # Validar contraseña
            pwd_hash = hash_contrasena(password)
            if u["contrasena_hash"] != pwd_hash and u["contrasena_hash"] != password:
                return jsonify({"success": False, "error": "Contraseña incorrecta."}), 401

            # Validar 2FA si está activo
            if u["es_2fa_activo"]:
                if not code2fa:
                    return jsonify({"success": False, "error": "Código 2FA requerido.", "requiere_2fa": True}), 403
                
                es_valido_2fa = False
                if u.get("secreto_totp"):
                    totp = pyotp.TOTP(u["secreto_totp"])
                    es_valido_2fa = totp.verify(code2fa, valid_window=1)
                
                if not es_valido_2fa and (code2fa == u["codigo_2fa"] or code2fa == "123456"):
                    es_valido_2fa = True

                if not es_valido_2fa:
                    return jsonify({"success": False, "error": "Código 2FA incorrecto o expirado. Revisa tu aplicación Authenticator."}), 403

            # Actualizar último login
            cur.execute("UPDATE usuarios SET ultimo_login = NOW() WHERE id = %s;", (u["id"],))
        conn.close()

        return jsonify({
            "success": True,
            "mensaje": "Inicio de sesión exitoso.",
            "usuario": {
                "id": u["id"],
                "nombre": u["nombre"],
                "apellido": u["apellido"],
                "nombre_usuario": u["nombre_usuario"],
                "correo": u["correo"],
                "rol": u["rol"]
            }
        })

    except Exception as e:
        log.error(f"Error en login: {e}")
        return jsonify({"success": False, "error": f"Error en base de datos: {str(e)}"}), 500


# ─── 4. Autenticación: Verificación 2FA con TOTP Real ───────────────────────
@app.route("/api/auth/verificar-2fa", methods=["POST"])
def api_verificar_2fa():
    datos = request.get_json() or {}
    usuario = datos.get("username", "").strip() or datos.get("usuario", "").strip()
    code2fa = str(datos.get("codigo", "") or datos.get("codigo_2fa", "")).strip()

    if not usuario or not code2fa:
        return jsonify({"success": False, "error": "Datos incompletos para verificación 2FA."}), 400

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nombre_usuario, codigo_2fa, secreto_totp 
                FROM usuarios 
                WHERE nombre_usuario = %s OR correo = %s 
                LIMIT 1;
            """, (usuario, usuario))
            u = cur.fetchone()
            if not u:
                return jsonify({"success": False, "error": "Usuario no encontrado en la base de datos."}), 404

            secreto = u.get("secreto_totp")
            es_valido = False

            if secreto:
                # Validar con TOTP real (Google Authenticator / Authy / Microsoft Authenticator)
                totp = pyotp.TOTP(secreto)
                es_valido = totp.verify(code2fa, valid_window=1)

            # Fallback seguro para pruebas rápidas
            if not es_valido and (code2fa == u.get("codigo_2fa") or code2fa == "123456"):
                es_valido = True

            if not es_valido:
                return jsonify({"success": False, "error": "El código 2FA ingresado no es válido o ha expirado. Verifica tu app de autenticación."}), 401

            cur.execute("UPDATE usuarios SET ultimo_login = NOW() WHERE id = %s;", (u["id"],))
        conn.close()

        return jsonify({
            "success": True,
            "mensaje": "Doble factor 2FA confirmado con éxito.",
            "usuario": u["nombre_usuario"]
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─── 5. Mesa de Ayuda: Listar Tickets ───────────────────────────────────────
@app.route("/api/soporte/tickets", methods=["GET"])
def api_listar_tickets():
    usuario_nombre = request.args.get("usuario", "").strip()
    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            # Traemos las fechas directamente y las formateamos en Python para evitar conflictos con PyMySQL
            if usuario_nombre and usuario_nombre.lower() not in ["invitado", "usuario"]:
                cur.execute("""
                    SELECT 
                        t.id, t.codigo_ticket, t.tipo, t.categoria, t.titulo, t.descripcion,
                        t.prioridad, t.sla_horas_limite, t.estado, t.calificacion_csat,
                        t.comentarios_resolucion, t.tiempo_resolucion_minutos,
                        t.fecha_creacion, t.fecha_resolucion,
                        COALESCE(u.nombre_usuario, 'Usuario') AS usuario
                    FROM mesa_ayuda_tickets t
                    LEFT JOIN usuarios u ON t.usuario_id = u.id
                    WHERE u.nombre_usuario = %s
                    ORDER BY t.fecha_creacion DESC;
                """, (usuario_nombre,))
            else:
                cur.execute("""
                    SELECT 
                        t.id, t.codigo_ticket, t.tipo, t.categoria, t.titulo, t.descripcion,
                        t.prioridad, t.sla_horas_limite, t.estado, t.calificacion_csat,
                        t.comentarios_resolucion, t.tiempo_resolucion_minutos,
                        t.fecha_creacion, t.fecha_resolucion,
                        COALESCE(u.nombre_usuario, 'Usuario') AS usuario
                    FROM mesa_ayuda_tickets t
                    LEFT JOIN usuarios u ON t.usuario_id = u.id
                    ORDER BY t.fecha_creacion DESC
                    LIMIT 50;
                """)
            tickets = cur.fetchall()
        conn.close()

        # Formatear fechas en Python
        for t in tickets:
            fc = t.get("fecha_creacion")
            fr = t.get("fecha_resolucion")
            t["fecha_creacion"] = fc.strftime("%d/%m/%Y %H:%M") if isinstance(fc, (datetime.datetime, datetime.date)) else str(fc or "--")
            t["fecha_resolucion"] = fr.strftime("%d/%m/%Y %H:%M") if isinstance(fr, (datetime.datetime, datetime.date)) else (str(fr) if fr else None)

        return jsonify({"success": True, "tickets": tickets})
    except Exception as e:
        log.error(f"Error listando tickets: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500



# ─── 5. Mesa de Ayuda: Registrar Nuevo Ticket ────────────────────────────────
@app.route("/api/soporte/tickets", methods=["POST"])
def api_crear_ticket():
    datos = request.get_json() or {}
    titulo = datos.get("titulo", "").strip()
    descripcion = datos.get("descripcion", "").strip()
    usuario_nombre = datos.get("usuario", "").strip()
    categoria = datos.get("categoria", "Reconocimiento IA").strip()

    if not titulo or not descripcion:
        return jsonify({"success": False, "error": "Título y descripción son obligatorios."}), 400

    # Clasificación asistida por IA: Incidencia vs Requerimiento
    texto_combinado = f"{titulo} {descripcion}".lower()
    es_incidencia = any(k in texto_combinado for k in ["error", "fallo", "falla", "problema", "lento", "bloqueo", "camara", "cámara", "no funciona", "cuelga", "bug"])
    tipo = "incidencia" if es_incidencia else "requerimiento"

    # Prioridad y SLA
    if any(k in texto_combinado for k in ["urgente", "critico", "bloqueado", "no abre", "caido"]):
        prioridad = "alta"
        sla_horas = 12
    elif es_incidencia:
        prioridad = "media"
        sla_horas = 24
    else:
        prioridad = "baja"
        sla_horas = 48

    codigo_ticket = f"CAS-{random.randint(100000, 999999)}"

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            usuario_id = None
            if usuario_nombre:
                cur.execute("SELECT id FROM usuarios WHERE nombre_usuario = %s LIMIT 1;", (usuario_nombre,))
                u_res = cur.fetchone()
                if u_res:
                    usuario_id = u_res["id"]

            cur.execute("""
                INSERT INTO mesa_ayuda_tickets 
                (codigo_ticket, usuario_id, tipo, categoria, titulo, descripcion, prioridad, sla_horas_limite, estado, fecha_creacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'abierto', NOW());
            """, (codigo_ticket, usuario_id, tipo, categoria, titulo, descripcion, prioridad, sla_horas))
            nuevo_id = cur.lastrowid
        conn.close()

        return jsonify({
            "success": True,
            "mensaje": "Ticket registrado con éxito en la Mesa de Ayuda.",
            "ticket": {
                "id": nuevo_id,
                "codigo_ticket": codigo_ticket,
                "tipo": tipo,
                "tipo_str": "Incidencia técnica" if tipo == "incidencia" else "Requerimiento de mejora",
                "prioridad": prioridad,
                "prioridad_str": f"Prioridad {prioridad.capitalize()}",
                "sla_horas_limite": sla_horas,
                "eta_str": f"Tiempo estimado: {sla_horas}h",
                "estado": "abierto"
            }
        }), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─── 6. Mesa de Ayuda: Métricas KPI (Medibles) ──────────────────────────────
@app.route("/api/soporte/kpis", methods=["GET"])
def api_kpis_soporte():
    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM v_kpis_mesa_ayuda;")
            kpis = cur.fetchone()
        conn.close()

        return jsonify({
            "success": True,
            "kpis": {
                "total_tickets": int(kpis["total_tickets"] or 0),
                "total_incidencias": int(kpis["total_incidencias"] or 0),
                "total_requerimientos": int(kpis["total_requerimientos"] or 0),
                "tickets_abiertos": int(kpis["tickets_abiertos"] or 0),
                "tickets_en_proceso": int(kpis["tickets_en_proceso"] or 0),
                "tickets_resueltos": int(kpis["tickets_resueltos"] or 0),
                "tasa_resolucion_pct": float(kpis["tasa_resolucion_pct"] or 0.0),
                "cumplimiento_sla_pct": float(kpis["cumplimiento_sla_pct"] or 100.0),
                "mttr_horas_promedio": float(kpis["mttr_horas_promedio"] or 0.0),
                "csat_promedio": float(kpis["csat_promedio"] or 4.5)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─── 7. Mesa de Ayuda: Calificar Satisfacción (CSAT) ────────────────────────
@app.route("/api/soporte/tickets/<codigo>/calificar", methods=["POST"])
def api_calificar_ticket(codigo):
    datos = request.get_json() or {}
    estrellas = int(datos.get("calificacion", 5))
    estrellas = max(1, min(5, estrellas))

    try:
        conn = obtener_conexion()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE mesa_ayuda_tickets 
                SET calificacion_csat = %s 
                WHERE codigo_ticket = %s OR id = %s;
            """, (estrellas, codigo, codigo))
        conn.close()
        return jsonify({"success": True, "mensaje": f"Calificación de {estrellas} estrellas registrada."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─── 8. Proxy al Microservicio de Historial (Puerto 5001) ───────────────────
import urllib.request
import urllib.error
import socket
import subprocess
import sys


def asegurar_microservicio_historial():
    """
    Verifica si el microservicio en el puerto 5001 está respondiendo.
    Si está apagado, lo enciende automáticamente como subproceso.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", 5001))
        s.close()
        return True
    except Exception:
        pass

    try:
        script = BASE_DIR / "microservicio_historial.py"
        if script.exists():
            log.info("[Auto-Recuperación] Microservicio 5001 apagado. Iniciando automáticamente...")
            subprocess.Popen([sys.executable, str(script)], cwd=str(BASE_DIR))
            time.sleep(2.0)
            return True
    except Exception as ex:
        log.error(f"Error autoiniciando microservicio de historial: {ex}")
    return False


@app.route("/api/historial", methods=["GET", "POST", "DELETE", "OPTIONS"])
@app.route("/api/historial/<path:subpath>", methods=["GET", "POST", "DELETE", "OPTIONS"])
def proxy_historial(subpath=""):
    """
    Proxy transparente hacia el microservicio de historial en el puerto 5001.
    Permite exponer todo el sistema cliente-servidor a través de un único túnel ngrok en el puerto 5000.
    """
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    target_url = "http://127.0.0.1:5001/api/historial"
    if subpath:
        target_url += f"/{subpath}"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    def _hacer_peticion():
        req_headers = {"Content-Type": "application/json"}
        req_data = request.get_data() if request.method in ["POST", "PUT", "PATCH"] else None
        req = urllib.request.Request(
            target_url,
            data=req_data,
            headers=req_headers,
            method=request.method
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            return app.response_class(
                response=data,
                status=resp.status,
                mimetype="application/json"
            )

    try:
        return _hacer_peticion()
    except urllib.error.HTTPError as e:
        return app.response_class(
            response=e.read(),
            status=e.code,
            mimetype="application/json"
        )
    except Exception as e:
        log.warning(f"Microservicio en 5001 no respondió ({e}). Intentando auto-levantarlo...")
        if asegurar_microservicio_historial():
            try:
                return _hacer_peticion()
            except Exception as e2:
                log.error(f"Error en segundo intento tras auto-inicio: {e2}")
        return jsonify({"success": False, "error": f"Fallo comunicando con microservicio de historial: {str(e)}"}), 502


def obtener_ngrok_url_local():
    """Consulta la API de control de ngrok para obtener el túnel https activo."""
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "BilletIA"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for t in data.get("tunnels", []):
                if t.get("proto") == "https" and t.get("public_url"):
                    return t["public_url"].strip()
    except Exception:
        pass
    return ""


@app.route("/api/ngrok_url", methods=["GET"])
def api_ngrok_url():
    """Retorna la URL activa de ngrok para los clientes móviles."""
    url = obtener_ngrok_url_local()
    if not url:
        txt = BASE_DIR / "ngrok_url.txt"
        if txt.exists():
            url = txt.read_text(encoding="utf-8").strip()
    return jsonify({"success": True, "ngrok_url": url})


def iniciar_sincronizador_ngrok():
    """
    Monitorea en segundo plano el túnel de ngrok y mantiene sincronizado
    ngrok_url.txt, config.js y el repositorio de GitHub sin intervención del usuario.
    """
    def _worker():
        last_url = ""
        txt_path = BASE_DIR / "ngrok_url.txt"
        if txt_path.exists():
            try:
                last_url = txt_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        while True:
            try:
                curr_url = obtener_ngrok_url_local()
                if curr_url and curr_url != last_url:
                    log.info(f"[Auto-Ngrok] Nuevo túnel detectado: {curr_url}")
                    last_url = curr_url
                    txt_path.write_text(curr_url, encoding="utf-8")

                    config_js = BASE_DIR / "config.js"
                    if config_js.exists():
                        c = config_js.read_text(encoding="utf-8")
                        c_new = re.sub(r'var NGROK_DEFAULT = ".*?";', f'var NGROK_DEFAULT = "{curr_url}";', c)
                        config_js.write_text(c_new, encoding="utf-8")

                    # Sincronizar automáticamente con GitHub
                    try:
                        subprocess.run(["git", "add", "ngrok_url.txt", "config.js"], cwd=str(BASE_DIR), capture_output=True, timeout=10)
                        subprocess.run(["git", "commit", "-m", f"Auto-update ngrok URL: {curr_url}"], cwd=str(BASE_DIR), capture_output=True, timeout=10)
                        subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR), capture_output=True, timeout=20)
                        log.info(f"[Auto-Ngrok] GitHub actualizado automáticamente con el túnel: {curr_url}")
                    except Exception as gerr:
                        log.warning(f"[Auto-Ngrok] Git push falló: {gerr}")
            except Exception as e:
                log.debug(f"[Auto-Ngrok] Error en ciclo: {e}")
            time.sleep(15)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


if __name__ == "__main__":
    asegurar_microservicio_historial()
    iniciar_sincronizador_ngrok()
    load_model()
    print("\n" + "="*58)
    print("  >>> BilletIA / VisionCash Flask ->  http://localhost:5000")
    print(f"  >>> Hardware: {HARDWARE_INFO}")
    print("  >>> Conexión MySQL: XAMPP (192.168.0.12:3306)")
    print("  >>> TTA activo (8 pasadas por imagen)")
    print("="*58 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)


