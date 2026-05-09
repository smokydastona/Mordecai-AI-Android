from __future__ import annotations

import shutil
import subprocess

from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai_core.tool_registry import AutomationMismatch, PermissionDenied, ToolManifest


class AccessibilityToolProvider:
    def __init__(self, settings: Settings, policy: PolicyEngine) -> None:
        self.settings = settings
        self.policy = policy

    def tools(self) -> list[tuple[ToolManifest, object]]:
        return [
            (
                ToolManifest(
                    tool="android.accessibility_dump",
                    provider="provider.accessibility",
                    permissions=("android-control", "accessibility"),
                    description="Capture a read-only UI hierarchy dump through adb and uiautomator.",
                    input_schema={},
                    output_schema={"stdout": "string", "stderr": "string"},
                    risk_level="high",
                    confirmation_policy="always",
                    safe_mode_behavior="read-only",
                    sandbox_profile="device-control",
                ),
                self.dump_ui,
            )
        ]

    def dump_ui(self) -> dict[str, str]:
        if not self.settings.enable_android_control:
            raise PermissionDenied("Android control is disabled.")
        if shutil.which("adb") is None:
            raise AutomationMismatch("adb is not available on PATH.")
        command = ["adb", "exec-out", "uiautomator", "dump", "/dev/tty"]
        decision = self.policy.validate_command(" ".join(command))
        if not decision.allowed:
            raise PermissionDenied(decision.reason)
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise AutomationMismatch(result.stderr.strip() or "uiautomator dump failed")
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}