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
    assert 'INSTALL_SHELL_APK="${MORDECAI_INSTALL_SHELL_APK:-true}"' in installer
    assert 'android-shell-latest' in installer
    assert 'termux-open --content-type application/vnd.android.package-archive' in installer


def test_ci_workflow_publishes_android_shell_release_asset():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert 'name: Publish Android Shell Release Asset' in workflow
    assert 'gh release create android-shell-latest' in workflow