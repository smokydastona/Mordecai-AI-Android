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
DATA_DIR="${MORDECAI_DATA_DIR:-${INSTALL_ROOT}/data}"
STATE_DIR="${MORDECAI_STATE_DIR:-${DATA_DIR}/state}"
LOG_DIR="${MORDECAI_LOG_DIR:-${DATA_DIR}/logs}"
SCRIPT_DIR="${INSTALL_ROOT}/scripts"
PROOT_DISTRO="${MORDECAI_PROOT_DISTRO:-ubuntu-24.04}"
SERVICE_HOST="${MORDECAI_SERVICE_HOST:-127.0.0.1}"
SERVICE_PORT="${MORDECAI_SERVICE_PORT:-8000}"
SERVICE_URL="http://${SERVICE_HOST}:${SERVICE_PORT}"
CONTRACTS_DIR="${STATE_DIR}/contracts"
POLICY_REPORT_PATH="${STATE_DIR}/policy-report.json"
PROVIDER_REGISTRY_PATH="${CONTRACTS_DIR}/provider-registry.json"
TOOL_MANIFEST_PATH="${CONTRACTS_DIR}/tool-manifest.json"
REQUIRED_PROXY_HOSTS="api.github.com github.com hf.co huggingface.co cas-bridge.xethub.hf.co"

run_in_distro() {
  local command="$1"
  proot-distro login "${PROOT_DISTRO}" --shared-tmp -- /bin/bash -lc "${command}"
}

require_path() {
  local candidate="$1"
  local message="$2"
  if [ ! -e "${candidate}" ]; then
    printf '%s\n' "${message}" >&2
    exit 1
  fi
}

printf '%s\n' 'Running Mordecai first-boot verification...'

require_path "${BACKEND_DIR}" "Backend directory not found at ${BACKEND_DIR}. Run scripts/proot-setup.sh first."
require_path "${ENV_DIR}" "Runtime environment not found at ${ENV_DIR}. Run scripts/proot-setup.sh first."
require_path "${BACKEND_DIR}/prompts/system_prompt.txt" "System prompt not found under ${BACKEND_DIR}/prompts/system_prompt.txt."

if ! proot-distro login "${PROOT_DISTRO}" --shared-tmp -- /usr/bin/env true >/dev/null 2>&1; then
  printf '%s\n' "proot distro ${PROOT_DISTRO} is not installed. Run scripts/proot-setup.sh first." >&2
  exit 1
fi

run_in_distro "test -x '${ENV_DIR}/bin/python'"
run_in_distro "'${ENV_DIR}/bin/python' -c \"import sysconfig; platform = sysconfig.get_platform(); assert 'android' not in platform.lower(), platform\""

if [ ! -d "${BACKEND_DIR}/.git" ]; then
  printf '%s\n' 'Initializing git repository for the portable backend checkout...'
  git -C "${BACKEND_DIR}" init
fi
git -C "${BACKEND_DIR}" config pull.ff only
git -C "${BACKEND_DIR}" config push.default nothing

mkdir -p "${STATE_DIR}" "${LOG_DIR}" "${CONTRACTS_DIR}"

printf '%s\n' 'Exporting provider and tool contracts...'
run_in_distro "'${ENV_DIR}/bin/python' -m mordecai.runtime_contracts --export-dir '${CONTRACTS_DIR}'"
run_in_distro "test -s '${PROVIDER_REGISTRY_PATH}'"
run_in_distro "test -s '${TOOL_MANIFEST_PATH}'"

printf '%s\n' 'Starting dashboard runtime...'
"${SCRIPT_DIR}/start.sh"

healthy=false
for attempt in $(seq 1 30); do
  if curl -fsS "${SERVICE_URL}/health" > /dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 1
done

if [ "${healthy}" != "true" ]; then
  printf '%s\n' "Dashboard did not become healthy at ${SERVICE_URL} within 30 seconds." >&2
  exit 1
fi

curl -fsS "${SERVICE_URL}/api/policy" > "${POLICY_REPORT_PATH}"
curl -fsS "${SERVICE_URL}/api/runtime/provider-registry" > "${PROVIDER_REGISTRY_PATH}"
curl -fsS "${SERVICE_URL}/api/runtime/tool-manifest" > "${TOOL_MANIFEST_PATH}"

required_hosts_csv="$(printf '%s' "${REQUIRED_PROXY_HOSTS}" | tr ' ' ',')"
run_in_distro "'${ENV_DIR}/bin/python' -c \"import json, pathlib, sys; data=json.loads(pathlib.Path('${POLICY_REPORT_PATH}').read_text(encoding='utf-8')); required='${required_hosts_csv}'.split(','); allowed=set(data['allowed_domains']); missing=sorted(host for host in required if host and host not in allowed); print('Proxy allowlist verified.' if not missing else 'Missing allowlist hosts: ' + ', '.join(missing)); sys.exit(1 if missing else 0)\""

printf 'Git status: %s\n' "$(git -C "${BACKEND_DIR}" status --short --branch | head -n 1)"
printf 'Policy report: %s\n' "${POLICY_REPORT_PATH}"
printf 'Provider registry: %s\n' "${PROVIDER_REGISTRY_PATH}"
printf 'Tool manifest: %s\n' "${TOOL_MANIFEST_PATH}"
printf 'Dashboard: %s\n' "${SERVICE_URL}"
printf '%s\n' 'First boot verification completed.'