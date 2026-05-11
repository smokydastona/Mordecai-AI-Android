import asyncio

from mordecai.android_control import AndroidController
from mordecai.config import Settings
from mordecai.home_automation import HomeAutomationService
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.store import StateStore
from mordecai.providers import ProviderRouter
from mordecai_core.events import EventBus
from mordecai_core.tool_registry import RuntimeContext, ToolExecutionRequest, ToolRegistry
from providers.android_control import AndroidControlToolProvider
from providers.cloud_llm import CloudLLMToolProvider
from providers.git_ops import GitOpsToolProvider
from providers.home_automation import HomeAutomationToolProvider
from providers.local_llm import LocalLLMToolProvider


class RecordingProxy(SafeHttpClient):
    def __init__(self, settings, policy, store):
        super().__init__(settings, policy, store)
        self.calls = []

    async def post_json(self, url, payload, headers=None):
        self.calls.append({"url": url, "payload": payload, "headers": headers or {}})
        return {"choices": [{"message": {"content": "proxied reply"}}]}


class RecordingHomeAutomationProxy(SafeHttpClient):
    def __init__(self, settings, policy, store):
        super().__init__(settings, policy, store)
        self.calls = []
        self.home_assistant_states = {
            "light.kitchen": {
                "entity_id": "light.kitchen",
                "state": "off",
                "attributes": {"friendly_name": "Kitchen", "brightness": 120},
            },
            "scene.relax": {
                "entity_id": "scene.relax",
                "state": "scening",
                "attributes": {"friendly_name": "Relax"},
            },
        }
        self.hue_lights = {
            "light-1": {"id": "light-1", "metadata": {"name": "Desk"}, "on": {"on": True}, "dimming": {"brightness": 80.0}},
        }
        self.hue_scenes = {
            "scene-1": {"id": "scene-1", "metadata": {"name": "Movie"}, "group": {"rid": "room-1", "rtype": "room"}},
        }

    async def request_json(self, method, url, payload=None, headers=None):
        self.calls.append({"method": method, "url": url, "payload": payload, "headers": headers or {}})
        if url.endswith("/api/states"):
            return [self.home_assistant_states["light.kitchen"], self.home_assistant_states["scene.relax"]]
        if "/api/states/light.kitchen" in url:
            return dict(self.home_assistant_states["light.kitchen"])
        if "/api/states/scene.relax" in url:
            return dict(self.home_assistant_states["scene.relax"])
        if url.endswith("/clip/v2/resource/light"):
            return {"data": list(self.hue_lights.values())}
        if url.endswith("/clip/v2/resource/scene"):
            return {"data": list(self.hue_scenes.values())}
        if "/clip/v2/resource/light/" in url:
            light_id = url.rsplit("/", 1)[-1]
            record = dict(self.hue_lights[light_id])
            if method == "PUT" and payload is not None:
                record["on"] = {"on": bool(payload["on"]["on"])}
                self.hue_lights[light_id] = record
            return {"data": [record]}
        if "/clip/v2/resource/scene/" in url:
            scene_id = url.rsplit("/", 1)[-1]
            return {"data": [dict(self.hue_scenes[scene_id])]} 
        raise AssertionError(f"Unexpected request: {method} {url}")

    async def post_json(self, url, payload, headers=None):
        self.calls.append({"method": "POST", "url": url, "payload": payload, "headers": headers or {}})
        if url.endswith("/api/services/light/turn_on"):
            entity_id = payload["entity_id"]
            self.home_assistant_states[entity_id] = {
                **self.home_assistant_states[entity_id],
                "state": "on",
            }
            return {"result": "ok"}
        if url.endswith("/api/services/light/turn_off"):
            entity_id = payload["entity_id"]
            self.home_assistant_states[entity_id] = {
                **self.home_assistant_states[entity_id],
                "state": "off",
            }
            return {"result": "ok"}
        if url.endswith("/api/services/scene/turn_on"):
            return {"result": "ok"}
        return await super().post_json(url, payload, headers=headers)

    async def put_json(self, url, payload, headers=None):
        return await self.request_json("PUT", url, payload=payload, headers=headers)


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


def test_home_automation_provider_lists_entities_and_toggles_lights(tmp_path):
    settings = Settings(
        workspace_dir=tmp_path,
        state_dir=tmp_path / ".mordecai",
        enable_home_automation=True,
        home_assistant_base_url="https://ha.internal",
        home_assistant_access_token="ha-secret",
        home_assistant_allowed_hosts=["ha.internal"],
        home_assistant_allowed_entity_ids=["light.kitchen"],
        home_assistant_allowed_scene_ids=["scene.relax"],
        philips_hue_bridge_url="https://192.168.1.20",
        philips_hue_application_key="hue-secret",
        philips_hue_allowed_hosts=["192.168.1.20"],
        philips_hue_allowed_light_ids=["light-1"],
        philips_hue_allowed_scene_ids=["scene-1"],
    )
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = RecordingHomeAutomationProxy(settings, policy, store)
    service = HomeAutomationService(settings, proxy)
    registry = ToolRegistry(EventBus())

    provider = HomeAutomationToolProvider(service, settings)
    for manifest, handler in provider.tools():
        registry.register(manifest, handler)

    list_result = registry.execute(
        ToolExecutionRequest(
            tool_name="home.list_entities",
            context=RuntimeContext(session_id="test", granted_permissions=frozenset({"network", "home-automation"})),
        )
    )
    toggle_result = registry.execute(
        ToolExecutionRequest(
            tool_name="home.toggle_light",
            arguments={"entity_id": "home-assistant:light.kitchen"},
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"network", "home-automation"}),
                safe_mode=False,
            ),
        )
    )

    assert list_result.status == "completed"
    assert list_result.output["entity_count"] == 2
    assert {item["backend"] for item in list_result.output["entities"]} == {"home-assistant", "philips-hue"}
    assert toggle_result.status == "completed"
    assert toggle_result.output["current_state"] == "on"


def test_home_automation_provider_activates_hue_scene_and_toggles_hue_light(tmp_path):
    settings = Settings(
        workspace_dir=tmp_path,
        state_dir=tmp_path / ".mordecai",
        enable_home_automation=True,
        philips_hue_bridge_url="https://192.168.1.20",
        philips_hue_application_key="hue-secret",
        philips_hue_allowed_hosts=["192.168.1.20"],
        philips_hue_allowed_light_ids=["light-1"],
        philips_hue_allowed_scene_ids=["scene-1"],
    )
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = RecordingHomeAutomationProxy(settings, policy, store)
    service = HomeAutomationService(settings, proxy)
    registry = ToolRegistry(EventBus())

    provider = HomeAutomationToolProvider(service, settings)
    for manifest, handler in provider.tools():
        registry.register(manifest, handler)

    scene_result = registry.execute(
        ToolExecutionRequest(
            tool_name="home.activate_scene",
            arguments={"scene_id": "scene-1"},
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"network", "home-automation"}),
                safe_mode=False,
            ),
        )
    )
    light_result = registry.execute(
        ToolExecutionRequest(
            tool_name="home.toggle_light",
            arguments={"entity_id": "philips-hue:light-1"},
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"network", "home-automation"}),
                safe_mode=False,
            ),
        )
    )

    assert scene_result.status == "completed"
    assert scene_result.output["scene"]["backend"] == "philips-hue"
    assert scene_result.output["activated"] is True
    assert light_result.status == "completed"
    assert light_result.output["entity"]["backend"] == "philips-hue"
    assert light_result.output["current_state"] == "off"


def test_home_automation_provider_requires_confirmation_setting_for_state_changes(tmp_path):
    settings = Settings(
        workspace_dir=tmp_path,
        state_dir=tmp_path / ".mordecai",
        enable_home_automation=True,
        home_automation_require_confirmation=False,
        home_assistant_base_url="https://ha.internal",
        home_assistant_access_token="ha-secret",
        home_assistant_allowed_hosts=["ha.internal"],
        home_assistant_allowed_entity_ids=["light.kitchen"],
    )
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = RecordingHomeAutomationProxy(settings, policy, store)
    service = HomeAutomationService(settings, proxy)
    registry = ToolRegistry(EventBus())

    manifest, handler = HomeAutomationToolProvider(service, settings).tools()[2]
    registry.register(manifest, handler)

    result = registry.execute(
        ToolExecutionRequest(
            tool_name="home.toggle_light",
            arguments={"entity_id": "light.kitchen"},
            context=RuntimeContext(
                session_id="test",
                granted_permissions=frozenset({"network", "home-automation"}),
                safe_mode=False,
            ),
        )
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "PermissionDenied"
