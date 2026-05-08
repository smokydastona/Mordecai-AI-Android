from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Sequence

from mordecai_core.runtime import get_runtime_components


async def run_once(message: str) -> dict[str, Any]:
    response = await get_runtime_components().runtime.chat(message)
    return response.model_dump(mode="json")


def status_snapshot() -> dict[str, Any]:
    return get_runtime_components().runtime.status().model_dump(mode="json")


def interactive_loop(prompt: str = "mordecai> ") -> None:
    while True:
        try:
            message = input(prompt).strip()
        except EOFError:
            print()
            return
        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            return
        payload = asyncio.run(run_once(message))
        print(payload["reply"])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Mordecai from the canonical mordecai_core layer.")
    parser.add_argument("message", nargs="?", help="One-shot message to send to Mordecai.")
    parser.add_argument("--status", action="store_true", help="Print the current runtime status JSON.")
    parser.add_argument("--events", action="store_true", help="Print recent runtime events JSON.")
    parser.add_argument("--interactive", action="store_true", help="Start an interactive terminal loop.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.status:
        print(json.dumps(status_snapshot(), indent=2))
        return 0
    if args.events:
        events = get_runtime_components().runtime.events()
        print(json.dumps(events, indent=2))
        return 0
    if args.interactive or not args.message:
        interactive_loop()
        return 0
    print(json.dumps(asyncio.run(run_once(args.message)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())