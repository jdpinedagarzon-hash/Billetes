# -*- coding: utf-8 -*-
"""
Capa de Lógica de Negocio - Procesamiento de Imágenes
Auto-recorte de billetes, detección de orientación horizontal y Test-Time Augmentation (TTA).
"""
import io
import numpy as np
from PIL import Image, ImageOps

def decodificar_imagen(bytes_imagen):
    img = Image.open(io.BytesIO(bytes_imagen))
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    if max(img.size) > 960:
        img.thumbnail((960, 960), Image.Resampling.BILINEAR)
    return img

def auto_recortar_billete(img_pil):
    arr = np.array(img_pil)
    h, w = arr.shape[:2]
    # Si la imagen es vertical, rotar 90 grados para orientación canónica horizontal
    if h > w:
        return img_pil.rotate(90, expand=True)
    return img_pil
