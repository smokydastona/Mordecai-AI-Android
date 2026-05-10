from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from datetime import UTC, datetime
import re

from mordecai.config import Settings
from mordecai.avatar import DEFAULT_AVATAR_EMOTION, build_avatar_profile, classify_avatar_emotion
from mordecai.git_tools import GitService
from mordecai.models import AvatarProfile, ChatResponse, ConversationEntry, GoalRecord, GoalRequest, MemoryRecord, MemorySearchResult, MemoryWriteRequest, RoutineRecord, RoutineRequest, RuntimeEvent, StatusSnapshot
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
        self.avatar_emotion = DEFAULT_AVATAR_EMOTION
        self.system_prompt = self._load_system_prompt()

    async def chat(self, message: str) -> ChatResponse:
        self.store.append_conversation(ConversationEntry(role="user", content=message))
        self._remember_from_message(message)
        actions: list[str] = []
        lowered = message.lower().strip()
        context = self._build_context(message)

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
        self.avatar_emotion = classify_avatar_emotion(reply, actions)
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
            mode=self.settings.mode,
            provider=self.settings.default_provider,
            environment=self.settings.environment,
            git_branch=git_status["branch"],
            git_dirty=bool(git_status["dirty"]),
            pending_candidates=len([candidate for candidate in self.improvement_manager.list_candidates() if not candidate.applied]),
            wake_words=self.voice_profile.wake_words,
            cpu_percent=resources.cpu_percent,
            memory_mb=resources.memory_mb,
            recent_requests=len(self.store.read_proxy_records()),
            service_host=self.settings.service_host,
            service_port=self.settings.service_port,
            avatar_emotion=self.avatar_emotion,
            active_goals=len([goal for goal in self.store.read_goals() if goal.status == "active"]),
            active_routines=len([routine for routine in self.store.read_routines() if routine.enabled]),
        )

    def memory(self) -> list[ConversationEntry]:
        return self.store.read_conversation()

    def memory_records(self) -> list[MemoryRecord]:
        return self.store.read_memories()

    def remember(self, request: MemoryWriteRequest) -> MemoryRecord:
        now = datetime.now(UTC)
        record = MemoryRecord(
            memory_id=uuid4().hex[:12],
            category=request.category,
            content=request.content.strip(),
            tags=self._normalize_tags(request.tags),
            source=request.source,
            importance=request.importance,
            pinned=request.pinned,
            created_at=now,
            updated_at=now,
        )
        self.store.save_memory(record)
        self.store.append_event(RuntimeEvent(category="memory", detail=f"saved:{record.memory_id}:{record.category}"))
        return record

    def search_memory(
        self,
        query: str,
        *,
        limit: int = 5,
        categories: list[str] | None = None,
        pinned_only: bool = False,
    ) -> list[MemorySearchResult]:
        return self.store.search_memories(
            query,
            limit=limit,
            categories=categories,
            pinned_only=pinned_only,
        )

    def events(self) -> list[dict[str, object]]:
        return [event.model_dump(mode="json") for event in self.store.read_events()]

    def voice(self) -> VoiceProfile:
        return self.voice_profile

    def avatar(self) -> AvatarProfile:
        return build_avatar_profile(self.settings, current_emotion=self.avatar_emotion)

    def goals(self) -> list[GoalRecord]:
        return self.store.read_goals()

    def routines(self) -> list[RoutineRecord]:
        return self.store.read_routines()

    def create_goal(self, request: GoalRequest) -> GoalRecord:
        now = datetime.now(UTC)
        record = GoalRecord(
            goal_id=uuid4().hex[:12],
            title=request.title,
            description=request.description,
            priority=request.priority,
            created_at=now,
            updated_at=now,
        )
        self.store.save_goal(record)
        self.store.append_event(RuntimeEvent(category="goal", detail=f"created:{record.goal_id}"))
        return record

    def create_routine(self, request: RoutineRequest) -> RoutineRecord:
        now = datetime.now(UTC)
        record = RoutineRecord(
            routine_id=uuid4().hex[:12],
            title=request.title,
            description=request.description,
            trigger=request.trigger,
            enabled=request.enabled,
            created_at=now,
            updated_at=now,
        )
        self.store.save_routine(record)
        self.store.append_event(RuntimeEvent(category="routine", detail=f"created:{record.routine_id}"))
        return record

    def _build_context(self, focus_message: str) -> str:
        git_state = self.git_service.status()
        last_messages = self.store.read_conversation()[-6:]
        history = "\n".join(f"{entry.role}: {entry.content}" for entry in last_messages)
        retrieved_memories = self.search_memory(focus_message, limit=4)
        memory_lines = "\n".join(
            f"- [{item.record.category}] {item.record.content}"
            for item in retrieved_memories
        ) or "- none"
        return (
            f"User: {self.settings.user_name}\n"
            f"Branch: {git_state['branch']}\n"
            f"Dirty: {git_state['dirty']}\n"
            f"Wake words: {', '.join(self.voice_profile.wake_words)}\n"
            f"Relevant memory:\n{memory_lines}\n"
            f"Recent conversation:\n{history}"
        )

    def _remember_from_message(self, message: str) -> None:
        candidate = self._derive_memory_request(message)
        if candidate is None:
            return
        existing = self.search_memory(candidate.content, limit=1, categories=[candidate.category])
        if existing and existing[0].record.content.lower() == candidate.content.lower():
            return
        self.remember(candidate)

    def _derive_memory_request(self, message: str) -> MemoryWriteRequest | None:
        cleaned = " ".join(message.strip().split())
        if len(cleaned) < 12:
            return None
        lowered = cleaned.lower()
        if any(token in lowered for token in ("i prefer", "i usually", "please always", "don't ", "do not ")):
            return MemoryWriteRequest(
                category="preference",
                content=cleaned,
                tags=self._extract_tags(cleaned),
                source="conversation",
                importance=4,
            )
        if any(token in lowered for token in ("i am working on", "i'm working on", "debugging", "building", "fixing", "implementing")):
            return MemoryWriteRequest(
                category="project",
                content=cleaned,
                tags=self._extract_tags(cleaned),
                source="conversation",
                importance=3,
            )
        if any(token in lowered for token in ("remind me", "need to", "todo", "to do", "follow up")):
            return MemoryWriteRequest(
                category="task",
                content=cleaned,
                tags=self._extract_tags(cleaned),
                source="conversation",
                importance=3,
            )
        if cleaned.endswith((".", "!", "?")) and len(cleaned.split()) >= 8:
            return MemoryWriteRequest(
                category="episode",
                content=cleaned,
                tags=self._extract_tags(cleaned),
                source="conversation",
                importance=2,
            )
        return None

    def _extract_tags(self, text: str) -> list[str]:
        stop_words = {
            "about", "after", "always", "assistant", "because", "before", "build", "could", "debugging",
            "during", "follow", "have", "implementing", "need", "please", "project", "should", "that",
            "their", "them", "there", "this", "today", "want", "with", "working",
        }
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        tags: list[str] = []
        for token in tokens:
            if len(token) < 3 or token in stop_words:
                continue
            if token not in tags:
                tags.append(token)
            if len(tags) == 6:
                break
        return tags

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in tags:
            cleaned = tag.strip().lower().replace(" ", "-")
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    def _load_system_prompt(self) -> str:
        prompt_path = Path(self.settings.system_prompt_path)
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "You are Mordecai: formal, precise, loyal to the user, stable, reversible, and transparent."