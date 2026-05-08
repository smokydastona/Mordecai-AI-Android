from __future__ import annotations

from dataclasses import dataclass

from mordecai.config import Settings
from mordecai.proxy import SafeHttpClient


@dataclass
class ProviderReply:
    provider: str
    content: str


class ProviderRouter:
    def __init__(self, settings: Settings, proxy: SafeHttpClient) -> None:
        self.settings = settings
        self.proxy = proxy

    async def generate(self, system_prompt: str, message: str, context: str) -> ProviderReply:
        if self.settings.openai_api_key and self.settings.openai_base_url and self.settings.openai_model:
            return await self._openai_compatible(system_prompt, message, context)
        return self._rule_based(message, context)

    async def _openai_compatible(self, system_prompt: str, message: str, context: str) -> ProviderReply:
        payload = {
            "model": self.settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"Context:\n{context}"},
                {"role": "user", "content": message},
            ],
        }
        response = await self.proxy.post_json(
            f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
        )
        content = response["choices"][0]["message"]["content"]
        return ProviderReply(provider="openai-compatible", content=content)

    def _rule_based(self, message: str, context: str) -> ProviderReply:
        lowered = message.lower()
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
                f"Relevant context: {context[:500]}"
            )
        return ProviderReply(provider="rule-based", content=content)