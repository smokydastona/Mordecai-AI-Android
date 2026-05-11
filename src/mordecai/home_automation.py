from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from mordecai.config import Settings
from mordecai.proxy import SafeHttpClient
from mordecai_core.tool_registry import ProviderUnavailable, ToolValidationFailure


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


@dataclass(frozen=True, slots=True)
class HomeAutomationEntity:
    id: str
    backend: str
    backend_id: str
    name: str
    type: str
    state: str
    attributes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "backend": self.backend,
            "backend_id": self.backend_id,
            "name": self.name,
            "type": self.type,
            "state": self.state,
            "attributes": self.attributes,
        }


@dataclass(frozen=True, slots=True)
class HomeAutomationScene:
    id: str
    backend: str
    backend_id: str
    name: str
    type: str
    attributes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "backend": self.backend,
            "backend_id": self.backend_id,
            "name": self.name,
            "type": self.type,
            "attributes": self.attributes,
        }


class HomeAssistantAutomationClient:
    backend_name = "home-assistant"

    def __init__(self, settings: Settings, proxy: SafeHttpClient) -> None:
        self.settings = settings
        self.proxy = proxy
        self.base_url = settings.home_assistant_base_url or ""
        self.allowed_entity_ids = frozenset(settings.home_assistant_allowed_entity_ids)
        self.allowed_scene_ids = frozenset(settings.home_assistant_allowed_scene_ids)

    def allows_entity(self, entity_id: str) -> bool:
        return entity_id in self.allowed_entity_ids

    def allows_scene(self, scene_id: str) -> bool:
        return scene_id in self.allowed_scene_ids

    async def list_entities(self) -> list[HomeAutomationEntity]:
        payload = await self.proxy.request_json("GET", _join_url(self.base_url, "/api/states"), headers=self._headers())
        entities: list[HomeAutomationEntity] = []
        for item in payload:
            entity_id = str(item.get("entity_id", ""))
            if entity_id.startswith("light.") and self.allows_entity(entity_id):
                entities.append(self._normalize_entity(item))
        return sorted(entities, key=lambda item: item.name.lower())

    async def list_scenes(self) -> list[HomeAutomationScene]:
        payload = await self.proxy.request_json("GET", _join_url(self.base_url, "/api/states"), headers=self._headers())
        scenes: list[HomeAutomationScene] = []
        for item in payload:
            entity_id = str(item.get("entity_id", ""))
            if entity_id.startswith("scene.") and self.allows_scene(entity_id):
                scenes.append(self._normalize_scene(item))
        return sorted(scenes, key=lambda item: item.name.lower())

    async def toggle_light(self, entity_id: str) -> dict[str, Any]:
        if not self.allows_entity(entity_id):
            raise ToolValidationFailure("Home Assistant light is not allowlisted.", details={"entity_id": entity_id})
        previous = await self._fetch_entity_state(entity_id)
        service = "turn_off" if previous.state == "on" else "turn_on"
        await self.proxy.post_json(
            _join_url(self.base_url, f"/api/services/light/{service}"),
            {"entity_id": entity_id},
            headers=self._headers(),
        )
        current = await self._fetch_entity_state(entity_id)
        return {
            "backend": self.backend_name,
            "entity_id": current.id,
            "entity": current.to_dict(),
            "previous_state": previous.state,
            "current_state": current.state,
            "action": "toggle-light",
        }

    async def activate_scene(self, scene_id: str) -> dict[str, Any]:
        if not self.allows_scene(scene_id):
            raise ToolValidationFailure("Home Assistant scene is not allowlisted.", details={"scene_id": scene_id})
        scene = await self._fetch_scene_state(scene_id)
        await self.proxy.post_json(
            _join_url(self.base_url, "/api/services/scene/turn_on"),
            {"entity_id": scene_id},
            headers=self._headers(),
        )
        return {
            "backend": self.backend_name,
            "scene_id": scene.id,
            "scene": scene.to_dict(),
            "activated": True,
            "action": "activate-scene",
        }

    async def _fetch_entity_state(self, entity_id: str) -> HomeAutomationEntity:
        payload = await self.proxy.request_json(
            "GET",
            _join_url(self.base_url, f"/api/states/{quote(entity_id, safe='')}"),
            headers=self._headers(),
        )
        return self._normalize_entity(payload)

    async def _fetch_scene_state(self, scene_id: str) -> HomeAutomationScene:
        payload = await self.proxy.request_json(
            "GET",
            _join_url(self.base_url, f"/api/states/{quote(scene_id, safe='')}"),
            headers=self._headers(),
        )
        return self._normalize_scene(payload)

    def _normalize_entity(self, payload: dict[str, Any]) -> HomeAutomationEntity:
        entity_id = str(payload.get("entity_id", ""))
        attributes = payload.get("attributes") or {}
        return HomeAutomationEntity(
            id=f"{self.backend_name}:{entity_id}",
            backend=self.backend_name,
            backend_id=entity_id,
            name=str(attributes.get("friendly_name") or entity_id),
            type="light",
            state=str(payload.get("state", "unknown")),
            attributes=self._select_attributes(attributes),
        )

    def _normalize_scene(self, payload: dict[str, Any]) -> HomeAutomationScene:
        scene_id = str(payload.get("entity_id", ""))
        attributes = payload.get("attributes") or {}
        return HomeAutomationScene(
            id=f"{self.backend_name}:{scene_id}",
            backend=self.backend_name,
            backend_id=scene_id,
            name=str(attributes.get("friendly_name") or scene_id),
            type="scene",
            attributes=self._select_attributes(attributes),
        )

    @staticmethod
    def _select_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "friendly_name",
            "brightness",
            "color_mode",
            "supported_color_modes",
            "icon",
            "area_id",
            "assumed_state",
        ]
        return {key: attributes[key] for key in keys if key in attributes}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.home_assistant_access_token}"}


class PhilipsHueAutomationClient:
    backend_name = "philips-hue"

    def __init__(self, settings: Settings, proxy: SafeHttpClient) -> None:
        self.settings = settings
        self.proxy = proxy
        self.base_url = settings.philips_hue_bridge_url or ""
        self.allowed_light_ids = frozenset(settings.philips_hue_allowed_light_ids)
        self.allowed_scene_ids = frozenset(settings.philips_hue_allowed_scene_ids)

    def allows_entity(self, entity_id: str) -> bool:
        return entity_id in self.allowed_light_ids

    def allows_scene(self, scene_id: str) -> bool:
        return scene_id in self.allowed_scene_ids

    async def list_entities(self) -> list[HomeAutomationEntity]:
        payload = await self.proxy.request_json("GET", _join_url(self.base_url, "/clip/v2/resource/light"), headers=self._headers())
        entities = [self._normalize_entity(item) for item in payload.get("data", []) if self.allows_entity(str(item.get("id", "")))]
        return sorted(entities, key=lambda item: item.name.lower())

    async def list_scenes(self) -> list[HomeAutomationScene]:
        payload = await self.proxy.request_json("GET", _join_url(self.base_url, "/clip/v2/resource/scene"), headers=self._headers())
        scenes = [self._normalize_scene(item) for item in payload.get("data", []) if self.allows_scene(str(item.get("id", "")))]
        return sorted(scenes, key=lambda item: item.name.lower())

    async def toggle_light(self, entity_id: str) -> dict[str, Any]:
        if not self.allows_entity(entity_id):
            raise ToolValidationFailure("Philips Hue light is not allowlisted.", details={"entity_id": entity_id})
        previous = await self._fetch_entity_state(entity_id)
        target_on = previous.state != "on"
        await self.proxy.put_json(
            _join_url(self.base_url, f"/clip/v2/resource/light/{quote(entity_id, safe='')}"),
            {"on": {"on": target_on}},
            headers=self._headers(),
        )
        current = await self._fetch_entity_state(entity_id)
        return {
            "backend": self.backend_name,
            "entity_id": current.id,
            "entity": current.to_dict(),
            "previous_state": previous.state,
            "current_state": current.state,
            "action": "toggle-light",
        }

    async def activate_scene(self, scene_id: str) -> dict[str, Any]:
        if not self.allows_scene(scene_id):
            raise ToolValidationFailure("Philips Hue scene is not allowlisted.", details={"scene_id": scene_id})
        scene = await self._fetch_scene_state(scene_id)
        await self.proxy.put_json(
            _join_url(self.base_url, f"/clip/v2/resource/scene/{quote(scene_id, safe='')}"),
            {"recall": {"action": "active"}},
            headers=self._headers(),
        )
        return {
            "backend": self.backend_name,
            "scene_id": scene.id,
            "scene": scene.to_dict(),
            "activated": True,
            "action": "activate-scene",
        }

    async def _fetch_entity_state(self, entity_id: str) -> HomeAutomationEntity:
        payload = await self.proxy.request_json(
            "GET",
            _join_url(self.base_url, f"/clip/v2/resource/light/{quote(entity_id, safe='')}"),
            headers=self._headers(),
        )
        data = payload.get("data", [])
        if not data:
            raise ProviderUnavailable("Philips Hue light lookup returned no data.", details={"entity_id": entity_id})
        return self._normalize_entity(data[0])

    async def _fetch_scene_state(self, scene_id: str) -> HomeAutomationScene:
        payload = await self.proxy.request_json(
            "GET",
            _join_url(self.base_url, f"/clip/v2/resource/scene/{quote(scene_id, safe='')}"),
            headers=self._headers(),
        )
        data = payload.get("data", [])
        if not data:
            raise ProviderUnavailable("Philips Hue scene lookup returned no data.", details={"scene_id": scene_id})
        return self._normalize_scene(data[0])

    def _normalize_entity(self, payload: dict[str, Any]) -> HomeAutomationEntity:
        entity_id = str(payload.get("id", ""))
        metadata = payload.get("metadata") or {}
        return HomeAutomationEntity(
            id=f"{self.backend_name}:{entity_id}",
            backend=self.backend_name,
            backend_id=entity_id,
            name=str(metadata.get("name") or entity_id),
            type="light",
            state="on" if bool((payload.get("on") or {}).get("on")) else "off",
            attributes=self._select_entity_attributes(payload),
        )

    def _normalize_scene(self, payload: dict[str, Any]) -> HomeAutomationScene:
        scene_id = str(payload.get("id", ""))
        metadata = payload.get("metadata") or {}
        return HomeAutomationScene(
            id=f"{self.backend_name}:{scene_id}",
            backend=self.backend_name,
            backend_id=scene_id,
            name=str(metadata.get("name") or scene_id),
            type="scene",
            attributes=self._select_scene_attributes(payload),
        )

    @staticmethod
    def _select_entity_attributes(payload: dict[str, Any]) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        if "dimming" in payload:
            attributes["dimming"] = payload["dimming"]
        if "color_temperature" in payload:
            attributes["color_temperature"] = payload["color_temperature"]
        metadata = payload.get("metadata") or {}
        if "name" in metadata:
            attributes["friendly_name"] = metadata["name"]
        return attributes

    @staticmethod
    def _select_scene_attributes(payload: dict[str, Any]) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        metadata = payload.get("metadata") or {}
        if "name" in metadata:
            attributes["friendly_name"] = metadata["name"]
        if "group" in payload:
            attributes["group"] = payload["group"]
        return attributes

    def _headers(self) -> dict[str, str]:
        return {"hue-application-key": str(self.settings.philips_hue_application_key)}


class HomeAutomationService:
    def __init__(self, settings: Settings, proxy: SafeHttpClient) -> None:
        self.settings = settings
        self.proxy = proxy
        self.clients: dict[str, HomeAssistantAutomationClient | PhilipsHueAutomationClient] = {}
        for backend in settings.configured_home_automation_backends():
            if backend == "home-assistant":
                self.clients[backend] = HomeAssistantAutomationClient(settings, proxy)
            elif backend == "philips-hue":
                self.clients[backend] = PhilipsHueAutomationClient(settings, proxy)

    def is_configured(self) -> bool:
        return bool(self.clients)

    def configured_backends(self) -> tuple[str, ...]:
        return tuple(self.clients)

    async def list_entities(self) -> dict[str, Any]:
        entities: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for backend, client in self.clients.items():
            try:
                entities.extend(item.to_dict() for item in await client.list_entities())
            except Exception as exc:
                errors.append({"backend": backend, "message": str(exc)})
        if not entities and errors:
            raise ProviderUnavailable("All configured home automation backends failed to list entities.", details={"errors": errors})
        entities.sort(key=lambda item: (str(item["backend"]), str(item["name"]).lower()))
        return {
            "backends": list(self.configured_backends()),
            "entity_count": len(entities),
            "entities": entities,
            "errors": errors,
        }

    async def list_scenes(self) -> dict[str, Any]:
        scenes: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for backend, client in self.clients.items():
            try:
                scenes.extend(item.to_dict() for item in await client.list_scenes())
            except Exception as exc:
                errors.append({"backend": backend, "message": str(exc)})
        if not scenes and errors:
            raise ProviderUnavailable("All configured home automation backends failed to list scenes.", details={"errors": errors})
        scenes.sort(key=lambda item: (str(item["backend"]), str(item["name"]).lower()))
        return {
            "backends": list(self.configured_backends()),
            "scene_count": len(scenes),
            "scenes": scenes,
            "errors": errors,
        }

    async def toggle_light(self, entity_id: str) -> dict[str, Any]:
        backend_name, backend_entity_id = self._resolve_entity_identifier(entity_id)
        return await self.clients[backend_name].toggle_light(backend_entity_id)

    async def activate_scene(self, scene_id: str) -> dict[str, Any]:
        backend_name, backend_scene_id = self._resolve_scene_identifier(scene_id)
        return await self.clients[backend_name].activate_scene(backend_scene_id)

    def _resolve_entity_identifier(self, entity_id: str) -> tuple[str, str]:
        if ":" in entity_id:
            backend, raw_identifier = entity_id.split(":", 1)
            client = self.clients.get(backend)
            if client is None:
                raise ToolValidationFailure("Unknown home automation backend.", details={"entity_id": entity_id})
            if not client.allows_entity(raw_identifier):
                raise ToolValidationFailure("Home automation light is not allowlisted.", details={"entity_id": entity_id})
            return backend, raw_identifier
        matches = [backend for backend, client in self.clients.items() if client.allows_entity(entity_id)]
        if not matches:
            raise ToolValidationFailure("Home automation light is not allowlisted.", details={"entity_id": entity_id})
        if len(matches) > 1:
            raise ToolValidationFailure(
                "Home automation light identifier is ambiguous across backends.",
                details={"entity_id": entity_id, "backends": matches},
            )
        return matches[0], entity_id

    def _resolve_scene_identifier(self, scene_id: str) -> tuple[str, str]:
        if ":" in scene_id:
            backend, raw_identifier = scene_id.split(":", 1)
            client = self.clients.get(backend)
            if client is None:
                raise ToolValidationFailure("Unknown home automation backend.", details={"scene_id": scene_id})
            if not client.allows_scene(raw_identifier):
                raise ToolValidationFailure("Home automation scene is not allowlisted.", details={"scene_id": scene_id})
            return backend, raw_identifier
        matches = [backend for backend, client in self.clients.items() if client.allows_scene(scene_id)]
        if not matches:
            raise ToolValidationFailure("Home automation scene is not allowlisted.", details={"scene_id": scene_id})
        if len(matches) > 1:
            raise ToolValidationFailure(
                "Home automation scene identifier is ambiguous across backends.",
                details={"scene_id": scene_id, "backends": matches},
            )
        return matches[0], scene_id