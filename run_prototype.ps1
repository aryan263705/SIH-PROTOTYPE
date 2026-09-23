# AI Border Surveillance Prototype - Unified Launcher
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AI Border Surveillance System (SIH26187)" -ForegroundColor Yellow
Write-Host "  Team: AI Avengers - Prototype Launcher" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start Backend in a new window
Write-Host "[1/2] Launching Backend Server on http://0.0.0.0:8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; .\venv\Scripts\Activate.ps1; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 3

# Start Frontend in a new window
Write-Host "[2/2] Launching Frontend Console on http://localhost:5173..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\frontend'; npm run dev"

Start-Sleep -Seconds 3

# Open default browser
Start-Process "http://localhost:5173"
Write-Host "`nPrototype is now LIVE! Access dashboard at: http://localhost:5173" -ForegroundColor Green
