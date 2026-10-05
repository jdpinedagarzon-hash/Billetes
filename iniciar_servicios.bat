@echo off
title VisionCash - Lanzador de Sistema y Microservicio
color 0B
echo ============================================================================
echo            VISIONCASH - SISTEMA DE RECONOCIMIENTO & MICROSERVICIOS
echo ============================================================================
echo.
echo [*] Conectando a Base de Datos MySQL en XAMPP (192.168.0.12:3306)...
echo.
echo [1/2] Levantando Microservicio de Historial & Metricas en Puerto 5001...
start "VisionCash - Microservicio Historial [Puerto 5001]" cmd /k "python microservicio_historial.py"

timeout /t 2 /nobreak >nul

echo [2/2] Levantando Servidor Principal Flask & IA en Puerto 5000...
start "VisionCash - Servidor Principal & IA [Puerto 5000]" cmd /k "python app.py"

echo.
echo ============================================================================
echo   ENLACES DISPONIBLES:
echo   1. Aplicacion Web:       http://localhost:5000/Menu_principal.html
echo   2. Registro de Usuario:  http://localhost:5000/Menu_principal_3.html
echo   3. Iniciar Sesion:       http://localhost:5000/Menu_principal_2.html
echo   4. Mesa de Ayuda & KPIs: http://localhost:5000/Soporte.html
echo   5. Microservicio API:    http://localhost:5001/api/historial/metricas
echo   6. Base de Datos XAMPP:  http://192.168.0.12/phpmyadmin/
echo ============================================================================
echo.
pause
