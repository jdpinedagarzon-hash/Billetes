# -*- coding: utf-8 -*-
"""
Componentes Transversales - Configuración del Sistema
Define parámetros globales, puertos y rutas del ecosistema VisionCash.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
PORT_PRINCIPAL = int(os.environ.get("VISIONCASH_PORT", 5000))
PORT_HISTORIAL = int(os.environ.get("HISTORIAL_PORT", 5001))
DB_HOST = os.environ.get("DB_HOST", "192.168.0.12")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "visioncash_db")

MODEL_PATH = BASE_DIR / "visioncash" / "motor_ia" / "modelos_entrenados" / "banknote_efficientnetv2s.pt"
CLASSES_PATH = BASE_DIR / "visioncash" / "motor_ia" / "modelos_entrenados" / "classes.json"
