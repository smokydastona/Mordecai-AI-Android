import sys

from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai.store import StateStore
from mordecai_core.events import EventBus
from mordecai_core.tool_registry import RuntimeContext, ToolExecutionRequest, ToolRegistry
from providers.accessibility import AccessibilityToolProvider
from providers.shell_ops import ShellToolProvider


def test_shell_provider_executes_bounded_command_and_records_history(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    policy = PolicyEngine(settings)
    store = StateStore(settings.state_dir, settings.max_log_entries)
    registry = ToolRegistry(EventBus(), execution_recorder=store.append_tool_execution)
    manifest, handler = ShellToolProvider(settings, policy).tools()[0]
    registry.register(manifest, handler)

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="shell.run",
            arguments={"command": [sys.executable, "-c", "print('shell-ok')"], "cwd": "."},
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"shell"}),
                safe_mode=False,
            ),
        )
    )

    history = store.read_tool_executions()

    assert result.status == "completed"
    assert result.output["stdout"] == "shell-ok"
    assert history[-1].tool_name == "shell.run"
    assert history[-1].status == "completed"


def test_accessibility_provider_requires_android_control_enablement(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    policy = PolicyEngine(settings)
    registry = ToolRegistry(EventBus())
    manifest, handler = AccessibilityToolProvider(settings, policy).tools()[0]
    registry.register(manifest, handler)

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="android.accessibility_dump",
            arguments={},
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"android-control", "accessibility"}),
            ),
        )
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "PermissionDenied"