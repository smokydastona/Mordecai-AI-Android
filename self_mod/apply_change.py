from __future__ import annotations

import argparse
import json
from typing import Sequence

from mordecai.config import ensure_state_dirs, get_settings
from mordecai.policy import PolicyEngine
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore


def _manager() -> SelfImprovementManager:
    settings = get_settings()
    ensure_state_dirs(settings)
    return SelfImprovementManager(settings, PolicyEngine(settings), StateStore(settings.state_dir, settings.max_log_entries))


def apply_candidate(candidate_id: str) -> dict[str, object]:
    return _manager().apply_candidate(candidate_id).model_dump(mode="json")


def rollback_candidate(candidate_id: str) -> dict[str, object]:
    return _manager().rollback_candidate(candidate_id).model_dump(mode="json")


def list_candidates() -> list[dict[str, object]]:
    return [candidate.model_dump(mode="json") for candidate in _manager().list_candidates()]


def list_backups() -> list[dict[str, object]]:
    return [backup.model_dump(mode="json") for backup in _manager().list_backups()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply, roll back, or inspect Mordecai self-mod candidates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("candidate_id")

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("candidate_id")

    subparsers.add_parser("list")
    subparsers.add_parser("backups")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "apply":
        payload = apply_candidate(args.candidate_id)
    elif args.command == "rollback":
        payload = rollback_candidate(args.candidate_id)
    elif args.command == "list":
        payload = list_candidates()
    else:
        payload = list_backups()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())