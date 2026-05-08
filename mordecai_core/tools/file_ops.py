from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from mordecai.config import get_settings


class FileTools:
    def __init__(self, workspace_dir: Path | None = None) -> None:
        self.workspace_dir = (workspace_dir or get_settings().workspace_dir).resolve()

    def list_files(self, pattern: str = "**/*") -> list[str]:
        return sorted(
            path.relative_to(self.workspace_dir).as_posix()
            for path in self.workspace_dir.glob(pattern)
            if path.is_file()
        )

    def read_text(self, relative_path: str) -> str:
        return self._resolve(relative_path).read_text(encoding="utf-8")

    def write_text(self, relative_path: str, content: str) -> Path:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def delete(self, relative_path: str) -> None:
        path = self._resolve(relative_path)
        if path.exists():
            path.unlink()

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.workspace_dir / relative_path).resolve()
        if not candidate.is_relative_to(self.workspace_dir):
            raise PermissionError(f"Path escapes workspace: {relative_path}")
        return candidate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Workspace file operations for Mordecai.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("pattern", nargs="?", default="**/*")

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("path")

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("path")
    write_parser.add_argument("content")

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("path")

    args = parser.parse_args(list(argv) if argv is not None else None)
    tools = FileTools()

    if args.command == "list":
        print("\n".join(tools.list_files(args.pattern)))
    elif args.command == "read":
        print(tools.read_text(args.path))
    elif args.command == "write":
        print(tools.write_text(args.path, args.content))
    elif args.command == "delete":
        tools.delete(args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())