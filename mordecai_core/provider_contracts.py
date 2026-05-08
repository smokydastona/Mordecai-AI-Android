from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mordecai.config import Settings
from mordecai.proxy import SafeHttpClient


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    system_prompt: str
    message: str
    context: str


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider: str
    content: str


class AIProvider(Protocol):
    name: str

    async def chat(self, request: ProviderRequest) -> ProviderResult:
        ...


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self, settings: Settings, proxy: SafeHttpClient) -> None:
        self.settings = settings
        self.proxy = proxy

    async def chat(self, request: ProviderRequest) -> ProviderResult:
        payload = {
            "model": self.settings.openai_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "system", "content": f"Context:\n{request.context}"},
                {"role": "user", "content": request.message},
            ],
        }
        response = await self.proxy.post_json(
            f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
        )
        return ProviderResult(provider=self.name, content=response["choices"][0]["message"]["content"])


class RuleBasedProvider:
    name = "rule-based"

    async def chat(self, request: ProviderRequest) -> ProviderResult:
        lowered = request.message.lower()
        if "status" in lowered:
            content = "I remain stable, policy-bound, and ready. Ask for dashboard status for full telemetry."
        elif "backup" in lowered:
            content = "A backup snapshot can be created through the git backup endpoint when you are ready to commit current state."
        elif "improve" in lowered:
            content = "I can stage improvements as sandbox candidates, run tests, and present diffs before any live promotion."
        else:
            content = (
                "I am Mordecai. I operate with a formal, policy-driven runtime, a restricted network surface, "
                "sandboxed self-improvement, and a reversible git-backed workflow. "
                f"Relevant context: {request.context[:500]}"
            )
        return ProviderResult(provider=self.name, content=content)


class ProviderCatalog:
    def __init__(self, providers: list[AIProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def names(self) -> list[str]:
        return sorted(self._providers)

    def get(self, name: str) -> AIProvider:
        return self._providers[name]