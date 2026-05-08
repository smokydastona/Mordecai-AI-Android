from __future__ import annotations

import shutil
import subprocess

from mordecai.config import Settings
from mordecai.policy import PolicyEngine


class AndroidController:
    def __init__(self, settings: Settings, policy: PolicyEngine) -> None:
        self.settings = settings
        self.policy = policy

    def perform(self, action: str, arguments: list[str]) -> dict[str, str]:
        if not self.settings.enable_android_control:
            raise PermissionError("Android control is disabled")
        if shutil.which("adb") is None:
            raise RuntimeError("adb is not available on PATH")
        command = self._build_command(action, arguments)
        decision = self.policy.validate_command(" ".join(command))
        if not decision.allowed:
            raise PermissionError(decision.reason)
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "adb command failed")
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}

    def _build_command(self, action: str, arguments: list[str]) -> list[str]:
        if action == "tap" and len(arguments) == 2:
            return ["adb", "shell", "input", "tap", *arguments]
        if action == "swipe" and len(arguments) == 4:
            return ["adb", "shell", "input", "swipe", *arguments]
        if action == "type" and len(arguments) == 1:
            return ["adb", "shell", "input", "text", arguments[0]]
        if action == "open_app" and len(arguments) == 1:
            package = arguments[0]
            if package not in self.settings.allowed_android_packages:
                raise PermissionError(f"Package '{package}' is not allowlisted")
            return ["adb", "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]
        raise ValueError("Unsupported Android action or argument count")