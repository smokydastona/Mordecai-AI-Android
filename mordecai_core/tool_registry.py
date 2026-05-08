from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from mordecai_core.events import EventBus


ToolHandler = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ToolManifest:
    tool: str
    permissions: tuple[str, ...]
    description: str
    input_schema: dict[str, object] = field(default_factory=dict)
    output_schema: dict[str, object] = field(default_factory=dict)


class ToolRegistry:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self._manifests: dict[str, ToolManifest] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, manifest: ToolManifest, handler: ToolHandler) -> None:
        self._manifests[manifest.tool] = manifest
        self._handlers[manifest.tool] = handler
        self.event_bus.publish(
            "tool.registered",
            {"tool": manifest.tool, "permissions": list(manifest.permissions)},
        )

    def list_tools(self) -> list[ToolManifest]:
        return [self._manifests[name] for name in sorted(self._manifests)]

    def describe(self, tool_name: str) -> ToolManifest:
        return self._manifests[tool_name]

    def invoke(self, tool_name: str, *args: object, **kwargs: object) -> Any:
        manifest = self.describe(tool_name)
        self.event_bus.publish("tool.invoked", {"tool": manifest.tool})
        result = self._handlers[tool_name](*args, **kwargs)
        self.event_bus.publish("tool.completed", {"tool": manifest.tool})
        return result