from __future__ import annotations

import argparse
import json
from typing import Sequence

from mordecai_core.runtime import get_runtime_components


class GitTools:
    def status(self) -> dict[str, object]:
        return get_runtime_components().git_service.status()

    def backup(self, message: str, push: bool = False) -> dict[str, object]:
        return get_runtime_components().git_service.backup(message, push)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Git operations for the Mordecai runtime.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("message")
    backup_parser.add_argument("--push", action="store_true")

    args = parser.parse_args(list(argv) if argv is not None else None)
    tools = GitTools()

    if args.command == "status":
        print(json.dumps(tools.status(), indent=2))
    else:
        print(json.dumps(tools.backup(args.message, push=args.push), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())