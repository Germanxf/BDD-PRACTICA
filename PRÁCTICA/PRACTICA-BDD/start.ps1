# start.ps1 — Arrancar el proyecto 2PC en Windows
param([switch]$Fallo)

$env:MODO_FALLO = if ($Fallo) { "1" } else { "0" }

Write-Host ""
Write-Host "══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Práctica 2PC — Transacciones Distribuidas" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "  Levantando contenedores Docker..." -ForegroundColor Yellow
docker compose up --build -d

Write-Host ""
Write-Host "  Esperando que los servicios estén listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

Write-Host ""
Write-Host "  Abriendo interfaz gráfica..." -ForegroundColor Green
python interfaz/interfaz_2pc.py
