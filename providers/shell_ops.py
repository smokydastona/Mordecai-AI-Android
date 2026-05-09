from __future__ import annotations

import subprocess
from pathlib import Path

from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai_core.tool_registry import PermissionDenied, ToolManifest, ToolValidationFailure


class ShellToolProvider:
    def __init__(self, settings: Settings, policy: PolicyEngine) -> None:
        self.settings = settings
        self.policy = policy

    def tools(self) -> list[tuple[ToolManifest, object]]:
        return [
            (
                ToolManifest(
                    tool="shell.run",
                    provider="provider.shell",
                    permissions=("shell",),
                    description="Run a bounded local command inside the workspace.",
                    input_schema={"command": "array", "cwd": "string"},
                    output_schema={"stdout": "string", "stderr": "string", "returncode": "integer"},
                    risk_level="high",
                    confirmation_policy="always",
                    safe_mode_behavior="deny",
                    sandbox_profile="workspace-write",
                ),
                self.run,
            )
        ]

    def run(self, command: list[object], cwd: str = ".") -> dict[str, object]:
        if not command:
            raise ToolValidationFailure("Shell command cannot be empty.")
        command_parts = [str(part) for part in command]
        decision = self.policy.validate_command(" ".join(command_parts))
        if not decision.allowed:
            raise PermissionDenied(decision.reason, details={"command": command_parts})
        working_dir = self._resolve_workspace_path(cwd)
        result = subprocess.run(command_parts, cwd=working_dir, text=True, capture_output=True, check=False)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    def _resolve_workspace_path(self, relative_path: str) -> Path:
        candidate = (self.settings.workspace_dir / relative_path).resolve()
        if not candidate.is_relative_to(self.settings.workspace_dir.resolve()):
            raise PermissionDenied("Shell working directory escapes the workspace.", details={"cwd": relative_path})
        return candidate