from __future__ import annotations

import asyncio
import hashlib
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx

from mordecai.config import Settings
from mordecai.models import ProxyRequestRecord, RuntimeEvent
from mordecai.policy import PolicyEngine
from mordecai.store import StateStore


class SafeHttpClient:
    def __init__(
        self,
        settings: Settings,
        policy: PolicyEngine,
        store: StateStore,
        client_factory: callable | None = None,
    ) -> None:
        self.settings = settings
        self.policy = policy
        self.store = store
        self._request_times: deque[datetime] = deque()
        self._lock = asyncio.Lock()
        self._client_factory = client_factory or self._default_client_factory

    async def fetch_text(self, url: str) -> str:
        response = await self._request("GET", url)
        return response.text

    async def fetch_json(self, url: str) -> Any:
        response = await self._request("GET", url, headers={"Accept": "application/json"})
        return response.json()

    async def post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
        request_headers = {
            "User-Agent": "Mordecai/0.1",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)
        response = await self._request("POST", url, headers=request_headers, json=payload)
        return response.json()

    async def download_file(
        self,
        url: str,
        destination: Path,
        *,
        sha256: str | None = None,
        max_bytes: int | None = None,
        executable: bool = False,
    ) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination.with_name(f"{destination.name}.download")
        if temp_path.exists():
            temp_path.unlink()

        headers = {"User-Agent": "Mordecai/0.1", "Accept": "application/octet-stream"}
        async with self._client_factory() as client:
            current_url = url
            for _ in range(6):
                await self._gate_request(current_url, "GET")
                async with client.stream("GET", current_url, headers=headers, follow_redirects=False) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise RuntimeError("Redirect response did not include a location header")
                        current_url = urljoin(str(response.request.url), location)
                        continue
                    response.raise_for_status()

                    content_length = response.headers.get("content-length")
                    if max_bytes is not None and content_length:
                        if int(content_length) > max_bytes:
                            raise RuntimeError(f"Download exceeds size limit of {max_bytes} bytes")

                    total_bytes = 0
                    digest = hashlib.sha256() if sha256 else None
                    try:
                        with temp_path.open("wb") as handle:
                            async for chunk in response.aiter_bytes():
                                if not chunk:
                                    continue
                                handle.write(chunk)
                                total_bytes += len(chunk)
                                if max_bytes is not None and total_bytes > max_bytes:
                                    raise RuntimeError(f"Download exceeds size limit of {max_bytes} bytes")
                                if digest is not None:
                                    digest.update(chunk)
                    except Exception:
                        if temp_path.exists():
                            temp_path.unlink()
                        raise

                    if digest is not None and digest.hexdigest().lower() != sha256.lower():
                        temp_path.unlink(missing_ok=True)
                        raise RuntimeError(f"SHA-256 mismatch while downloading {destination.name}")

                    temp_path.replace(destination)
                    if executable:
                        destination.chmod(0o755)
                    return destination

        raise RuntimeError(f"Too many redirects while downloading {url}")

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

    def _default_client_factory(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.settings.proxy_timeout_seconds, follow_redirects=False)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        request_headers = {"User-Agent": "Mordecai/0.1"}
        if headers:
            request_headers.update(headers)

        async with self._client_factory() as client:
            current_url = url
            for _ in range(6):
                await self._gate_request(current_url, method)
                response = await client.request(
                    method,
                    current_url,
                    headers=request_headers,
                    json=json,
                    follow_redirects=False,
                )
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        response.raise_for_status()
                    current_url = urljoin(str(response.request.url), location)
                    continue
                response.raise_for_status()
                return response

        raise RuntimeError(f"Too many redirects while requesting {url}")

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