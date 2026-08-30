@echo off
REM ============================================
REM  Start Amber (Windows)
REM ============================================
chcp 65001 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [Info] Brak .venv — uzyje systemowego Pythona.
)

python run.py
pause
