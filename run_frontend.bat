@echo off
title AI Border Surveillance - Frontend Command Center
echo ========================================================
echo   AI Border Surveillance System (SIH26187) - Frontend
echo   Team: AI Avengers
echo ========================================================
echo.
cd /d "%~dp0\frontend"
echo Starting Vite Dev Server on port 5173...
npm run dev
pause
