import asyncio

from mordecai.config import Settings
from mordecai.policy import PolicyEngine
from mordecai.providers import ProviderRouter
from mordecai.proxy import SafeHttpClient
from mordecai.store import StateStore


class RecordingProxy(SafeHttpClient):
    def __init__(self, settings, policy, store):
        super().__init__(settings, policy, store)
        self.calls = []

    async def post_json(self, url, payload, headers=None):
        self.calls.append({"url": url, "payload": payload, "headers": headers or {}})
        return {"choices": [{"message": {"content": "proxied reply"}}]}


def test_provider_router_uses_proxy_for_openai_calls(tmp_path):
    settings = Settings(
        workspace_dir=tmp_path,
        state_dir=tmp_path / ".mordecai",
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="secret",
        openai_model="gpt-test",
    )
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = RecordingProxy(settings, policy, store)
    router = ProviderRouter(settings, proxy)

    reply = asyncio.run(router.generate("system", "hello", "context"))

    assert reply.provider == "openai-compatible"
    assert reply.content == "proxied reply"
    assert proxy.calls
    assert proxy.calls[0]["url"] == "https://api.openai.com/v1/chat/completions"