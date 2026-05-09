from __future__ import annotations

from mordecai.git_tools import GitService
from mordecai_core.tool_registry import ToolManifest


class GitOpsToolProvider:
    def __init__(self, git_service: GitService) -> None:
        self.git_service = git_service

    def tools(self) -> list[tuple[ToolManifest, object]]:
        return [
            (
                ToolManifest(
                    tool="git.backup",
                    provider="provider.git",
                    permissions=("git",),
                    description="Create a git backup commit and optionally push it.",
                    input_schema={"message": "string", "push": "boolean"},
                    output_schema={"commit": "string", "push": "string"},
                    risk_level="high",
                    confirmation_policy="always",
                    safe_mode_behavior="deny",
                    sandbox_profile="workspace-write",
                ),
                self.backup,
            )
        ]

    def backup(self, message: str, push: bool) -> dict[str, object]:
        return self.git_service.backup(message, push)
