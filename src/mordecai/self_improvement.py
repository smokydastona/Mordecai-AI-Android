from __future__ import annotations

import difflib
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from mordecai.config import Settings
from mordecai.models import ImprovementBackupRecord, ImprovementCandidate, ImprovementRequest, RuntimeEvent
from mordecai.policy import PolicyEngine
from mordecai.store import StateStore


class SelfImprovementManager:
    IGNORE_NAMES = (
        ".git",
        ".mordecai",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "*.egg-info",
        "*.pyc",
    )

    def __init__(self, settings: Settings, policy: PolicyEngine, store: StateStore) -> None:
        self.settings = settings
        self.policy = policy
        self.store = store

    def create_candidate(self, request: ImprovementRequest) -> ImprovementCandidate:
        file_decision = self.policy.validate_file_changes(request.changes)
        content_decision = self.policy.validate_change_content(request.changes)
        blocked = [] if file_decision.allowed else file_decision.reason.split(": ", 1)[-1].split(", ")
        diff_filters_blocked = [] if content_decision.allowed else content_decision.reason.split(": ", 1)[-1].split(", ")
        candidate_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
        candidate_root = self.settings.state_dir / "candidates" / candidate_id
        candidate_root.mkdir(parents=True, exist_ok=True)
        candidate_workspace = self._prepare_candidate_workspace(candidate_root) if file_decision.allowed and content_decision.allowed else None
        diff_preview: dict[str, str] = {}
        files: list[str] = []
        for change in request.changes:
            target_path = self.settings.workspace_dir / Path(change.path)
            files.append(Path(change.path).as_posix())
            original = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
            preview = "".join(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    change.content.splitlines(keepends=True),
                    fromfile=f"a/{Path(change.path).as_posix()}",
                    tofile=f"b/{Path(change.path).as_posix()}",
                )
            )
            diff_preview[Path(change.path).as_posix()] = preview
            if candidate_workspace is not None:
                sandbox_path = candidate_workspace / Path(change.path)
                sandbox_path.parent.mkdir(parents=True, exist_ok=True)
                sandbox_path.write_text(change.content, encoding="utf-8")
        tests_passed = None
        test_output = "Not run"
        if request.run_tests and file_decision.allowed and content_decision.allowed:
            tests_passed, test_output = self._run_tests(candidate_workspace)
        candidate = ImprovementCandidate(
            candidate_id=candidate_id,
            description=request.description,
            created_at=datetime.now(UTC),
            files=files,
            protected_paths_blocked=blocked,
            diff_filters_blocked=diff_filters_blocked,
            tests_passed=tests_passed,
            test_output=test_output,
            diff_preview=diff_preview,
            applied=False,
        )
        self.store.save_candidate(candidate)
        self.store.append_event(RuntimeEvent(category="improvement", detail=f"Candidate created: {candidate_id}"))
        if (request.auto_apply or self.settings.auto_apply_improvements) and candidate.tests_passed and not candidate.protected_paths_blocked and not candidate.diff_filters_blocked:
            self.apply_candidate(candidate_id)
            candidate.applied = True
            self.store.save_candidate(candidate)
        return candidate

    def apply_candidate(self, candidate_id: str) -> ImprovementCandidate:
        candidate = self._get_candidate(candidate_id)
        if candidate.protected_paths_blocked:
            raise PermissionError("Candidate touches protected paths")
        if candidate.diff_filters_blocked:
            raise PermissionError("Candidate diff blocked by policy filters")
        if candidate.tests_passed is False:
            raise RuntimeError("Candidate tests failed")
        candidate_root = self.settings.state_dir / "candidates" / candidate_id
        candidate_workspace = candidate_root / "workspace"
        backup_root = self.settings.state_dir / "backups" / candidate_id
        backup_root.mkdir(parents=True, exist_ok=True)
        restored_files: list[str] = []
        for relative_path in candidate.files:
            live_path = self.settings.workspace_dir / relative_path
            sandbox_path = candidate_workspace / relative_path
            live_path.parent.mkdir(parents=True, exist_ok=True)
            if live_path.exists():
                backup_path = backup_root / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                backup_path.write_text(live_path.read_text(encoding="utf-8"), encoding="utf-8")
            live_path.write_text(sandbox_path.read_text(encoding="utf-8"), encoding="utf-8")
            restored_files.append(relative_path)
        candidate.applied = True
        self.store.save_candidate(candidate)
        self.store.save_backup_record(ImprovementBackupRecord(candidate_id=candidate_id, files=restored_files))
        self.store.append_event(RuntimeEvent(category="improvement", detail=f"Candidate applied: {candidate_id}"))
        return candidate

    def list_candidates(self) -> list[ImprovementCandidate]:
        return self.store.read_candidates()

    def list_backups(self) -> list[ImprovementBackupRecord]:
        return self.store.read_backup_records()

    def rollback_candidate(self, candidate_id: str) -> ImprovementCandidate:
        candidate = self._get_candidate(candidate_id)
        backup_root = self.settings.state_dir / "backups" / candidate_id
        if not backup_root.exists():
            raise FileNotFoundError(f"No backup exists for candidate '{candidate_id}'")
        for relative_path in candidate.files:
            backup_path = backup_root / relative_path
            live_path = self.settings.workspace_dir / relative_path
            if backup_path.exists():
                live_path.parent.mkdir(parents=True, exist_ok=True)
                live_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
            elif live_path.exists():
                live_path.unlink()
        candidate.applied = False
        self.store.save_candidate(candidate)
        self.store.append_event(RuntimeEvent(category="improvement", detail=f"Candidate rolled back: {candidate_id}"))
        return candidate

    def _get_candidate(self, candidate_id: str) -> ImprovementCandidate:
        for candidate in self.store.read_candidates():
            if candidate.candidate_id == candidate_id:
                return candidate
        raise KeyError(f"Unknown candidate '{candidate_id}'")

    def _prepare_candidate_workspace(self, candidate_root: Path) -> Path:
        workspace_copy = candidate_root / "workspace"
        ignore = shutil.ignore_patterns(*self.IGNORE_NAMES)
        shutil.copytree(self.settings.workspace_dir, workspace_copy, dirs_exist_ok=True, ignore=ignore)
        return workspace_copy

    def _run_tests(self, workspace_dir: Path) -> tuple[bool, str]:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=workspace_dir,
            text=True,
            capture_output=True,
            check=False,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode == 0, output