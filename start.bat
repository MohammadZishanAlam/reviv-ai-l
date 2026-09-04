@echo off
title Reviv-AI-l Backend Server
cd /d "%~dp0"

echo =======================================================
echo    Reviv-AI-l: Autonomous Payment Failure Recovery
echo    Razorpay AI Buildathon 2026 - Track 3
echo =======================================================
echo.

:: Check if virtual environment exists
if not exist ".venv\Scripts\uvicorn.exe" (
    echo [*] Creating virtual environment and installing dependencies...
    python -m venv .venv
    call .venv\Scripts\pip.exe install -r requirements.txt
)

echo [*] Starting FastAPI Backend on http://127.0.0.1:8000 ...
echo [*] Opening your browser in 2 seconds...

start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: Start Uvicorn
.\.venv\Scripts\uvicorn.exe src.main:app --reload --host 127.0.0.1 --port 8000

pause
