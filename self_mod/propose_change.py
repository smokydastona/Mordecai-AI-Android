from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from mordecai.config import ensure_state_dirs, get_settings
from mordecai.models import ImprovementRequest
from mordecai.policy import PolicyEngine
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore


def _manager() -> SelfImprovementManager:
    settings = get_settings()
    ensure_state_dirs(settings)
    return SelfImprovementManager(settings, PolicyEngine(settings), StateStore(settings.state_dir, settings.max_log_entries))


def load_change_spec(
    spec_path: Path,
    description: str | None = None,
    run_tests: bool = True,
    auto_apply: bool = False,
) -> ImprovementRequest:
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        payload = {"description": description or spec_path.stem, "changes": payload}
    if description is not None:
        payload["description"] = description
    payload.setdefault("run_tests", run_tests)
    payload.setdefault("auto_apply", auto_apply)
    return ImprovementRequest.model_validate(payload)


def propose_candidate(
    spec_path: Path,
    description: str | None = None,
    run_tests: bool = True,
    auto_apply: bool = False,
) -> dict[str, object]:
    request = load_change_spec(spec_path, description=description, run_tests=run_tests, auto_apply=auto_apply)
    return _manager().create_candidate(request).model_dump(mode="json")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Propose a self-modification candidate for Mordecai.")
    parser.add_argument("spec", type=Path, help="Path to a JSON file describing changes or a full ImprovementRequest payload.")
    parser.add_argument("--description")
    parser.add_argument("--no-tests", action="store_true")
    parser.add_argument("--auto-apply", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    payload = propose_candidate(
        args.spec,
        description=args.description,
        run_tests=not args.no_tests,
        auto_apply=args.auto_apply,
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())