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
PROOT_DISTRO="${MORDECAI_PROOT_DISTRO:-ubuntu}"

run_in_distro() {
  local command="$1"
  proot-distro login "${PROOT_DISTRO}" --shared-tmp -- /bin/bash -lc "${command}"
}

ensure_proot_distro() {
  if proot-distro login "${PROOT_DISTRO}" --shared-tmp -- /usr/bin/env true >/dev/null 2>&1; then
    return
  fi

  printf 'Installing proot distro: %s\n' "${PROOT_DISTRO}"
  proot-distro install "${PROOT_DISTRO}"
}

runtime_python_platform() {
  run_in_distro "'${ENV_DIR}/bin/python' -c 'import sysconfig; print(sysconfig.get_platform())'"
}

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
MORDECAI_PROOT_DISTRO=${PROOT_DISTRO}
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
pkg install -y git curl proot-distro

mkdir -p "${INSTALL_ROOT}" "${DATA_DIR}" "${STATE_DIR}" "${LOG_DIR}" "${CACHE_DIR}" "${MODELS_DIR}" "${SCRIPT_DIR}"

ensure_proot_distro

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

printf '%s\n' 'Preparing Linux runtime inside proot...'
run_in_distro 'export DEBIAN_FRONTEND=noninteractive; apt-get update; apt-get install -y git python3 python3-venv python3-pip build-essential'

if ! run_in_distro "test -x '${ENV_DIR}/bin/python'"; then
  printf '%s\n' 'Creating Python environment inside proot...'
  run_in_distro "python3 -m venv '${ENV_DIR}'"
fi

runtime_platform="$(runtime_python_platform)"
if printf '%s' "${runtime_platform}" | grep -qi 'android'; then
  printf '%s\n' 'Replacing Android-native virtual environment with a proot Linux environment...'
  rm -rf "${ENV_DIR}"
  run_in_distro "python3 -m venv '${ENV_DIR}'"
fi

run_in_distro "'${ENV_DIR}/bin/python' -m pip install --upgrade pip setuptools wheel"
run_in_distro "'${ENV_DIR}/bin/python' -m pip install -e '${BACKEND_DIR}'"

write_env_file
sync_runtime_scripts

printf '\n%s\n' 'Mordecai Phase 1 install complete.'
printf 'Install root: %s\n' "${INSTALL_ROOT}"
printf 'Backend: %s\n' "${BACKEND_DIR}"
printf 'Data: %s\n' "${DATA_DIR}"
printf 'Runtime layer: %s (%s)\n' 'proot-distro' "${PROOT_DISTRO}"
printf 'Start command: %s\n' "${SCRIPT_DIR}/start.sh"
printf 'Dashboard URL: %s\n' 'http://127.0.0.1:8000'