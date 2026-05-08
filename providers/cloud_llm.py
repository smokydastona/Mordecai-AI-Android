from __future__ import annotations

from mordecai.providers import ProviderRouter
from mordecai_core.provider_contracts import ProviderRequest
from mordecai_core.tool_registry import ContextOverflow, ProviderUnavailable, ToolManifest


class CloudLLMToolProvider:
    def __init__(self, router: ProviderRouter) -> None:
        self.router = router

    def tools(self) -> list[tuple[ToolManifest, object]]:
        return [
            (
                ToolManifest(
                    tool="cloud-llm.chat",
                    permissions=("network", "llm"),
                    description="Run a cloud language-model completion through the safe proxy.",
                    input_schema={"message": "string", "system_prompt": "string", "context": "string"},
                    output_schema={"provider": "string", "content": "string"},
                    risk_level="moderate",
                    confirmation_policy="on-request",
                    safe_mode_behavior="allow",
                    sandbox_profile="networked",
                ),
                self.chat,
            )
        ]

    async def chat(self, message: str, system_prompt: str = "", context: str = "") -> dict[str, str]:
        if not (self.router.settings.openai_api_key and self.router.settings.openai_base_url and self.router.settings.openai_model):
            raise ProviderUnavailable("Cloud provider configuration is incomplete.", details={"provider": "openai-compatible"})
        provider = self.router.catalog.get("openai-compatible")
        if provider.capabilities.max_context < len(message) + len(system_prompt) + len(context):
            raise ContextOverflow("Requested prompt exceeds the configured cloud provider context window.")
        result = await provider.chat(ProviderRequest(system_prompt=system_prompt, message=message, context=context))
        return {"provider": result.provider, "content": result.content}