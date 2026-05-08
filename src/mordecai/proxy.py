from __future__ import annotations

import asyncio
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote_plus

import httpx

from mordecai.config import Settings
from mordecai.models import ProxyRequestRecord, RuntimeEvent
from mordecai.policy import PolicyEngine
from mordecai.store import StateStore


class SafeHttpClient:
    def __init__(self, settings: Settings, policy: PolicyEngine, store: StateStore) -> None:
        self.settings = settings
        self.policy = policy
        self.store = store
        self._request_times: deque[datetime] = deque()
        self._lock = asyncio.Lock()

    async def fetch_text(self, url: str) -> str:
        await self._gate_request(url, "GET")
        async with httpx.AsyncClient(timeout=self.settings.proxy_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mordecai/0.1"})
            response.raise_for_status()
            return response.text

    async def fetch_json(self, url: str) -> Any:
        await self._gate_request(url, "GET")
        async with httpx.AsyncClient(timeout=self.settings.proxy_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mordecai/0.1", "Accept": "application/json"})
            response.raise_for_status()
            return response.json()

    async def post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
        await self._gate_request(url, "POST")
        request_headers = {
            "User-Agent": "Mordecai/0.1",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)
        async with httpx.AsyncClient(timeout=self.settings.proxy_timeout_seconds, follow_redirects=True) as client:
            response = await client.post(url, json=payload, headers=request_headers)
            response.raise_for_status()
            return response.json()

    async def github_search_repositories(self, query: str, limit: int) -> list[dict[str, Any]]:
        url = f"https://api.github.com/search/repositories?q={quote_plus(query)}&per_page={limit}"
        payload = await self.fetch_json(url)
        items = payload.get("items", [])
        return [
            {
                "full_name": item["full_name"],
                "description": item.get("description"),
                "url": item["html_url"],
                "stars": item.get("stargazers_count", 0),
            }
            for item in items
        ]

    async def web_search(self, query: str) -> dict[str, Any]:
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        payload = await self.fetch_json(url)
        related = payload.get("RelatedTopics", [])
        simplified: list[dict[str, Any]] = []
        for entry in related[:5]:
            if isinstance(entry, dict) and entry.get("Text"):
                simplified.append({"text": entry.get("Text"), "url": entry.get("FirstURL")})
        return {
            "abstract": payload.get("AbstractText", ""),
            "heading": payload.get("Heading", query),
            "related": simplified,
        }

    async def _gate_request(self, url: str, method: str) -> None:
        decision = self.policy.validate_url(url)
        self.store.append_proxy_record(
            ProxyRequestRecord(method=method, url=url, allowed=decision.allowed, reason=decision.reason)
        )
        self.store.append_event(RuntimeEvent(category="proxy", detail=f"{method} {url} -> {decision.reason}"))
        if not decision.allowed:
            raise PermissionError(decision.reason)
        async with self._lock:
            now = datetime.now(UTC)
            cutoff = now - timedelta(minutes=1)
            while self._request_times and self._request_times[0] < cutoff:
                self._request_times.popleft()
            if len(self._request_times) >= self.settings.max_requests_per_minute:
                raise RuntimeError("Outbound request rate limit exceeded")
            self._request_times.append(now)