from __future__ import annotations

from pathlib import Path

from mordecai.config import Settings
from mordecai.git_tools import GitService
from mordecai.models import ChatResponse, ConversationEntry, StatusSnapshot
from mordecai.policy import PolicyEngine
from mordecai.providers import ProviderRouter
from mordecai.proxy import SafeHttpClient
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore
from mordecai.voice import VoiceProfile, build_voice_profile
from mordecai.watchdog import Watchdog


class MordecaiRuntime:
    def __init__(
        self,
        settings: Settings,
        store: StateStore,
        policy: PolicyEngine,
        proxy: SafeHttpClient,
        git_service: GitService,
        provider_router: ProviderRouter,
        improvement_manager: SelfImprovementManager,
        watchdog: Watchdog,
    ) -> None:
        self.settings = settings
        self.store = store
        self.policy = policy
        self.proxy = proxy
        self.git_service = git_service
        self.provider_router = provider_router
        self.improvement_manager = improvement_manager
        self.watchdog = watchdog
        self.voice_profile = build_voice_profile(settings)
        self.system_prompt = self._load_system_prompt()

    async def chat(self, message: str) -> ChatResponse:
        self.store.append_conversation(ConversationEntry(role="user", content=message))
        actions: list[str] = []
        lowered = message.lower().strip()
        context = self._build_context()

        if lowered.startswith("override:"):
            reply = "Override acknowledged. Safety and physical-harm constraints remain in force."
            provider_name = "policy-engine"
            actions.append("override-acknowledged")
        elif lowered.startswith("github search "):
            query = message[len("github search ") :].strip()
            results = await self.proxy.github_search_repositories(query, 5)
            reply = "\n".join(f"- {item['full_name']} ({item['stars']} stars): {item['url']}" for item in results) or "No repositories found."
            provider_name = "github-search"
            actions.append("github-search")
        elif lowered.startswith("fetch "):
            url = message[len("fetch ") :].strip()
            text = await self.proxy.fetch_text(url)
            reply = text[:2000]
            provider_name = "safe-proxy"
            actions.append("fetch-url")
        else:
            provider_reply = await self.provider_router.generate(self.system_prompt, message, context)
            reply = provider_reply.content
            provider_name = provider_reply.provider

        self.store.append_conversation(ConversationEntry(role="assistant", content=reply))
        return ChatResponse(
            reply=reply,
            provider=provider_name,
            actions=actions,
            memory_count=len(self.store.read_conversation()),
        )

    def status(self) -> StatusSnapshot:
        git_status = self.git_service.status()
        resources = self.watchdog.snapshot()
        return StatusSnapshot(
            app_name=self.settings.app_name,
            provider=self.settings.default_provider,
            environment=self.settings.environment,
            git_branch=git_status["branch"],
            git_dirty=bool(git_status["dirty"]),
            pending_candidates=len([candidate for candidate in self.improvement_manager.list_candidates() if not candidate.applied]),
            wake_words=self.voice_profile.wake_words,
            cpu_percent=resources.cpu_percent,
            memory_mb=resources.memory_mb,
            recent_requests=len(self.store.read_proxy_records()),
        )

    def memory(self) -> list[ConversationEntry]:
        return self.store.read_conversation()

    def events(self) -> list[dict[str, object]]:
        return [event.model_dump(mode="json") for event in self.store.read_events()]

    def voice(self) -> VoiceProfile:
        return self.voice_profile

    def _build_context(self) -> str:
        git_state = self.git_service.status()
        last_messages = self.store.read_conversation()[-6:]
        history = "\n".join(f"{entry.role}: {entry.content}" for entry in last_messages)
        return (
            f"User: {self.settings.user_name}\n"
            f"Branch: {git_state['branch']}\n"
            f"Dirty: {git_state['dirty']}\n"
            f"Wake words: {', '.join(self.voice_profile.wake_words)}\n"
            f"Recent conversation:\n{history}"
        )

    def _load_system_prompt(self) -> str:
        prompt_path = Path(self.settings.system_prompt_path)
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "You are Mordecai: formal, precise, loyal to the user, stable, reversible, and transparent."