from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def run_pytest(workspace: Path | None = None, pytest_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "pytest", *(pytest_args or ["-q"])]
    return subprocess.run(
        command,
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Mordecai test suite from the self_mod layer.")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("pytest_args", nargs="*")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = run_pytest(args.workspace, args.pytest_args or ["-q"])
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())