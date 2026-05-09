import asyncio
from urllib.parse import urlparse

import httpx

from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.store import StateStore


def test_proxy_blocks_disallowed_domains_and_logs_decision(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = SafeHttpClient(settings, policy, store)

    try:
        asyncio.run(proxy._gate_request("https://example.com/blocked", "GET"))
    except PermissionError as exc:
        assert "allowlist" in str(exc)
    else:
        raise AssertionError("Expected disallowed domain to be blocked")

    record = store.read_proxy_records()[-1]
    assert record.allowed is False
    assert record.url == "https://example.com/blocked"


def test_proxy_allows_allowlisted_domains_and_records_success(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = SafeHttpClient(settings, policy, store)

    asyncio.run(proxy._gate_request("https://api.github.com/search/repositories?q=mordecai", "GET"))

    record = store.read_proxy_records()[-1]
    assert record.allowed is True
    assert record.url.startswith("https://api.github.com/")


def test_proxy_blocks_redirect_to_disallowed_domain(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "huggingface.co":
            return httpx.Response(302, headers={"location": "https://example.com/file.bin"}, request=request)
        raise AssertionError(f"Unexpected request to {request.url}")

    proxy = SafeHttpClient(
        settings,
        policy,
        store,
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
    )

    try:
        asyncio.run(proxy.fetch_text("https://huggingface.co/repo/file.txt"))
    except PermissionError as exc:
        assert "allowlist" in str(exc)
    else:
        raise AssertionError("Expected redirect target to be blocked")

    assert store.read_proxy_records()[-1].url == "https://example.com/file.bin"


def test_proxy_download_file_allows_safe_redirect_chain(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    payload = b"model-bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "huggingface.co":
            return httpx.Response(302, headers={"location": "https://cdn-lfs.hf.co/models/test.bin"}, request=request)
        if request.url.host == "cdn-lfs.hf.co":
            return httpx.Response(200, content=payload, headers={"content-length": str(len(payload))}, request=request)
        raise AssertionError(f"Unexpected request to {request.url}")

    proxy = SafeHttpClient(
        settings,
        policy,
        store,
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
    )

    destination = tmp_path / "models" / "test.bin"
    asyncio.run(proxy.download_file("https://huggingface.co/repo/test.bin", destination, max_bytes=1024))

    assert destination.read_bytes() == payload
    logged_hosts = [urlparse(record.url).hostname for record in store.read_proxy_records()]
    assert "huggingface.co" in logged_hosts
    assert "cdn-lfs.hf.co" in logged_hosts