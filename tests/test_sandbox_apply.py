from mordecai.config import Settings
from mordecai.models import ImprovementRequest
from mordecai.policy import PolicyEngine
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore


def test_sandbox_apply_promotes_then_rollback_restores_live_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    state_dir = tmp_path / ".mordecai"
    src_dir = workspace / "src" / "demo"
    tests_dir = workspace / "tests"
    src_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    (workspace / "pyproject.toml").write_text("[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n", encoding="utf-8")
    (src_dir / "calc.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (tests_dir / "test_calc.py").write_text(
        "from src.demo.calc import value\n\n\ndef test_value():\n    assert value() == 7\n",
        encoding="utf-8",
    )

    settings = Settings(workspace_dir=workspace, state_dir=state_dir)
    policy = PolicyEngine(settings)
    store = StateStore(state_dir, settings.max_log_entries)
    manager = SelfImprovementManager(settings, policy, store)

    candidate = manager.create_candidate(
        ImprovementRequest(
            description="Promote and rollback calc change",
            changes=[{"path": "src/demo/calc.py", "content": "def value():\n    return 7\n"}],
            run_tests=True,
        )
    )

    applied = manager.apply_candidate(candidate.candidate_id)
    rolled_back = manager.rollback_candidate(candidate.candidate_id)

    assert candidate.tests_passed is True
    assert applied.applied is True
    assert rolled_back.applied is False
    assert (workspace / "src" / "demo" / "calc.py").read_text(encoding="utf-8") == "def value():\n    return 1\n"
