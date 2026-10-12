@echo off
title VisionCash - Lanzador de Sistema y Microservicio
color 0B
echo ============================================================================
echo            VISIONCASH - SISTEMA DE RECONOCIMIENTO & MICROSERVICIOS
echo ============================================================================
echo.
echo [*] Conectando a Base de Datos MySQL en XAMPP (192.168.0.12:3306)...
echo.

cd /d "%~dp0"

echo [1/3] Levantando Microservicio de Historial y Metricas en Puerto 5001...
start "VisionCash - Microservicio Historial [Puerto 5001]" cmd /k "python microservicio_historial.py"

timeout /t 2 /nobreak >nul

echo [2/3] Levantando Servidor Principal Flask e IA en Puerto 5000...
start "VisionCash - Servidor Principal e IA [Puerto 5000]" cmd /k "python app.py"

timeout /t 3 /nobreak >nul

echo [3/3] Iniciando tunel ngrok en Puerto 5000...
start "VisionCash - Tunel ngrok" cmd /k "ngrok.exe http 5000"

echo.
echo ============================================================================
echo   ENLACES DISPONIBLES:
echo   1. Aplicacion Web Local:   http://localhost:5000/Menu_principal.html
echo   2. GitHub Pages (Web):     https://jdpinedagarzon-hash.github.io/Billetes/
echo   3. Registro de Usuario:    http://localhost:5000/Menu_principal_3.html
echo   4. Iniciar Sesion:         http://localhost:5000/Menu_principal_2.html
echo   5. Mesa de Ayuda y KPIs:   http://localhost:5000/Soporte.html
echo   6. Microservicio API:      http://localhost:5001/api/historial/metricas
echo   7. Base de Datos XAMPP:    http://192.168.0.12/phpmyadmin/
echo ============================================================================
echo.
echo [OK] Todos los servicios han sido iniciados.
echo      El tunel ngrok se actualiza automaticamente en GitHub cada 15 segundos.
echo.
pause
