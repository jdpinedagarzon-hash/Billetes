"""
microservicio_historial.py - Punto de entrada del Microservicio de Historial (Puerto 5001)
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from componentes_transversales.monitoreo.microservicio_historial import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
