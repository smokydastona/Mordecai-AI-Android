from __future__ import annotations

import subprocess
from pathlib import Path


class GitService:
    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.workspace_dir,
            text=True,
            capture_output=True,
            check=False,
            errors="replace",
        )

    def status(self) -> dict[str, object]:
        branch_result = self._run("rev-parse", "--abbrev-ref", "HEAD")
        if branch_result.returncode != 0:
            return {"branch": None, "dirty": False, "status": branch_result.stderr.strip()}
        status_result = self._run("status", "--short")
        lines = [line for line in status_result.stdout.splitlines() if line.strip()]
        return {
            "branch": branch_result.stdout.strip(),
            "dirty": bool(lines),
            "status": lines,
        }

    def backup(self, message: str, push: bool) -> dict[str, object]:
        add_result = self._run("add", ".")
        if add_result.returncode != 0:
            raise RuntimeError(add_result.stderr.strip() or "git add failed")
        commit_result = self._run("commit", "-m", message)
        if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout.lower() and "nothing to commit" not in commit_result.stderr.lower():
            raise RuntimeError(commit_result.stderr.strip() or commit_result.stdout.strip() or "git commit failed")
        push_output = ""
        if push:
            push_result = self._run("push")
            if push_result.returncode != 0:
                raise RuntimeError(push_result.stderr.strip() or "git push failed")
            push_output = push_result.stdout.strip()
        return {
            "commit": commit_result.stdout.strip() or commit_result.stderr.strip() or "nothing to commit",
            "push": push_output,
        }