#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT_DIR="${HOME}/mordecai"

pkg update -y
pkg upgrade -y
pkg install -y git python tur-repo proot-distro

mkdir -p "$ROOT_DIR"

if [ ! -d "$ROOT_DIR/.git" ]; then
  git clone https://github.com/smokydastona/Mordecai-AI-Android.git "$ROOT_DIR"
fi

cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]

printf '%s\n' 'Sandbox bootstrap complete. Start the runtime with scripts/termux_boot.sh.'