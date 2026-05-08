from __future__ import annotations

from dataclasses import dataclass

from mordecai.agent import MordecaiRuntime
from mordecai.android_control import AndroidController
from mordecai.git_tools import GitService
from mordecai.main import build_runtime
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore
from mordecai_core.events import EventBus
from mordecai_core.provider_contracts import ProviderCatalog
from mordecai_core.tool_registry import RuntimeContext, ToolExecutionRequest, ToolExecutionResult, ToolManifest, ToolRegistry
from mordecai_core.tools.file_ops import FileTools


@dataclass(frozen=True, slots=True)
class RuntimeComponents:
    runtime: MordecaiRuntime
    proxy: SafeHttpClient
    git_service: GitService
    improvement_manager: SelfImprovementManager
    android_controller: AndroidController
    policy: PolicyEngine
    store: StateStore
    event_bus: EventBus
    tool_registry: ToolRegistry
    provider_catalog: ProviderCatalog

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, object] | None = None,
        context: RuntimeContext | None = None,
        *,
        timeout_seconds: float = 10.0,
        max_retries: int = 0,
    ) -> ToolExecutionResult:
        return self.tool_registry.execute(
            ToolExecutionRequest(
                tool_name=tool_name,
                arguments=arguments or {},
                context=context or RuntimeContext(session_id="runtime", granted_permissions=frozenset()),
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            )
        )

    def discover_capabilities(self) -> dict[str, object]:
        return {
            "providers": self.provider_catalog.names(),
            "tools": [manifest.tool for manifest in self.tool_registry.list_tools()],
        }


def _build_tool_registry(event_bus: EventBus, proxy: SafeHttpClient, git_service: GitService) -> ToolRegistry:
    registry = ToolRegistry(event_bus)
    file_tools = FileTools()
    registry.register(
        ToolManifest(
            tool="filesystem.read",
            permissions=("storage",),
            description="Read file contents from the workspace.",
            input_schema={"path": "string"},
            output_schema={"content": "string"},
            safe_mode_behavior="read-only",
        ),
        file_tools.read_text,
    )
    registry.register(
        ToolManifest(
            tool="filesystem.write",
            permissions=("storage",),
            description="Write file contents inside the workspace.",
            input_schema={"path": "string", "content": "string"},
            output_schema={"path": "string"},
            risk_level="moderate",
            confirmation_policy="on-request",
        ),
        file_tools.write_text,
    )
    registry.register(
        ToolManifest(
            tool="git.status",
            permissions=("git",),
            description="Inspect repository status.",
            output_schema={"branch": "string", "dirty": "boolean"},
            safe_mode_behavior="read-only",
        ),
        git_service.status,
    )
    registry.register(
        ToolManifest(
            tool="web.search",
            permissions=("network",),
            description="Run a safe web search through the outbound proxy.",
            input_schema={"query": "string"},
            output_schema={"abstract": "string", "related": "array"},
            risk_level="moderate",
        ),
        proxy.web_search,
    )
    registry.register(
        ToolManifest(
            tool="github.search",
            permissions=("network",),
            description="Search GitHub repositories through the safe outbound proxy.",
            input_schema={"query": "string", "limit": "integer"},
            output_schema={"results": "array"},
            risk_level="moderate",
        ),
        proxy.github_search_repositories,
    )
    return registry


def get_runtime_components() -> RuntimeComponents:
    runtime, proxy, git_service, improvement_manager, android, policy, store = build_runtime()
    event_bus = EventBus()
    tool_registry = _build_tool_registry(event_bus, proxy, git_service)
    return RuntimeComponents(
        runtime=runtime,
        proxy=proxy,
        git_service=git_service,
        improvement_manager=improvement_manager,
        android_controller=android,
        policy=policy,
        store=store,
        event_bus=event_bus,
        tool_registry=tool_registry,
        provider_catalog=runtime.provider_router.catalog,
    )