@echo off
title AI Border Surveillance - Backend Server
echo ========================================================
echo   AI Border Surveillance System (SIH26187) - Backend
echo   Team: AI Avengers
echo ========================================================
echo.
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting FastAPI & Computer Vision Pipeline on port 8000...
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
