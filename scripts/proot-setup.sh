#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if [ -z "${TERMUX_VERSION:-}" ] && [ ! -d "/data/data/com.termux/files/usr" ]; then
  printf '%s\n' 'This installer must be run from Termux.' >&2
  exit 1
fi

INSTALL_ROOT="${MORDECAI_INSTALL_ROOT:-$HOME/mordecai}"
BACKEND_DIR="${INSTALL_ROOT}/backend"
ENV_DIR="${INSTALL_ROOT}/env"
DATA_DIR="${INSTALL_ROOT}/data"
STATE_DIR="${DATA_DIR}/state"
LOG_DIR="${DATA_DIR}/logs"
CACHE_DIR="${DATA_DIR}/cache"
MODELS_DIR="${DATA_DIR}/models"
SCRIPT_DIR="${INSTALL_ROOT}/scripts"
ENV_FILE="${INSTALL_ROOT}/.env"
REPO_URL="${MORDECAI_REPO_URL:-https://github.com/smokydastona/Mordecai-AI-Android.git}"

sync_runtime_scripts() {
  local source_dir="${BACKEND_DIR}/scripts"
  mkdir -p "${SCRIPT_DIR}"
  for script_name in proot-setup.sh start.sh stop.sh termux_boot.sh update.sh; do
    if [ -f "${source_dir}/${script_name}" ]; then
      cp "${source_dir}/${script_name}" "${SCRIPT_DIR}/${script_name}"
      chmod 755 "${SCRIPT_DIR}/${script_name}"
    fi
  done
}

write_env_file() {
  if [ -f "${ENV_FILE}" ]; then
    return
  fi
  cat > "${ENV_FILE}" <<EOF
MORDECAI_INSTALL_ROOT=${INSTALL_ROOT}
MORDECAI_WORKSPACE_DIR=${BACKEND_DIR}
MORDECAI_DATA_DIR=${DATA_DIR}
MORDECAI_STATE_DIR=${STATE_DIR}
MORDECAI_LOG_DIR=${LOG_DIR}
MORDECAI_CACHE_DIR=${CACHE_DIR}
MORDECAI_MODELS_DIR=${MODELS_DIR}
MORDECAI_MODE=mode-a
MORDECAI_SERVICE_HOST=127.0.0.1
MORDECAI_SERVICE_PORT=8000
MORDECAI_ENABLE_ANDROID_CONTROL=false
MORDECAI_ENABLE_ADVANCED_SELF_IMPROVEMENT=false
MORDECAI_ENABLE_DAEMON_MODE=false
MORDECAI_ALLOW_GIT_PUSH=false
EOF
}

printf '%s\n' 'Updating Termux packages and installing Mordecai prerequisites...'
pkg update -y
pkg upgrade -y
pkg install -y git python curl proot-distro

mkdir -p "${INSTALL_ROOT}" "${DATA_DIR}" "${STATE_DIR}" "${LOG_DIR}" "${CACHE_DIR}" "${MODELS_DIR}" "${SCRIPT_DIR}"

if [ -d "${BACKEND_DIR}/.git" ]; then
  printf '%s\n' 'Updating existing Mordecai checkout...'
  git -C "${BACKEND_DIR}" pull --ff-only
elif [ -e "${BACKEND_DIR}" ]; then
  printf '%s\n' "${BACKEND_DIR} exists but is not a git checkout. Move it aside and rerun the installer." >&2
  exit 1
else
  printf '%s\n' 'Cloning Mordecai backend...'
  git clone "${REPO_URL}" "${BACKEND_DIR}"
fi

if [ ! -d "${ENV_DIR}" ]; then
  printf '%s\n' 'Creating Python environment...'
  python -m venv "${ENV_DIR}"
fi

# shellcheck disable=SC1090
. "${ENV_DIR}/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e "${BACKEND_DIR}"

write_env_file
sync_runtime_scripts

printf '\n%s\n' 'Mordecai Phase 1 install complete.'
printf 'Install root: %s\n' "${INSTALL_ROOT}"
printf 'Backend: %s\n' "${BACKEND_DIR}"
printf 'Data: %s\n' "${DATA_DIR}"
printf 'Start command: %s\n' "${SCRIPT_DIR}/start.sh"
printf 'Dashboard URL: %s\n' 'http://127.0.0.1:8000'