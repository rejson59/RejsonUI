#!/usr/bin/env bash
# ============================================
#  Instalacja Amber (macOS / Linux)
# ============================================
set -e
cd "$(dirname "$0")"

echo "[Amber] Sprawdzam Pythona..."
command -v python3 >/dev/null || { echo "Zainstaluj Python 3.10+."; exit 1; }

echo "[Amber] Tworzę środowisko wirtualne..."
python3 -m venv .venv
source .venv/bin/activate

echo "[Amber] Instaluję zależności..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[OK] Amber gotowa! Uruchom:  ./start_amber.sh"
