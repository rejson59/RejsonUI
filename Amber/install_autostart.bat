@echo off
REM ============================================
REM  Autostart Amber przy włączaniu laptopa (Windows)
REM  Dodaje wpis do rejestru (HKCU\...\Run).
REM ============================================
chcp 65001 >nul
cd /d "%~dp0"

set KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run
set VBS=%~dp0amber_autostart.vbs

echo [Amber] Dodaje wpis autostartu...
reg add "%KEY%" /v "Amber" /t REG_SZ /d "wscript.exe \"%VBS%\"" /f

echo.
echo [OK] Amber bedzie uruchamiac sie przy logowaniu.
echo [Info] Aby usunac autostart:  reg delete "%KEY%" /v "Amber" /f
pause
