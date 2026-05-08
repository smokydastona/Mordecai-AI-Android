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

INSTALL_ROOT="${MORDECAI_INSTALL_ROOT:-${INSTALL_ROOT}}"
BACKEND_DIR="${MORDECAI_WORKSPACE_DIR:-${INSTALL_ROOT}/backend}"
ENV_DIR="${INSTALL_ROOT}/env"
DATA_DIR="${MORDECAI_DATA_DIR:-${INSTALL_ROOT}/data}"
STATE_DIR="${MORDECAI_STATE_DIR:-${DATA_DIR}/state}"
LOG_DIR="${MORDECAI_LOG_DIR:-${DATA_DIR}/logs}"
PID_FILE="${LOG_DIR}/backend.pid"
LOG_FILE="${LOG_DIR}/backend.log"

mkdir -p "${DATA_DIR}" "${STATE_DIR}" "${LOG_DIR}"

if [ ! -d "${BACKEND_DIR}" ]; then
  printf '%s\n' "Backend directory not found at ${BACKEND_DIR}. Run scripts/proot-setup.sh first." >&2
  exit 1
fi

if [ ! -x "${ENV_DIR}/bin/python" ]; then
  printf '%s\n' "Python environment not found at ${ENV_DIR}. Run scripts/proot-setup.sh first." >&2
  exit 1
fi

if [ -f "${PID_FILE}" ]; then
  existing_pid="$(cat "${PID_FILE}")"
  if [ -n "${existing_pid}" ] && kill -0 "${existing_pid}" 2>/dev/null; then
    printf 'Mordecai is already running at http://127.0.0.1:%s (pid %s).\n' "${MORDECAI_SERVICE_PORT:-8000}" "${existing_pid}"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

export MORDECAI_INSTALL_ROOT="${INSTALL_ROOT}"
export MORDECAI_WORKSPACE_DIR="${BACKEND_DIR}"
export MORDECAI_DATA_DIR="${DATA_DIR}"
export MORDECAI_STATE_DIR="${STATE_DIR}"
export MORDECAI_LOG_DIR="${LOG_DIR}"
export MORDECAI_MODE="${MORDECAI_MODE:-mode-a}"
export MORDECAI_SERVICE_HOST="${MORDECAI_SERVICE_HOST:-127.0.0.1}"
export MORDECAI_SERVICE_PORT="${MORDECAI_SERVICE_PORT:-8000}"
export MORDECAI_ENABLE_ANDROID_CONTROL="${MORDECAI_ENABLE_ANDROID_CONTROL:-false}"
export MORDECAI_ENABLE_ADVANCED_SELF_IMPROVEMENT="${MORDECAI_ENABLE_ADVANCED_SELF_IMPROVEMENT:-false}"
export MORDECAI_ENABLE_DAEMON_MODE="${MORDECAI_ENABLE_DAEMON_MODE:-false}"
export MORDECAI_ALLOW_GIT_PUSH="${MORDECAI_ALLOW_GIT_PUSH:-false}"

cd "${BACKEND_DIR}"
nohup "${ENV_DIR}/bin/python" -m mordecai.main >> "${LOG_FILE}" 2>&1 &
echo "$!" > "${PID_FILE}"

printf 'Mordecai started (pid %s).\n' "$(cat "${PID_FILE}")"
printf 'Dashboard: http://127.0.0.1:%s\n' "${MORDECAI_SERVICE_PORT}"
printf 'Log file: %s\n' "${LOG_FILE}"