# -*- coding: utf-8 -*-
"""
Capa de Lógica de Negocio - Gestión de Usuarios & Seguridad 2FA
Reglas de autenticación, hash seguro y validación TOTP (Google Authenticator).
"""
import hashlib
import pyotp

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verificar_password(password_plana: str, hash_almacenado: str) -> bool:
    return hash_password(password_plana) == hash_almacenado

def generar_secreto_2fa() -> str:
    return pyotp.random_base32()

def validar_codigo_totp(secreto: str, codigo: str) -> bool:
    try:
        totp = pyotp.TOTP(secreto)
        return totp.verify(str(codigo).strip(), valid_window=1)
    except Exception:
        return False
