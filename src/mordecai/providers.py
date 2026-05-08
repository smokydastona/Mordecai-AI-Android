from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mordecai.config import Settings
from mordecai_core.events import EventBus
from mordecai_core.provider_contracts import OpenAICompatibleProvider, ProviderCatalog, ProviderRequest, ProviderRequirements, RuleBasedProvider
from mordecai.proxy import SafeHttpClient


@dataclass
class ProviderReply:
    provider: str
    content: str


class ProviderRouter:
    def __init__(self, settings: Settings, proxy: SafeHttpClient, event_bus: EventBus | None = None) -> None:
        self.settings = settings
        self.proxy = proxy
        self.event_bus = event_bus
        self.catalog = ProviderCatalog(
            [
                RuleBasedProvider(),
                OpenAICompatibleProvider(settings, proxy),
            ]
        )
        self._recent_decisions: list[dict[str, Any]] = []

    async def generate(self, system_prompt: str, message: str, context: str) -> ProviderReply:
        request = ProviderRequest(system_prompt=system_prompt, message=message, context=context)
        requirements = ProviderRequirements(
            requires_tool_calling=False,
            min_context_window=min(max(len(system_prompt) + len(message) + len(context), 0), 128000),
        )
        preferred_provider = self._preferred_provider_name()
        try:
            provider = self.catalog.choose(requirements, preferred_name=preferred_provider)
        except KeyError:
            provider = self.catalog.get("rule-based")
            self._record_decision(provider.name, "fallback", requirements)
        else:
            self._record_decision(provider.name, "selected", requirements)
        result = await provider.chat(request)
        return ProviderReply(provider=result.provider, content=result.content)

    def attach_event_bus(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def capabilities(self) -> dict[str, dict[str, object]]:
        return self.catalog.capabilities_matrix()

    def recent_decisions(self) -> list[dict[str, Any]]:
        return list(self._recent_decisions[-20:])

    def _preferred_provider_name(self) -> str:
        if self.settings.openai_api_key and self.settings.openai_base_url and self.settings.openai_model:
            return "openai-compatible"
        return "rule-based"

    def _record_decision(self, provider_name: str, outcome: str, requirements: ProviderRequirements) -> None:
        decision = {
            "provider": provider_name,
            "outcome": outcome,
            "requirements": {
                "requires_streaming": requirements.requires_streaming,
                "requires_vision": requirements.requires_vision,
                "requires_tool_calling": requirements.requires_tool_calling,
                "min_context_window": requirements.min_context_window,
                "prefer_local": requirements.prefer_local,
            },
        }
        self._recent_decisions.append(decision)
        self._recent_decisions = self._recent_decisions[-50:]
        if self.event_bus is not None:
            self.event_bus.publish(
                f"provider.{outcome}",
                {
                    "provider": provider_name,
                    "requirements": decision["requirements"],
                },
            )