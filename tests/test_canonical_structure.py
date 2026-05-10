from pathlib import Path

from mordecai.config import get_settings
from mordecai_core.models.local_models import LocalModelRegistry
from mordecai_core.tools.file_ops import FileTools
from net_proxy.proxy import ConfigurableNetProxy, load_proxy_config
from self_mod.propose_change import load_change_spec
from voice.wake_word import WakeWordDetector


def test_wake_word_detector_extracts_command():
    detector = WakeWordDetector(["Mordecai", "Mori"])

    result = detector.detect("Mordecai: open diagnostics")

    assert result.matched is True
    assert result.wake_word == "Mordecai"
    assert result.command == "open diagnostics"


def test_local_model_registry_bootstraps_profiles(tmp_path, monkeypatch):
    monkeypatch.setenv("MORDECAI_STATE_DIR", str(tmp_path / ".mordecai"))
    get_settings.cache_clear()

    registry = LocalModelRegistry()
    profiles = registry.load()

    assert profiles
    assert any(profile.name == "whisper-cli" for profile in profiles)


def test_load_proxy_config_and_build_proxy():
    config = load_proxy_config(Path("net_proxy/config.yaml"))
    proxy = ConfigurableNetProxy(Path("net_proxy/config.yaml"))

    assert "api.github.com" in config.allowed_domains
    assert proxy.settings.max_requests_per_minute == config.limits.max_requests_per_minute


def test_load_change_spec_from_array_payload(tmp_path):
    spec_path = tmp_path / "change.json"
    spec_path.write_text('[{"path": "src/demo.py", "content": "value = 1\\n"}]', encoding="utf-8")

    request = load_change_spec(spec_path, description="demo")

    assert request.description == "demo"
    assert request.changes[0].path == "src/demo.py"


def test_file_tools_refuses_workspace_escape(tmp_path):
    tools = FileTools(tmp_path)

    try:
        tools.write_text("../escape.txt", "blocked")
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected workspace escape to be blocked")


def test_phase1_installer_defaults_to_models_and_shell_apk():
    installer = Path("scripts/proot-setup.sh").read_text(encoding="utf-8")

    assert 'INSTALL_DEFAULT_MODELS="${MORDECAI_INSTALL_DEFAULT_MODELS:-true}"' in installer
    assert 'INSTALL_LOCAL_MODEL_BINARIES="${MORDECAI_INSTALL_LOCAL_MODEL_BINARIES:-true}"' in installer
    assert 'INSTALL_SHELL_APK="${MORDECAI_INSTALL_SHELL_APK:-true}"' in installer
    assert 'FORCE_REINSTALL="${MORDECAI_FORCE_REINSTALL:-false}"' in installer
    assert 'android-shell-latest' in installer
    assert 'termux-open --content-type application/vnd.android.package-archive' in installer


def test_phase1_installer_provisions_phone_supported_local_model_runtimes():
    installer = Path("scripts/proot-setup.sh").read_text(encoding="utf-8")

    assert 'install_local_model_binaries()' in installer
    assert 'ensure_runtime_tool_layout()' in installer
    assert 'repair_llama_cpp_checkout()' in installer
    assert "run_in_distro \"mkdir -p '${TOOLS_DIR}' '${TOOLS_BIN_DIR}'\"" in installer
    assert "test -d '${LLAMA_CPP_DIR}/.git' && test -f '${LLAMA_CPP_DIR}/CMakeLists.txt'" in installer
    assert "git -C '${LLAMA_CPP_DIR}' rev-parse --is-inside-work-tree >/dev/null 2>&1" in installer
    assert "run_in_distro \"rm -rf '${LLAMA_CPP_DIR}' '${LLAMA_CPP_BUILD_DIR}'\"" in installer
    assert 'install_voice_runtime_python_packages()' in installer
    assert 'TORCH_CPU_INDEX_URL="${MORDECAI_TORCH_CPU_INDEX_URL:-https://download.pytorch.org/whl/cpu}"' in installer
    assert "runtime_platform=\"$(runtime_python_platform)\"" in installer
    assert "'${ENV_DIR}/bin/python' -m pip install --index-url '${TORCH_CPU_INDEX_URL}' 'torch<3'" in installer
    assert "'${ENV_DIR}/bin/python' -m pip install openai-whisper piper-tts" in installer
    assert 'ggml-org/llama.cpp' in installer
    assert "'${ENV_DIR}/bin/python' -m pip check" in installer
    assert 'verify_voice_runtime_python_packages' in installer
    assert 'assert torch.version.cuda is None' in installer
    assert "command -v ffmpeg >/dev/null" in installer
    assert "cmake --build '${LLAMA_CPP_BUILD_DIR}' -j\\$(nproc)" in installer
    assert "ln -sf '${ENV_DIR}/bin/whisper' '${TOOLS_BIN_DIR}/whisper'" in installer
    assert "ln -sf '${ENV_DIR}/bin/piper' '${TOOLS_BIN_DIR}/piper'" in installer
    assert "${LLAMA_CPP_BUILD_DIR}/bin/llama-cli' ]; then ln -sf '${LLAMA_CPP_BUILD_DIR}/bin/llama-cli' '${TOOLS_BIN_DIR}/llama-cli'; else ln -sf '${LLAMA_CPP_BUILD_DIR}/bin/main' '${TOOLS_BIN_DIR}/llama-cli'; fi" in installer


def test_phase1_installer_supports_force_reinstall_without_wiping_models_or_state():
    installer = Path("scripts/proot-setup.sh").read_text(encoding="utf-8")

    assert 'force_reinstall_runtime_layers()' in installer
    assert 'Force reinstall requested; removing backend checkout, runtime environment, tools, and copied scripts while preserving models and state...' in installer
    assert 'rm -rf "${BACKEND_DIR}" "${ENV_DIR}" "${TOOLS_DIR}" "${SCRIPT_DIR}"' in installer


def test_phase1_installer_repairs_missing_runtime_directories_and_broken_tool_checkout_in_place():
    installer = Path("scripts/proot-setup.sh").read_text(encoding="utf-8")

    assert 'ensure_runtime_layout()' in installer
    assert 'mkdir -p "${INSTALL_ROOT}" "${DATA_DIR}" "${STATE_DIR}" "${LOG_DIR}" "${CACHE_DIR}" "${MODELS_DIR}" "${SCRIPT_DIR}" "${ROOTFS_CACHE_DIR}" "${TOOLS_DIR}"' in installer
    assert 'repair_backend_checkout()' in installer
    assert 'Repairing broken Mordecai backend checkout in place before continuing...' in installer
    assert 'rm -rf "${BACKEND_DIR}"' in installer
    assert '[ -f "${BACKEND_DIR}/pyproject.toml" ] && [ -f "${BACKEND_DIR}/scripts/proot-setup.sh" ]' in installer
    assert 'Repairing broken llama.cpp tool checkout in place before continuing...' in installer


def test_phase1_installer_runs_post_install_backend_smoke_check():
    installer = Path("scripts/proot-setup.sh").read_text(encoding="utf-8")

    assert 'run_post_install_smoke_check()' in installer
    assert 'Running post-install backend smoke check...' in installer
    assert 'http://127.0.0.1:${service_port}/api/status' in installer
    assert 'http://127.0.0.1:${service_port}/api/runtime/provider-registry' in installer
    assert 'http://127.0.0.1:${service_port}/api/voice/engines' in installer
    assert 'Backend already running; preserving the existing process for smoke validation.' in installer
    assert 'started_here="true"' in installer
    assert 'trap ' in installer
    assert '"${SCRIPT_DIR}/start.sh"' in installer
    assert '"${SCRIPT_DIR}/stop.sh" >/dev/null' in installer
    assert "assert provider_registry['contract'] == 'provider-registry'" in installer
    assert "assert isinstance(provider_registry['providers'], list) and provider_registry['providers']" in installer
    assert "assert 'catalog_summary' in voice_engines" in installer
    assert "assert 'recommended_stack' in voice_engines" in installer
    assert 'command -v llama-cli >/dev/null && command -v whisper >/dev/null && command -v piper >/dev/null' in installer


def test_phase1_installer_verifies_runtime_and_default_model_bundle_after_install():
    installer = Path("scripts/proot-setup.sh").read_text(encoding="utf-8")

    assert 'verify_runtime_python_install' in installer
    assert 'import fastapi, httpx, yaml, pydantic_settings, uvicorn; import mordecai, mordecai_core, providers, self_mod, net_proxy, voice' in installer
    assert 'verify_default_model_bundle' in installer
    assert "test -f '${MODELS_DIR}/Qwen2.5-3B-Instruct-Q4_K_M.gguf'" in installer
    assert "test -f '${MODELS_DIR}/en_US-lessac-medium.onnx'" in installer
    assert "test -f '${MODELS_DIR}/en_US-lessac-medium.onnx.json'" in installer


def test_phase1_installer_supports_optional_debug_toolkit():
    installer = Path("scripts/proot-setup.sh").read_text(encoding="utf-8")

    assert 'INSTALL_DEBUG_TOOLKIT="${MORDECAI_INSTALL_DEBUG_TOOLKIT:-false}"' in installer
    assert 'install_debug_toolkit()' in installer
    assert "pip install py-spy viztracer mitmproxy" in installer


def test_start_script_exports_local_runtime_bin_path():
    start_script = Path("scripts/start.sh").read_text(encoding="utf-8")

    assert 'TOOLS_BIN_DIR="${TOOLS_DIR}/bin"' in start_script
    assert 'export PATH="${TOOLS_BIN_DIR}:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"' in start_script


def test_first_boot_script_exports_runtime_contracts_and_verifies_policy():
    first_boot = Path("scripts/first_boot.sh").read_text(encoding="utf-8")

    assert "python' -m mordecai.runtime_contracts --export-dir" in first_boot
    assert '/api/runtime/provider-registry' in first_boot
    assert '/api/runtime/tool-manifest' in first_boot
    assert '/api/policy' in first_boot
    assert 'REQUIRED_PROXY_HOSTS="api.github.com github.com hf.co huggingface.co"' in first_boot


def test_debugging_guide_exists_with_scenario_matrix():
    guide = Path("docs/debugging-guide.md").read_text(encoding="utf-8")

    assert "# Mordecai Debugging Guide" in guide
    assert "## Scenario Matrix" in guide
    assert "Battery drain or Android shell churn" in guide
    assert "Model download fails or stalls" in guide


def test_ci_workflow_publishes_android_shell_release_asset():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert 'name: Publish Android Shell Release Asset' in workflow
    assert 'name: Stage Android shell release asset' in workflow
    assert 'artifacts/android-shell-debug.apk' in workflow
    assert 'name: Resolve Android shell release asset path' in workflow
    assert "find artifacts/release -type f -name 'android-shell-debug.apk'" in workflow
    assert 'GH_REPO: ${{ github.repository }}' in workflow
    assert 'gh release create android-shell-latest' in workflow