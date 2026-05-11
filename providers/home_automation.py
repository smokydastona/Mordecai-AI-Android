from __future__ import annotations

from mordecai.config import Settings
from mordecai.home_automation import HomeAutomationService
from mordecai_core.tool_registry import PermissionDenied, ToolManifest


class HomeAutomationToolProvider:
    def __init__(self, service: HomeAutomationService, settings: Settings) -> None:
        self.service = service
        self.settings = settings

    def tools(self) -> list[tuple[ToolManifest, object]]:
        return [
            (
                ToolManifest(
                    tool="home.list_entities",
                    provider="provider.home-automation",
                    permissions=("network", "home-automation"),
                    description="List allowlisted Home Assistant and Philips Hue light entities.",
                    output_schema={"backends": "array", "entity_count": "integer", "entities": "array", "errors": "array"},
                    risk_level="low",
                    confirmation_policy="never",
                    safe_mode_behavior="read-only",
                    sandbox_profile="networked",
                ),
                self.list_entities,
            ),
            (
                ToolManifest(
                    tool="home.list_scenes",
                    provider="provider.home-automation",
                    permissions=("network", "home-automation"),
                    description="List allowlisted Home Assistant and Philips Hue scenes.",
                    output_schema={"backends": "array", "scene_count": "integer", "scenes": "array", "errors": "array"},
                    risk_level="low",
                    confirmation_policy="never",
                    safe_mode_behavior="read-only",
                    sandbox_profile="networked",
                ),
                self.list_scenes,
            ),
            (
                ToolManifest(
                    tool="home.toggle_light",
                    provider="provider.home-automation",
                    permissions=("network", "home-automation"),
                    description="Toggle an allowlisted Home Assistant or Philips Hue light.",
                    input_schema={"entity_id": "string"},
                    output_schema={"backend": "string", "entity_id": "string", "entity": "object", "previous_state": "string", "current_state": "string", "action": "string"},
                    risk_level="high",
                    confirmation_policy="always",
                    safe_mode_behavior="deny",
                    sandbox_profile="networked",
                ),
                self.toggle_light,
            ),
            (
                ToolManifest(
                    tool="home.activate_scene",
                    provider="provider.home-automation",
                    permissions=("network", "home-automation"),
                    description="Activate an allowlisted Home Assistant or Philips Hue scene.",
                    input_schema={"scene_id": "string"},
                    output_schema={"backend": "string", "scene_id": "string", "scene": "object", "activated": "boolean", "action": "string"},
                    risk_level="high",
                    confirmation_policy="always",
                    safe_mode_behavior="deny",
                    sandbox_profile="networked",
                ),
                self.activate_scene,
            ),
        ]

    async def list_entities(self) -> dict[str, object]:
        return await self.service.list_entities()

    async def list_scenes(self) -> dict[str, object]:
        return await self.service.list_scenes()

    async def toggle_light(self, entity_id: str) -> dict[str, object]:
        self._require_confirmation_setting()
        return await self.service.toggle_light(entity_id)

    async def activate_scene(self, scene_id: str) -> dict[str, object]:
        self._require_confirmation_setting()
        return await self.service.activate_scene(scene_id)

    def _require_confirmation_setting(self) -> None:
        if not self.settings.home_automation_require_confirmation:
            raise PermissionDenied(
                "State-changing home automation actions require confirmation and are disabled by configuration.",
                details={"setting": "home_automation_require_confirmation"},
            )