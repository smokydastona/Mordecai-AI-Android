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
    assert "permanent-avatar" in report.allowed_features
    assert "android-automation" in report.blocked_features
    assert "daemon-mode" in report.blocked_features


def test_policy_blocks_avatar_asset_changes(tmp_path):
    settings = Settings(workspace_dir=tmp_path / "backend")
    policy = PolicyEngine(settings)

    decision = policy.validate_file_changes([
        ImprovementFileChange(path="assets/avatar/happy.svg", content="<svg />")
    ])

    assert not decision.allowed


def test_policy_blocks_core_runtime_changes(tmp_path):
    settings = Settings(workspace_dir=tmp_path / "backend")
    policy = PolicyEngine(settings)

    decision = policy.validate_file_changes([
        ImprovementFileChange(path="mordecai_core/tool_registry.py", content="SAFE = False\n")
    ])

    assert not decision.allowed


def test_policy_blocks_provider_surface_changes(tmp_path):
    settings = Settings(workspace_dir=tmp_path / "backend")
    policy = PolicyEngine(settings)

    decision = policy.validate_file_changes([
        ImprovementFileChange(path="providers/cloud_llm.py", content="value = 1\n")
    ])

    assert not decision.allowed


def test_policy_blocks_checkout_endpoints_even_when_domain_is_allowlisted(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    policy = PolicyEngine(settings)

    decision = policy.validate_outbound_request("POST", "https://api.openai.com/v1/checkout/session", payload={"amount": 10})

    assert not decision.allowed
    assert "commerce" in decision.reason.lower() or "checkout" in decision.reason.lower()


def test_policy_blocks_personal_data_payloads(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    policy = PolicyEngine(settings)

    decision = policy.validate_outbound_request(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        payload={"email": "user@example.com", "message": "hello"},
    )

    assert not decision.allowed
    assert "personal data" in decision.reason.lower()


def test_policy_blocks_direct_android_input_actions(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai", enable_android_control=True)
    policy = PolicyEngine(settings)

    decision = policy.validate_android_action("tap", ["100", "200"])

    assert not decision.allowed
    assert "blocked" in decision.reason.lower()