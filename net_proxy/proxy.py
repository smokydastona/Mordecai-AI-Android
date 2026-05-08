from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml

from mordecai.config import Settings, ensure_state_dirs, get_settings
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.store import StateStore


@dataclass(slots=True)
class ProxyLimits:
    max_requests_per_minute: int
    timeout_seconds: float


@dataclass(slots=True)
class ProxyLogging:
    enabled: bool
    destination: str


@dataclass(slots=True)
class NetProxyConfig:
    allowed_domains: list[str]
    limits: ProxyLimits
    logging: ProxyLogging


def load_proxy_config(config_path: Path | None = None) -> NetProxyConfig:
    path = config_path or Path(__file__).with_name("config.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return NetProxyConfig(
        allowed_domains=list(raw["allowed_domains"]),
        limits=ProxyLimits(
            max_requests_per_minute=int(raw["limits"]["max_requests_per_minute"]),
            timeout_seconds=float(raw["limits"]["timeout_seconds"]),
        ),
        logging=ProxyLogging(
            enabled=bool(raw["logging"]["enabled"]),
            destination=str(raw["logging"]["destination"]),
        ),
    )


class ConfigurableNetProxy(SafeHttpClient):
    def __init__(self, config_path: Path | None = None, base_settings: Settings | None = None) -> None:
        config = load_proxy_config(config_path)
        settings = (base_settings or get_settings()).model_copy(deep=True)
        settings.allowed_domains = config.allowed_domains
        settings.max_requests_per_minute = config.limits.max_requests_per_minute
        settings.proxy_timeout_seconds = config.limits.timeout_seconds
        logging_path = Path(config.logging.destination)
        settings.state_dir = (settings.workspace_dir / logging_path).resolve().parent if not logging_path.is_absolute() else logging_path.resolve().parent
        ensure_state_dirs(settings)
        store = StateStore(settings.state_dir, settings.max_log_entries)
        super().__init__(settings, PolicyEngine(settings), store)
        self.config = config


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Standalone safe network proxy entry point for Mordecai.")
    parser.add_argument("command", choices=["fetch", "web", "github"])
    parser.add_argument("target")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    proxy = ConfigurableNetProxy(args.config)
    if args.command == "fetch":
        payload: Any = asyncio.run(proxy.fetch_text(args.target))
    elif args.command == "web":
        payload = asyncio.run(proxy.web_search(args.target))
    else:
        payload = asyncio.run(proxy.github_search_repositories(args.target, args.limit))
    print(payload if isinstance(payload, str) else json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())