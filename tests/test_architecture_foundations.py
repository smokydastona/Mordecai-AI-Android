import asyncio

from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai.store import StateStore
from mordecai_core.events import EventBus
from mordecai_core.provider_contracts import ProviderCatalog, ProviderRequest, RuleBasedProvider
from mordecai_core.tool_registry import ToolManifest, ToolRegistry
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