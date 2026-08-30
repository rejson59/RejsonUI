#!/usr/bin/env bash
# ============================================
#  Start Amber (macOS / Linux)
# ============================================
cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 run.py
