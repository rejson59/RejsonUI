@echo off
REM ============================================
REM  Budowa pliku .exe (Windows) — PyInstaller
REM  Uruchom PO instalacji zależności (install.bat)
REM ============================================
chcp 65001 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

echo [Amber] Instaluje PyInstaller (jesli brak)...
pip install pyinstaller

echo [Amber] Buduje Amber.exe ...
pyinstaller --noconfirm --clean Amber.spec

echo.
echo [OK] Gotowe! Plik znajdziesz w katalogu: dist\Amber\Amber.exe
pause
