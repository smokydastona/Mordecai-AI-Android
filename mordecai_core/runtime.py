from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from mordecai.agent import MordecaiRuntime
from mordecai.android_control import AndroidController
from mordecai.bootstrap import build_runtime
from mordecai.git_tools import GitService
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore
from mordecai.local_models import LocalModelService
from mordecai_core.events import EventBus
from mordecai_core.provider_contracts import ProviderCatalog
from mordecai_core.tool_registry import RuntimeContext, ToolExecutionRequest, ToolExecutionResult, ToolManifest, ToolRegistry
from mordecai_core.tools.file_ops import FileTools
from providers.android_control import AndroidControlToolProvider
from providers.accessibility import AccessibilityToolProvider
from providers.cloud_llm import CloudLLMToolProvider
from providers.git_ops import GitOpsToolProvider
from providers.local_llm import LocalLLMToolProvider
from providers.shell_ops import ShellToolProvider


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
            "providers": self.provider_catalog.capabilities_matrix(),
            "tools": self.tool_registry.capability_manifest(),
            "local_models": LocalModelService(self.runtime.settings).capability_manifest(),
            "provider_health": [record.model_dump(mode="json") for record in self.runtime.provider_router.health_snapshot()],
        }

    def trace_snapshot(self, limit: int = 25) -> dict[str, object]:
        events = [
            {
                "name": event.name,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in self.event_bus.recent()[-limit:]
        ]
        return {
            "events": events,
            "executions": [record.model_dump(mode="json") for record in self.store.read_tool_executions()[-limit:]],
            "provider_decisions": self.runtime.provider_router.recent_decisions()[-limit:],
            "policy_audits": [record.model_dump(mode="json") for record in self.store.read_policy_audits()[-limit:]],
            "latency_records": [record.model_dump(mode="json") for record in self.store.read_request_latencies()[-limit:]],
            "latency_summary": self.store.summarize_request_latencies().model_dump(mode="json"),
            "timelines": [record.model_dump(mode="json") for record in self.store.read_timelines()[-limit:]],
            "provider_health": [record.model_dump(mode="json") for record in self.store.read_provider_health()],
        }


def _build_tool_registry(
    event_bus: EventBus,
    proxy: SafeHttpClient,
    git_service: GitService,
    runtime: MordecaiRuntime,
    android_controller: AndroidController,
    store: StateStore,
) -> ToolRegistry:
    registry = ToolRegistry(event_bus, execution_recorder=store.append_tool_execution)
    file_tools = FileTools()
    registry.register(
        ToolManifest(
            tool="filesystem.read",
            provider="core.filesystem",
            permissions=("storage",),
            description="Read file contents from the workspace.",
            input_schema={"path": "string"},
            output_schema={"content": "string"},
            safe_mode_behavior="read-only",
            sandbox_profile="trusted",
        ),
        file_tools.read_text,
    )
    registry.register(
        ToolManifest(
            tool="filesystem.write",
            provider="core.filesystem",
            permissions=("storage",),
            description="Write file contents inside the workspace.",
            input_schema={"path": "string", "content": "string"},
            output_schema={"path": "string"},
            risk_level="moderate",
            confirmation_policy="on-request",
            sandbox_profile="workspace-write",
        ),
        file_tools.write_text,
    )
    registry.register(
        ToolManifest(
            tool="git.status",
            provider="core.git",
            permissions=("git",),
            description="Inspect repository status.",
            output_schema={"branch": "string", "dirty": "boolean"},
            safe_mode_behavior="read-only",
            sandbox_profile="trusted",
        ),
        git_service.status,
    )
    registry.register(
        ToolManifest(
            tool="web.search",
            provider="core.proxy",
            permissions=("network",),
            description="Run a safe web search through the outbound proxy.",
            input_schema={"query": "string"},
            output_schema={"abstract": "string", "related": "array"},
            risk_level="moderate",
            confirmation_policy="on-request",
            sandbox_profile="networked",
        ),
        proxy.web_search,
    )
    registry.register(
        ToolManifest(
            tool="github.search",
            provider="core.proxy",
            permissions=("network",),
            description="Search GitHub repositories through the safe outbound proxy.",
            input_schema={"query": "string", "limit": "integer"},
            output_schema={"results": "array"},
            risk_level="moderate",
            confirmation_policy="on-request",
            sandbox_profile="networked",
        ),
        proxy.github_search_repositories,
    )
    providers = [
        GitOpsToolProvider(git_service),
        LocalLLMToolProvider(runtime.provider_router.catalog),
        CloudLLMToolProvider(runtime.provider_router),
    ]
    if runtime.settings.enable_android_control:
        providers.extend(
            [
                AndroidControlToolProvider(android_controller),
                AccessibilityToolProvider(runtime.settings, runtime.policy),
            ]
        )
    if runtime.settings.mode != "mode-a":
        providers.append(ShellToolProvider(runtime.settings, runtime.policy))
    for provider in providers:
        for manifest, handler in provider.tools():
            registry.register(manifest, handler)
    return registry


@lru_cache(maxsize=1)
def get_runtime_components() -> RuntimeComponents:
    runtime, proxy, git_service, improvement_manager, android, policy, store = build_runtime()
    event_bus = EventBus()
    tool_registry = _build_tool_registry(event_bus, proxy, git_service, runtime, android, store)
    runtime.provider_router.attach_event_bus(event_bus)
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