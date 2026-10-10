@echo off
chcp 65001 >nul
echo ============================================================
echo   BilletIA - Pipeline de entrenamiento completo
echo   RTX 5060 Ti + Ryzen 5 5600 + 32GB RAM
echo   Framework: PyTorch 2.11 + CUDA 12.8
echo ============================================================
echo.
echo [PASO 1/2] Generando dataset augmentado (~5-10 min)...
echo   - 1200+ variaciones por imagen
echo   - Multiprocessing en todos los nucleos
echo.
python augment.py
if %errorlevel% neq 0 (
    echo [ERROR] Augmentacion fallo. Ver error arriba.
    pause
    exit /b 1
)
echo.
echo [PASO 2/2] Entrenando red neuronal (RTX 5060 Ti + CUDA)...
echo   - EfficientNetV2-S con Mixed Precision BF16
echo   - FASE 1: Transfer Learning (20 epocas)
echo   - FASE 2: Fine-Tuning (40 epocas)
echo.
python train.py
if %errorlevel% neq 0 (
    echo [ERROR] Entrenamiento fallo. Ver error arriba.
    pause
    exit /b 1
)
echo.
echo ============================================================
echo   PIPELINE COMPLETADO
echo   Modelo guardado en: models/banknote_efficientnetv2s.pt
echo.
echo   Ahora inicia el servidor:
echo     python app.py
echo   Y abre el navegador en:
echo     http://localhost:5000
echo ============================================================
pause
