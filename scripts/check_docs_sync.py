from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOC_TRACKED_FILES = {
    "CHANGELOG.md",
    "README.md",
    ".github/copilot-instructions.md",
}
DOC_TRACKED_PREFIXES = ("docs/",)
IMPLEMENTATION_PREFIXES = (
    "src/",
    "tests/",
    "android/",
    "sandbox/",
    "mordecai_core/",
    "self_mod/",
    "net_proxy/",
    "voice/",
    "scripts/",
    "prompts/",
)
IMPLEMENTATION_FILES = {
    "pyproject.toml",
    ".env.example",
}
PROCESS_PREFIXES = (
    ".github/workflows/",
    ".github/ISSUE_TEMPLATE/",
)
PROCESS_FILES = {
    ".github/PULL_REQUEST_TEMPLATE.md",
}


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def detect_base_ref(explicit_base: str | None) -> str:
    if explicit_base:
        return explicit_base
    github_base_ref = os.environ.get("GITHUB_BASE_REF")
    github_event_before = os.environ.get("GITHUB_EVENT_BEFORE")
    if github_base_ref:
        return f"origin/{github_base_ref}"
    if github_event_before and github_event_before != "0000000000000000000000000000000000000000":
        return github_event_before
    try:
        return _git("rev-parse", "HEAD^")
    except RuntimeError:
        return _git("rev-list", "--max-parents=0", "HEAD")


def changed_files(base_ref: str) -> list[str]:
    output = _git("diff", "--name-only", f"{base_ref}...HEAD")
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def is_doc_file(path: str) -> bool:
    return path in DOC_TRACKED_FILES or path.startswith(DOC_TRACKED_PREFIXES)


def is_process_file(path: str) -> bool:
    return path in PROCESS_FILES or path.startswith(PROCESS_PREFIXES)


def is_implementation_file(path: str) -> bool:
    if is_doc_file(path):
        return False
    return path in IMPLEMENTATION_FILES or path.startswith(IMPLEMENTATION_PREFIXES) or is_process_file(path)


def validate_docs_sync(paths: list[str]) -> list[str]:
    errors: list[str] = []
    implementation_changed = any(is_implementation_file(path) for path in paths)
    process_changed = any(is_process_file(path) for path in paths)
    if not implementation_changed:
        return errors

    if "CHANGELOG.md" not in paths:
        errors.append("CHANGELOG.md must be updated whenever implementation or process files change.")
    if "README.md" not in paths:
        errors.append("README.md must be updated whenever implementation or process files change.")
    if not any(path.startswith("docs/") for path in paths):
        errors.append("At least one file under docs/ must be updated whenever implementation or process files change.")
    if process_changed and ".github/copilot-instructions.md" not in paths:
        errors.append(".github/copilot-instructions.md must be updated when workflow or repo process files change.")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when implementation changes are pushed without changelog and docs updates.")
    parser.add_argument("--base", help="Git base ref or sha to compare against. Defaults to HEAD^ or CI metadata.")
    args = parser.parse_args(argv)

    base_ref = detect_base_ref(args.base)
    paths = changed_files(base_ref)
    errors = validate_docs_sync(paths)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print("Changed files:", file=sys.stderr)
        for path in paths:
            print(f"- {path}", file=sys.stderr)
        return 1
    print("Documentation sync check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())