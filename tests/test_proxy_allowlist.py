import asyncio

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