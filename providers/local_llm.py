from __future__ import annotations

from mordecai_core.provider_contracts import ProviderCatalog, ProviderRequest, ProviderRequirements
from mordecai_core.tool_registry import ContextOverflow, ProviderUnavailable, ToolManifest


class LocalLLMToolProvider:
    def __init__(self, catalog: ProviderCatalog) -> None:
        self.catalog = catalog

    def tools(self) -> list[tuple[ToolManifest, object]]:
        return [
            (
                ToolManifest(
                    tool="local-llm.chat",
                    permissions=("llm",),
                    description="Run a local-first language-model completion.",
                    input_schema={"message": "string", "system_prompt": "string", "context": "string"},
                    output_schema={"provider": "string", "content": "string"},
                    risk_level="low",
                    confirmation_policy="never",
                    safe_mode_behavior="allow",
                    sandbox_profile="trusted",
                ),
                self.chat,
            )
        ]

    async def chat(self, message: str, system_prompt: str = "", context: str = "") -> dict[str, str]:
        provider = self.catalog.choose(
            ProviderRequirements(
                min_context_window=len(message) + len(system_prompt) + len(context),
                prefer_local=True,
            ),
            preferred_name="rule-based",
        )
        if provider.capabilities.max_context < len(message) + len(system_prompt) + len(context):
            raise ContextOverflow("Requested prompt exceeds the selected local provider context window.")
        result = await provider.chat(ProviderRequest(system_prompt=system_prompt, message=message, context=context))
        return {"provider": result.provider, "content": result.content}
