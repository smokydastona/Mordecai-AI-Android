import asyncio
import time
from threading import Event

from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai.store import StateStore
from mordecai_core.events import EventBus
from mordecai_core.provider_contracts import ProviderCatalog, ProviderRequest, RuleBasedProvider
from mordecai_core.tool_registry import RuntimeContext, ToolExecutionRequest, ToolManifest, ToolRegistry
from mordecai_core.runtime import get_runtime_components
from mordecai.proxy import SafeHttpClient
from mordecai.providers import ProviderRouter


def test_event_bus_records_and_broadcasts_events():
    bus = EventBus()
    received = []
    wildcard = []

    bus.subscribe("tool.completed", lambda event: received.append(event.name))
    bus.subscribe("*", lambda event: wildcard.append(event.payload["tool"]))
    envelope = bus.publish("tool.completed", {"tool": "filesystem.read"})

    assert envelope.name == "tool.completed"
    assert received == ["tool.completed"]
    assert wildcard == ["filesystem.read"]
    assert bus.recent()[-1].payload["tool"] == "filesystem.read"


def test_tool_registry_registers_and_invokes_handlers():
    bus = EventBus()
    registry = ToolRegistry(bus)
    calls = []
    registry.register(
        ToolManifest(
            tool="filesystem.read",
            permissions=("storage",),
            description="Read a file",
        ),
        lambda path: calls.append(path) or "content",
    )

    result = registry.invoke("filesystem.read", "README.md")

    assert result == "content"
    assert calls == ["README.md"]
    assert [item.name for item in bus.recent()] == ["tool.registered", "tool.invoked", "tool.completed"]


def test_tool_registry_executes_with_permissions_and_telemetry():
    bus = EventBus()
    registry = ToolRegistry(bus)
    registry.register(
        ToolManifest(
            tool="filesystem.read",
            permissions=("storage",),
            description="Read a file",
            input_schema={"path": "string"},
            safe_mode_behavior="read-only",
        ),
        lambda path: f"read:{path}",
    )

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="filesystem.read",
            arguments={"path": "README.md"},
            context=RuntimeContext(session_id="test", granted_permissions=frozenset({"storage"})),
        )
    )

    assert result.status == "completed"
    assert result.output == "read:README.md"
    assert result.execution_id
    assert [item.name for item in bus.recent()] == [
        "tool.registered",
        "tool.execution.started",
        "tool.execution.completed",
    ]


def test_tool_registry_denies_missing_permissions():
    registry = ToolRegistry(EventBus())
    registry.register(
        ToolManifest(
            tool="filesystem.write",
            permissions=("storage",),
            description="Write a file",
            input_schema={"path": "string", "content": "string"},
            confirmation_policy="on-request",
        ),
        lambda path, content: path,
    )

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="filesystem.write",
            arguments={"path": "README.md", "content": "content"},
            context=RuntimeContext(session_id="test", granted_permissions=frozenset()),
        )
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "PermissionDenied"


def test_tool_registry_retries_retryable_failures():
    registry = ToolRegistry(EventBus())
    attempts = {"count": 0}

    def flaky_tool() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient")
        return "ok"

    registry.register(
        ToolManifest(tool="git.status", permissions=("git",), description="Git status"),
        flaky_tool,
    )

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="git.status",
            context=RuntimeContext(session_id="test", granted_permissions=frozenset({"git"})),
            max_retries=1,
        )
    )

    assert result.status == "completed"
    assert result.attempts == 2
    assert attempts["count"] == 2


def test_tool_registry_times_out_slow_handlers():
    registry = ToolRegistry(EventBus())
    registry.register(
        ToolManifest(tool="web.search", permissions=("network",), description="Search web"),
        lambda: time.sleep(0.05),
    )

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="web.search",
            context=RuntimeContext(session_id="test", granted_permissions=frozenset({"network"})),
            timeout_seconds=0.001,
        )
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "ToolTimeout"


def test_tool_registry_honors_cooperative_cancellation():
    registry = ToolRegistry(EventBus())
    cancellation = Event()
    cancellation.set()
    registry.register(
        ToolManifest(tool="web.search", permissions=("network",), description="Search web"),
        lambda: "unused",
    )

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="web.search",
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"network"}),
                cancellation=cancellation,
            ),
        )
    )

    assert result.status == "cancelled"
    assert result.error is not None
    assert result.error.code == "ExecutionCancelled"


def test_provider_catalog_supports_replaceable_providers():
    request = ProviderRequest(system_prompt="system", message="status", context="ctx")
    catalog = ProviderCatalog([RuleBasedProvider()])

    response = asyncio.run(catalog.get("rule-based").chat(request))

    assert catalog.names() == ["rule-based"]
    assert response.provider == "rule-based"
    assert "stable" in response.content.lower()


def test_provider_router_exposes_catalog_with_multiple_providers(tmp_path):
    settings = Settings(
        workspace_dir=tmp_path,
        state_dir=tmp_path / ".mordecai",
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="secret",
        openai_model="gpt-test",
    )
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = SafeHttpClient(settings, policy, store)
    router = ProviderRouter(settings, proxy)

    assert router.catalog.names() == ["openai-compatible", "rule-based"]


def test_runtime_components_expose_tool_registry_and_provider_catalog():
    components = get_runtime_components()

    tool_names = [manifest.tool for manifest in components.tool_registry.list_tools()]
    assert "filesystem.read" in tool_names
    assert "git.status" in tool_names
    assert "rule-based" in components.provider_catalog.names()


def test_runtime_components_execute_tools_and_discover_capabilities():
    components = get_runtime_components()

    result = components.execute_tool(
        "git.status",
        context=RuntimeContext(session_id="runtime", granted_permissions=frozenset({"git"})),
    )

    capabilities = components.discover_capabilities()

    assert result.status == "completed"
    assert isinstance(result.output, dict)
    assert "tools" in capabilities
    assert "providers" in capabilities
    assert any(tool["tool"] == "git.status" for tool in capabilities["tools"])


def test_runtime_components_hide_android_and_shell_tools_in_mode_a(tmp_path, monkeypatch):
    monkeypatch.setenv("MORDECAI_WORKSPACE_DIR", str(tmp_path))
    monkeypatch.setenv("MORDECAI_STATE_DIR", str(tmp_path / ".mordecai-test"))
    monkeypatch.setenv("MORDECAI_SYSTEM_PROMPT_PATH", str(tmp_path / "prompt.txt"))
    (tmp_path / "prompt.txt").write_text("Test prompt", encoding="utf-8")

    from mordecai.config import get_settings
    from mordecai.main import build_runtime
    from mordecai_core.runtime import get_runtime_components

    get_settings.cache_clear()
    build_runtime.cache_clear()
    get_runtime_components.cache_clear()

    components = get_runtime_components()
    tool_names = [manifest.tool for manifest in components.tool_registry.list_tools()]

    assert "android.control" not in tool_names
    assert "android.accessibility_dump" not in tool_names
    assert "shell.run" not in tool_names