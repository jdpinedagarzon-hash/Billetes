# ==============================================================================
# actualizar_ngrok.ps1 - Sincronizador Automático de ngrok con GitHub & App Móvil
# ==============================================================================

$ErrorActionPreference = "Continue"
$projectDir = "d:\proyecto\Lo que hay en google"
Set-Location -Path $projectDir

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   VISIONCASH / BILLETES - SINCRONIZADOR DE NGROK       " -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Comprobar si ngrok ya está corriendo
$ngrokProc = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if (-not $ngrokProc) {
    $ngrokExe = "$PSScriptRoot\ngrok.exe"
    if (-not (Test-Path $ngrokExe)) { $ngrokExe = "$projectDir\ngrok.exe" }
    Start-Process -FilePath $ngrokExe -ArgumentList "http 5000" -WindowStyle Minimized
    Start-Sleep -Seconds 4
} else {
    Write-Host "[OK] ngrok ya se encuentra en ejecucion." -ForegroundColor Green
}

# 2. Consultar la API local de ngrok para obtener la URL pública
$publicUrl = ""
$maxRetries = 10
$retry = 0

while ($retry -lt $maxRetries -and [string]::IsNullOrEmpty($publicUrl)) {
    try {
        $apiRes = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3 -ErrorAction Stop
        $tunnel = $apiRes.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
        if ($tunnel -and $tunnel.public_url) {
            $publicUrl = $tunnel.public_url.Trim()
        }
    } catch {
        Start-Sleep -Seconds 1
    }
    $retry++
}

if ([string]::IsNullOrEmpty($publicUrl)) {
    Write-Host "`n[ERROR] No se pudo obtener la URL de ngrok." -ForegroundColor Red
    Write-Host "Verifica que ngrok.exe este autenticado con tu token gratuito." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[OK] URL publica de ngrok detectada: $publicUrl" -ForegroundColor Green

# 3. Guardar en ngrok_url.txt (en configuracion, vistas y raiz)
$utf8 = New-Object System.Text.UTF8Encoding $false
$ngrokTxtPath = "$projectDir\componentes_transversales\configuracion\ngrok_url.txt"
$ngrokTxtVistas = "$projectDir\presentacion\codigo_fuente\vistas\ngrok_url.txt"
$ngrokTxtRoot = "$projectDir\ngrok_url.txt"

[System.IO.File]::WriteAllText($ngrokTxtPath, $publicUrl, $utf8)
[System.IO.File]::WriteAllText($ngrokTxtVistas, $publicUrl, $utf8)
[System.IO.File]::WriteAllText($ngrokTxtRoot, $publicUrl, $utf8)
Write-Host "[OK] ngrok_url.txt actualizado en configuracion y vistas." -ForegroundColor Green

# 4. Actualizar config.js
$configPaths = @(
    "$projectDir\config.js",
    "$projectDir\presentacion\codigo_fuente\servicios_api\config.js",
    "$projectDir\presentacion\codigo_fuente\vistas\config.js"
)
foreach ($cfg in $configPaths) {
    if (Test-Path $cfg) {
        $content = [System.IO.File]::ReadAllText($cfg)
        $pattern = 'var NGROK_DEFAULT = ".*?";'
        $replacement = 'var NGROK_DEFAULT = "' + $publicUrl + '";'
        $newContent = [System.Text.RegularExpressions.Regex]::Replace($content, $pattern, $replacement)
        [System.IO.File]::WriteAllText($cfg, $newContent, $utf8)
        Write-Host "[OK] config.js actualizado: $cfg" -ForegroundColor Green
    }
}

# 5. Subir a GitHub
Write-Host ""
Write-Host "[*] Sincronizando con repositorio GitHub..." -ForegroundColor Cyan

# Traer posibles cambios remotos con rebase para evitar rechazos si el repo cambio remotamente
git pull --rebase origin main

git add ngrok_url.txt componentes_transversales/configuracion/ngrok_url.txt presentacion/codigo_fuente/vistas/ngrok_url.txt presentacion/codigo_fuente/servicios_api/config.js presentacion/codigo_fuente/vistas/config.js

$staged = git diff --cached --name-only
if ($staged) {
    $commitMsg = "Auto-update ngrok URL: " + $publicUrl
    git commit -m $commitMsg
}

# Empujar cambios a GitHub
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "   SINCRONIZACION EXITOSA!                              " -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "Tu servidor esta activo en: $publicUrl" -ForegroundColor Yellow
    Write-Host "El APK de Android ya se conectara solo a esta URL." -ForegroundColor White
    Write-Host "GitHub Pages tambien quedo actualizado." -ForegroundColor White
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "`n[!] Se guardo localmente pero fallo git push." -ForegroundColor Yellow
}