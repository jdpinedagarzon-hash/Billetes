# -*- coding: utf-8 -*-
"""
Componentes Transversales - Respaldos de Base de Datos
Genera copias de seguridad de la base de datos MySQL (visioncash_db).
"""
import os
import time
import subprocess
from pathlib import Path

def realizar_backup():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_file = Path(__file__).resolve().parent / f"backup_visioncash_{timestamp}.sql"
    cmd = ["mysqldump", "-u", "root", "-h", "192.168.0.12", "visioncash_db"]
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            subprocess.run(cmd, stdout=f, check=True)
        print(f"[Backup] Respaldo exitoso en: {backup_file}")
    except Exception as e:
        print(f"[Backup] No se pudo realizar el volcado automático: {e}")

if __name__ == "__main__":
    realizar_backup()
