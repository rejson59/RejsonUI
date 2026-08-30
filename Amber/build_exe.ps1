# ============================================
#  Budowa .exe (Windows PowerShell)
#  Uruchom PO instalacji zależności.
# ============================================
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .venv\Scripts\Activate.ps1
}

Write-Host "[Amber] Instaluje PyInstaller..."
python -m pip install pyinstaller

Write-Host "[Amber] Buduje Amber.exe ..."
python -m PyInstaller --noconfirm --clean Amber.spec

Write-Host ""
Write-Host "[OK] Gotowe! dist\Amber\Amber.exe"
