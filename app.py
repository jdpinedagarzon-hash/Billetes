"""
app.py - Punto de entrada del Servidor Principal VisionCash
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from servicios_backend.iniciar_servidor import (
    app,
    load_model,
    iniciar_sincronizador_ngrok,
    asegurar_microservicio_historial,
    HARDWARE_INFO
)

if __name__ == "__main__":
    asegurar_microservicio_historial()
    iniciar_sincronizador_ngrok()
    load_model()
    print("\n" + "=" * 58)
    print("  >>> BilletIA / VisionCash Flask ->  http://localhost:5000")
    print(f"  >>> Hardware: {HARDWARE_INFO}")
    print("  >>> Conexión MySQL: XAMPP (192.168.0.12:3306)")
    print("  >>> TTA activo (8 pasadas por imagen)")
    print("=" * 58 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
