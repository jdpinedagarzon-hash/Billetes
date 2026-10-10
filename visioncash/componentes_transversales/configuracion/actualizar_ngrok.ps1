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
    Write-Host "[*] Iniciando ngrok en el puerto 5000..." -ForegroundColor Cyan
    Start-Process -FilePath "$projectDir\ngrok.exe" -ArgumentList "http 5000" -WindowStyle Minimized
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

# 3. Guardar en ngrok_url.txt
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText("$projectDir\ngrok_url.txt", $publicUrl, $utf8)
Write-Host "[OK] ngrok_url.txt actualizado con la nueva URL." -ForegroundColor Green

# 4. Actualizar config.js
$configJsPath = "$projectDir\config.js"
if (Test-Path $configJsPath) {
    $content = [System.IO.File]::ReadAllText($configJsPath)
    $pattern = 'var NGROK_DEFAULT = ".*?";'
    $replacement = 'var NGROK_DEFAULT = "' + $publicUrl + '";'
    $newContent = [System.Text.RegularExpressions.Regex]::Replace($content, $pattern, $replacement)
    [System.IO.File]::WriteAllText($configJsPath, $newContent, $utf8)
    Write-Host "[OK] config.js actualizado." -ForegroundColor Green
}

# 5. Subir a GitHub
Write-Host ""
Write-Host "[*] Sincronizando con GitHub..." -ForegroundColor Cyan
git add ngrok_url.txt config.js
$commitMsg = "Auto-update ngrok URL: " + $publicUrl
git commit -m $commitMsg
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