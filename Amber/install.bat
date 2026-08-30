@echo off
REM ============================================
REM  Instalacja Amber (Windows)
REM ============================================
chcp 65001 >nul
echo [Amber] Sprawdzam Pythona...
python --version >nul 2>&1
if errorlevel 1 (
    echo [BLAD] Nie znaleziono Pythona. Zainstaluj Python 3.10+ z https://www.python.org
    pause
    exit /b 1
)

echo [Amber] Tworze wirtualne srodowisko...
python -m venv .venv
call .venv\Scripts\activate.bat

echo [Amber] Instaluje zaleznosci...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [OK] Amber gotowa! Uruchom przez:  start_amber.bat
pause
