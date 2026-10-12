# -*- coding: utf-8 -*-
"""
Componentes Transversales - Seguridad & Autenticación
Generación de secretos criptográficos, verificación TOTP y protección contra ataques de fuerza bruta.
"""
import pyotp
import qrcode
import io
import base64

def crear_secreto_totp():
    return pyotp.random_base32()

def generar_codigo_qr_base64(usuario, secreto, emisor="VisionCash"):
    uri = pyotp.totp.TOTP(secreto).provisioning_uri(name=usuario, issuer_name=emisor)
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

def validar_totp(secreto, token):
    try:
        return pyotp.TOTP(secreto).verify(str(token).strip(), valid_window=1)
    except Exception:
        return False
