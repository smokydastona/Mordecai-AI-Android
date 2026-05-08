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

DATA_DIR="${MORDECAI_DATA_DIR:-${INSTALL_ROOT}/data}"
LOG_DIR="${MORDECAI_LOG_DIR:-${DATA_DIR}/logs}"
PID_FILE="${LOG_DIR}/backend.pid"

if [ ! -f "${PID_FILE}" ]; then
  printf '%s\n' 'Mordecai is not running.'
  exit 0
fi

pid="$(cat "${PID_FILE}")"
if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
  kill "${pid}"
  printf 'Stopped Mordecai (pid %s).\n' "${pid}"
else
  printf '%s\n' 'Mordecai was not running; removing stale PID file.'
fi
rm -f "${PID_FILE}"