#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SCRIPT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${MORDECAI_INSTALL_ROOT:-$(cd "${SCRIPT_HOME}/.." && pwd)}"
RUNTIME_SCRIPT="${INSTALL_ROOT}/scripts/start.sh"

if [ ! -x "${RUNTIME_SCRIPT}" ]; then
  printf '%s\n' "Missing ${RUNTIME_SCRIPT}. Run scripts/proot-setup.sh first." >&2
  exit 1
fi

exec "${RUNTIME_SCRIPT}"
