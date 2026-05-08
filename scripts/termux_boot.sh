#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT_DIR="${HOME}/mordecai"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m uvicorn mordecai.main:app --host 0.0.0.0 --port 8000
