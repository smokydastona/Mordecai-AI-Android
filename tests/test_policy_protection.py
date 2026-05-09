from pathlib import Path

from mordecai.config import Settings
from mordecai.models import ImprovementRequest
from mordecai.policy import PolicyEngine
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore


def test_policy_report_exposes_protected_runtime_surfaces(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    policy = PolicyEngine(settings)

    report = policy.report()

    assert "src/mordecai/main.py" in report.protected_paths
    assert "src/mordecai/policy.py" in report.protected_paths
    assert "src/mordecai/self_improvement.py" in report.protected_paths
    assert "src/mordecai/store.py" in report.protected_paths


def test_self_improvement_candidate_marks_protected_paths_blocked(tmp_path):
    workspace = tmp_path / "workspace"
    state_dir = tmp_path / ".mordecai"
    workspace.mkdir(parents=True)
    settings = Settings(workspace_dir=workspace, state_dir=state_dir)
    policy = PolicyEngine(settings)
    store = StateStore(state_dir, settings.max_log_entries)
    manager = SelfImprovementManager(settings, policy, store)
    protected = Path("src/mordecai/policy.py").as_posix()

    candidate = manager.create_candidate(
        ImprovementRequest(
            description="Attempt protected edit",
            changes=[{"path": protected, "content": "value = 2\n"}],
            run_tests=False,
        )
    )

    assert protected in candidate.protected_paths_blocked
    assert candidate.applied is False


def test_self_improvement_candidate_blocks_mordecai_core_changes(tmp_path):
    workspace = tmp_path / "workspace"
    state_dir = tmp_path / ".mordecai"
    workspace.mkdir(parents=True)
    settings = Settings(workspace_dir=workspace, state_dir=state_dir)
    policy = PolicyEngine(settings)
    store = StateStore(state_dir, settings.max_log_entries)
    manager = SelfImprovementManager(settings, policy, store)
    protected = Path("mordecai_core/tool_registry.py").as_posix()

    candidate = manager.create_candidate(
        ImprovementRequest(
            description="Attempt protected core edit",
            changes=[{"path": protected, "content": "SAFE = False\n"}],
            run_tests=False,
        )
    )

    assert protected in candidate.protected_paths_blocked
    assert candidate.applied is False
