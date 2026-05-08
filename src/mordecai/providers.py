from __future__ import annotations

from dataclasses import dataclass

from mordecai.config import Settings
from mordecai_core.provider_contracts import OpenAICompatibleProvider, ProviderCatalog, ProviderRequest, RuleBasedProvider
from mordecai.proxy import SafeHttpClient


@dataclass
class ProviderReply:
    provider: str
    content: str


class ProviderRouter:
    def __init__(self, settings: Settings, proxy: SafeHttpClient) -> None:
        self.settings = settings
        self.proxy = proxy
        self.catalog = ProviderCatalog(
            [
                RuleBasedProvider(),
                OpenAICompatibleProvider(settings, proxy),
            ]
        )

    async def generate(self, system_prompt: str, message: str, context: str) -> ProviderReply:
        request = ProviderRequest(system_prompt=system_prompt, message=message, context=context)
        if self.settings.openai_api_key and self.settings.openai_base_url and self.settings.openai_model:
            result = await self.catalog.get("openai-compatible").chat(request)
            return ProviderReply(provider=result.provider, content=result.content)
        result = await self.catalog.get("rule-based").chat(request)
        return ProviderReply(provider=result.provider, content=result.content)