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


def test_proxy_blocks_sensitive_query_values_even_on_allowlisted_domain(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = SafeHttpClient(settings, policy, store)

    try:
        asyncio.run(proxy._gate_request("https://api.github.com/search/users?q=user@example.com", "GET"))
    except PermissionError as exc:
        assert "personal data" in str(exc).lower()
    else:
        raise AssertionError("Expected personal data query value to be blocked")


def test_proxy_blocks_sensitive_post_payloads(tmp_path):
    settings = Settings(workspace_dir=tmp_path, state_dir=tmp_path / ".mordecai")
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = SafeHttpClient(settings, policy, store)

    try:
        asyncio.run(proxy.gate_request("https://api.openai.com/v1/chat/completions", "POST", {"phone": "+1 555 123 4567"}))
    except PermissionError as exc:
        assert "personal data" in str(exc).lower()
    else:
        raise AssertionError("Expected personal data payload to be blocked")


def test_proxy_request_json_supports_put_for_allowlisted_home_automation_hosts(tmp_path):
    settings = Settings(
        workspace_dir=tmp_path,
        state_dir=tmp_path / ".mordecai",
        enable_home_automation=True,
        philips_hue_allowed_hosts=["192.168.1.20"],
    )
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.host == "192.168.1.20"
        return httpx.Response(200, json={"data": [{"id": "light-1"}]}, request=request)

    proxy = SafeHttpClient(
        settings,
        policy,
        store,
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
    )

    payload = asyncio.run(
        proxy.put_json("https://192.168.1.20/clip/v2/resource/light/light-1", {"on": {"on": True}})
    )

    assert payload["data"][0]["id"] == "light-1"