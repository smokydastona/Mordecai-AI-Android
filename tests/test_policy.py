from mordecai.config import Settings
from mordecai.models import ImprovementFileChange
from mordecai.policy import PolicyEngine


def test_policy_blocks_wifi_toggle_command(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    policy = PolicyEngine(settings)

    decision = policy.validate_command("adb shell svc wifi enable")

    assert not decision.allowed


def test_policy_allows_normal_file_change(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    policy = PolicyEngine(settings)

    decision = policy.validate_file_changes([
        ImprovementFileChange(path="src/mordecai/example_module.py", content="value = 1\n")
    ])

    assert decision.allowed


def test_policy_report_marks_mode_a_capabilities(tmp_path):
    settings = Settings(workspace_dir=tmp_path / "backend")
    policy = PolicyEngine(settings)

    report = policy.report()

    assert report.mode == "mode-a"
    assert "localhost-fastapi" in report.allowed_features
    assert "android-automation" in report.blocked_features
    assert "daemon-mode" in report.blocked_features