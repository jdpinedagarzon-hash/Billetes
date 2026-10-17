@echo off
title VisionCash - Sincronizar ngrok con GitHub & App
color 0A
cd /d "%~dp0..\..\"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0actualizar_ngrok.ps1"
echo.
pause
