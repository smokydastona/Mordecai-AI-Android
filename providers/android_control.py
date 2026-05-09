from __future__ import annotations

from mordecai.android_control import AndroidController
from mordecai_core.tool_registry import AutomationMismatch, ToolManifest


class AndroidControlToolProvider:
    def __init__(self, controller: AndroidController) -> None:
        self.controller = controller

    def tools(self) -> list[tuple[ToolManifest, object]]:
        return [
            (
                ToolManifest(
                    tool="android.control",
                    provider="provider.android-control",
                    permissions=("android-control",),
                    description="Execute allowlisted Android control actions through adb.",
                    input_schema={"action": "string", "arguments": "array"},
                    output_schema={"stdout": "string", "stderr": "string"},
                    risk_level="high",
                    confirmation_policy="always",
                    safe_mode_behavior="deny",
                    sandbox_profile="device-control",
                ),
                self.execute,
            )
        ]

    def execute(self, action: str, arguments: list[object]) -> dict[str, str]:
        try:
            return self.controller.perform(action, [str(argument) for argument in arguments])
        except ValueError as exc:
            raise AutomationMismatch(str(exc), details={"action": action}) from exc
