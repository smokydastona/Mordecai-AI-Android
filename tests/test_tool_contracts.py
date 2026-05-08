import asyncio

from mordecai.android_control import AndroidController
from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.store import StateStore
from mordecai.providers import ProviderRouter
from mordecai_core.events import EventBus
from mordecai_core.tool_registry import RuntimeContext, ToolExecutionRequest, ToolRegistry
from providers.android_control import AndroidControlToolProvider
from providers.cloud_llm import CloudLLMToolProvider
from providers.git_ops import GitOpsToolProvider
from providers.local_llm import LocalLLMToolProvider


class RecordingProxy(SafeHttpClient):
    def __init__(self, settings, policy, store):
        super().__init__(settings, policy, store)
        self.calls = []

    async def post_json(self, url, payload, headers=None):
        self.calls.append({"url": url, "payload": payload, "headers": headers or {}})
        return {"choices": [{"message": {"content": "proxied reply"}}]}


class StubAndroidController(AndroidController):
    def __init__(self):
        pass

    def perform(self, action: str, arguments: list[str]) -> dict[str, str]:
        if action == "unsupported":
            raise ValueError("Unsupported Android action or argument count")
        return {"stdout": f"{action}:{','.join(arguments)}", "stderr": ""}


def test_local_and_cloud_llm_providers_execute_through_tool_registry(tmp_path):
    settings = Settings(
        workspace_dir=tmp_path,
        state_dir=tmp_path / ".mordecai",
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="secret",
        openai_model="gpt-test",
    )
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = RecordingProxy(settings, policy, store)
    router = ProviderRouter(settings, proxy)
    registry = ToolRegistry(EventBus())

    for provider in (LocalLLMToolProvider(router.catalog), CloudLLMToolProvider(router)):
        for manifest, handler in provider.tools():
            registry.register(manifest, handler)

    local_result = registry.execute(
        ToolExecutionRequest(
            tool_name="local-llm.chat",
            arguments={"message": "status", "system_prompt": "system", "context": "ctx"},
            context=RuntimeContext(session_id="test", granted_permissions=frozenset({"llm"})),
        )
    )
    cloud_result = registry.execute(
        ToolExecutionRequest(
            tool_name="cloud-llm.chat",
            arguments={"message": "hello", "system_prompt": "system", "context": "ctx"},
            context=RuntimeContext(session_id="test", granted_permissions=frozenset({"llm", "network"})),
        )
    )

    assert local_result.status == "completed"
    assert local_result.output["provider"] == "rule-based"
    assert cloud_result.status == "completed"
    assert cloud_result.output["provider"] == "openai-compatible"
    assert proxy.calls


def test_android_and_git_provider_manifests_define_high_risk_controls(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    git_provider = GitOpsToolProvider(__import__("mordecai.git_tools", fromlist=["GitService"]).GitService(tmp_path))
    android_provider = AndroidControlToolProvider(StubAndroidController())

    git_manifest = git_provider.tools()[0][0]
    android_manifest = android_provider.tools()[0][0]

    assert git_manifest.tool == "git.backup"
    assert git_manifest.confirmation_policy == "always"
    assert git_manifest.sandbox_profile == "workspace-write"
    assert android_manifest.tool == "android.control"
    assert android_manifest.risk_level == "high"
    assert android_manifest.safe_mode_behavior == "deny"


def test_android_provider_maps_invalid_actions_to_automation_mismatch():
    registry = ToolRegistry(EventBus())
    provider = AndroidControlToolProvider(StubAndroidController())
    manifest, handler = provider.tools()[0]
    registry.register(manifest, handler)

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="android.control",
            arguments={"action": "unsupported", "arguments": []},
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"android-control"}),
                safe_mode=False,
            ),
        )
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "AutomationMismatch"
