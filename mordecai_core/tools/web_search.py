from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Sequence

from mordecai_core.runtime import get_runtime_components


class WebTools:
    async def search_web(self, query: str) -> dict[str, Any]:
        return await get_runtime_components().proxy.web_search(query)

    async def search_github(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return await get_runtime_components().proxy.github_search_repositories(query, limit)

    async def fetch_text(self, url: str) -> str:
        return await get_runtime_components().proxy.fetch_text(url)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Web-facing tools backed by Mordecai's safe proxy.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    web_parser = subparsers.add_parser("web")
    web_parser.add_argument("query")

    github_parser = subparsers.add_parser("github")
    github_parser.add_argument("query")
    github_parser.add_argument("--limit", type=int, default=5)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("url")

    args = parser.parse_args(list(argv) if argv is not None else None)
    tools = WebTools()

    if args.command == "web":
        payload = asyncio.run(tools.search_web(args.query))
        print(json.dumps(payload, indent=2))
    elif args.command == "github":
        payload = asyncio.run(tools.search_github(args.query, args.limit))
        print(json.dumps(payload, indent=2))
    else:
        print(asyncio.run(tools.fetch_text(args.url)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())