#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SCRIPT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${MORDECAI_INSTALL_ROOT:-$(cd "${SCRIPT_HOME}/.." && pwd)}"
ENV_FILE="${INSTALL_ROOT}/.env"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
  set +a
fi

BACKEND_DIR="${MORDECAI_WORKSPACE_DIR:-${INSTALL_ROOT}/backend}"
ENV_DIR="${INSTALL_ROOT}/env"
SCRIPT_DIR="${INSTALL_ROOT}/scripts"

if [ ! -d "${BACKEND_DIR}/.git" ]; then
  printf '%s\n' "Backend checkout not found at ${BACKEND_DIR}. Run scripts/proot-setup.sh first." >&2
  exit 1
fi

git -C "${BACKEND_DIR}" pull --ff-only

# shellcheck disable=SC1090
. "${ENV_DIR}/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e "${BACKEND_DIR}"

mkdir -p "${SCRIPT_DIR}"
for script_name in proot-setup.sh start.sh stop.sh termux_boot.sh update.sh; do
  cp "${BACKEND_DIR}/scripts/${script_name}" "${SCRIPT_DIR}/${script_name}"
  chmod 755 "${SCRIPT_DIR}/${script_name}"
done

printf '%s\n' 'Mordecai backend updated.'