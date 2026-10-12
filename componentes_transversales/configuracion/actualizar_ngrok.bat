@echo off
title VisionCash - Sincronizar ngrok con GitHub & App
color 0A
cd /d "d:\proyecto\Lo que hay en google"
powershell -NoProfile -ExecutionPolicy Bypass -File "actualizar_ngrok.ps1"
echo.
pause
