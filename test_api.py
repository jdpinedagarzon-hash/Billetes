import requests
from pathlib import Path

def test_api():
    print("=" * 60)
    print("PROBANDO ENDPOINTS DE LA API REST (FLASK + MOBILENETV2)")
    print("=" * 60)
    
    # 1. Health check
    status = requests.get("http://127.0.0.1:5000/api/status").json()
    print(f"Estado del Servidor: {status.get('hardware')} | Clases: {status.get('classes_count')}")
    
    # 2. Inferencia por clase
    data_dir = Path("D:/proyecto/Fotos billetes")
    for folder in sorted(data_dir.iterdir()):
        if folder.is_dir():
            img_path = next(folder.glob("*.jpg"), None)
            if img_path:
                with open(img_path, "rb") as f:
                    res = requests.post("http://127.0.0.1:5000/api/predict", files={"file": f})
                    data = res.json()
                    pred = data["prediction"]
                    lat = data["latency_ms"]
                    print(f"Carpeta: {folder.name:8} -> {pred['display_summary']:32} | Latencia: {lat} ms")
    
    print("=" * 60)
    print("PRUEBAS COMPLETADAS CON ÉXITO")

if __name__ == "__main__":
    test_api()
