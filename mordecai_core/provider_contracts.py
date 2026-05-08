from __future__ import annotations

from dataclasses import asdict, dataclass
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


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    streaming: bool
    vision: bool
    tool_calling: bool
    max_context: int
    local: bool


@dataclass(frozen=True, slots=True)
class ProviderRequirements:
    requires_streaming: bool = False
    requires_vision: bool = False
    requires_tool_calling: bool = False
    min_context_window: int = 0
    prefer_local: bool = False


class AIProvider(Protocol):
    name: str
    capabilities: ProviderCapabilities

    async def chat(self, request: ProviderRequest) -> ProviderResult:
        ...


class OpenAICompatibleProvider:
    name = "openai-compatible"
    capabilities = ProviderCapabilities(
        streaming=True,
        vision=False,
        tool_calling=True,
        max_context=128000,
        local=False,
    )

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
    capabilities = ProviderCapabilities(
        streaming=False,
        vision=False,
        tool_calling=False,
        max_context=4096,
        local=True,
    )

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

    def capabilities_matrix(self) -> dict[str, dict[str, object]]:
        return {name: asdict(provider.capabilities) for name, provider in sorted(self._providers.items())}

    def choose(self, requirements: ProviderRequirements, *, preferred_name: str | None = None) -> AIProvider:
        candidates = list(self._providers.values())
        if preferred_name and preferred_name in self._providers:
            preferred = self._providers[preferred_name]
            if self._supports(preferred.capabilities, requirements):
                return preferred
        ranked = sorted(candidates, key=lambda provider: self._rank(provider.capabilities, requirements), reverse=True)
        for provider in ranked:
            if self._supports(provider.capabilities, requirements):
                return provider
        raise KeyError("No provider satisfies the requested capability profile")

    def _supports(self, capabilities: ProviderCapabilities, requirements: ProviderRequirements) -> bool:
        if requirements.requires_streaming and not capabilities.streaming:
            return False
        if requirements.requires_vision and not capabilities.vision:
            return False
        if requirements.requires_tool_calling and not capabilities.tool_calling:
            return False
        if capabilities.max_context < requirements.min_context_window:
            return False
        if requirements.prefer_local and not capabilities.local:
            return False
        return True

    def _rank(self, capabilities: ProviderCapabilities, requirements: ProviderRequirements) -> tuple[int, int, int]:
        return (
            int(capabilities.local == requirements.prefer_local),
            int(capabilities.tool_calling),
            capabilities.max_context,
        )