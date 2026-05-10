from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from mordecai.models import AgentPlanRecord, AndroidPerceptionSnapshot, ConversationEntry, GoalRecord, ImprovementBackupRecord, ImprovementCandidate, MemoryRecord, MemorySearchResult, ProxyRequestRecord, RoutineRecord, RuntimeEvent, RuntimeFailure, ToolExecutionRecord, VoiceSessionRecord


class StateStoreError(RuntimeError):
    pass


class StateStore:
    def __init__(self, state_dir: Path, max_log_entries: int) -> None:
        self.state_dir = state_dir
        self.max_log_entries = max_log_entries
        self._lock = Lock()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._conversation_path = state_dir / "conversation.json"
        self._proxy_log_path = state_dir / "proxy_log.json"
        self._candidates_path = state_dir / "candidates.json"
        self._events_path = state_dir / "events.json"
        self._backups_path = state_dir / "backups.json"
        self._tool_executions_path = state_dir / "tool_executions.json"
        self._goals_path = state_dir / "goals.json"
        self._routines_path = state_dir / "routines.json"
        self._memory_path = state_dir / "memory.json"
        self._perception_path = state_dir / "perception.json"
        self._voice_sessions_path = state_dir / "voice_sessions.json"
        self._plans_path = state_dir / "plans.json"
        for path, default in (
            (self._conversation_path, []),
            (self._proxy_log_path, []),
            (self._candidates_path, []),
            (self._events_path, []),
            (self._backups_path, []),
            (self._tool_executions_path, []),
            (self._goals_path, []),
            (self._routines_path, []),
            (self._memory_path, []),
            (self._perception_path, []),
            (self._voice_sessions_path, []),
            (self._plans_path, []),
        ):
            if not path.exists():
                path.write_text(json.dumps(default, indent=2), encoding="utf-8")

    def _load(self, path: Path) -> list[dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StateStoreError(f"State file '{path.name}' is corrupt: {exc}") from exc
        except FileNotFoundError as exc:
            raise StateStoreError(f"State file '{path.name}' is missing.") from exc

    def _save(self, path: Path, value: list[dict[str, Any]]) -> None:
        try:
            truncated = value[-self.max_log_entries :]
            content = json.dumps(truncated, indent=2)
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(path)
        except Exception as exc:
            raise StateStoreError(f"Failed to save state file '{path.name}': {exc}") from exc

    def append_conversation(self, entry: ConversationEntry) -> None:
        with self._lock:
            payload = self._load(self._conversation_path)
            payload.append(entry.model_dump(mode="json"))
            self._save(self._conversation_path, payload)

    def read_conversation(self) -> list[ConversationEntry]:
        with self._lock:
            return [ConversationEntry.model_validate(item) for item in self._load(self._conversation_path)]

    def save_memory(self, record: MemoryRecord) -> None:
        with self._lock:
            payload = self._load(self._memory_path)
            payload = [item for item in payload if item["memory_id"] != record.memory_id]
            payload.append(record.model_dump(mode="json"))
            self._save(self._memory_path, payload)

    def read_memories(self) -> list[MemoryRecord]:
        with self._lock:
            records = [MemoryRecord.model_validate(item) for item in self._load(self._memory_path)]
        return sorted(records, key=lambda record: record.updated_at)

    def save_perception_snapshot(self, record: AndroidPerceptionSnapshot) -> None:
        with self._lock:
            payload = self._load(self._perception_path)
            payload.append(record.model_dump(mode="json"))
            self._save(self._perception_path, payload)

    def read_perception_history(self) -> list[AndroidPerceptionSnapshot]:
        with self._lock:
            return [AndroidPerceptionSnapshot.model_validate(item) for item in self._load(self._perception_path)]

    def latest_perception(self) -> AndroidPerceptionSnapshot | None:
        history = self.read_perception_history()
        if not history:
            return None
        return history[-1]

    def save_voice_session(self, record: VoiceSessionRecord) -> None:
        with self._lock:
            payload = self._load(self._voice_sessions_path)
            payload = [item for item in payload if item["session_id"] != record.session_id]
            payload.append(record.model_dump(mode="json"))
            self._save(self._voice_sessions_path, payload)

    def read_voice_sessions(self) -> list[VoiceSessionRecord]:
        with self._lock:
            records = [VoiceSessionRecord.model_validate(item) for item in self._load(self._voice_sessions_path)]
        return sorted(records, key=lambda record: record.updated_at)

    def save_plan(self, record: AgentPlanRecord) -> None:
        with self._lock:
            payload = self._load(self._plans_path)
            payload = [item for item in payload if item["plan_id"] != record.plan_id]
            payload.append(record.model_dump(mode="json"))
            self._save(self._plans_path, payload)

    def read_plans(self) -> list[AgentPlanRecord]:
        with self._lock:
            records = [AgentPlanRecord.model_validate(item) for item in self._load(self._plans_path)]
        return sorted(records, key=lambda record: record.created_at)

    def get_plan(self, plan_id: str) -> AgentPlanRecord | None:
        for record in self.read_plans():
            if record.plan_id == plan_id:
                return record
        return None

    def get_voice_session(self, session_id: str) -> VoiceSessionRecord | None:
        for record in self.read_voice_sessions():
            if record.session_id == session_id:
                return record
        return None

    def search_memories(
        self,
        query: str,
        *,
        limit: int = 5,
        categories: list[str] | None = None,
        pinned_only: bool = False,
    ) -> list[MemorySearchResult]:
        tokens = self._tokenize(query)
        if not tokens:
            return []
        allowed_categories = {item for item in (categories or []) if item}
        ranked: list[MemorySearchResult] = []
        for record in self.read_memories():
            if pinned_only and not record.pinned:
                continue
            if allowed_categories and record.category not in allowed_categories:
                continue
            score = self._score_memory(record, tokens)
            if score <= 0:
                continue
            ranked.append(MemorySearchResult(record=record, score=round(score, 4)))
        ranked.sort(key=lambda item: (item.score, item.record.updated_at), reverse=True)
        return ranked[:limit]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1}

    def _score_memory(self, record: MemoryRecord, tokens: set[str]) -> float:
        haystack = self._tokenize(" ".join([record.content, *record.tags, record.category, record.source]))
        overlap = len(tokens & haystack)
        if overlap == 0:
            return 0.0
        recency_hours = max((datetime.now(UTC) - record.updated_at).total_seconds() / 3600, 0.0)
        recency_bonus = 1.0 / (1.0 + recency_hours / 24.0)
        pin_bonus = 0.75 if record.pinned else 0.0
        importance_bonus = record.importance * 0.35
        coverage_bonus = overlap / max(len(tokens), 1)
        return (overlap * 1.5) + coverage_bonus + recency_bonus + pin_bonus + importance_bonus

    def append_proxy_record(self, entry: ProxyRequestRecord) -> None:
        with self._lock:
            payload = self._load(self._proxy_log_path)
            payload.append(entry.model_dump(mode="json"))
            self._save(self._proxy_log_path, payload)

    def read_proxy_records(self) -> list[ProxyRequestRecord]:
        with self._lock:
            return [ProxyRequestRecord.model_validate(item) for item in self._load(self._proxy_log_path)]

    def save_candidate(self, candidate: ImprovementCandidate) -> None:
        with self._lock:
            payload = self._load(self._candidates_path)
            payload = [item for item in payload if item["candidate_id"] != candidate.candidate_id]
            payload.append(candidate.model_dump(mode="json"))
            self._save(self._candidates_path, payload)

    def read_candidates(self) -> list[ImprovementCandidate]:
        with self._lock:
            return [ImprovementCandidate.model_validate(item) for item in self._load(self._candidates_path)]

    def append_event(self, event: RuntimeEvent) -> None:
        with self._lock:
            payload = self._load(self._events_path)
            payload.append(event.model_dump(mode="json"))
            self._save(self._events_path, payload)

    def read_events(self) -> list[RuntimeEvent]:
        with self._lock:
            return [RuntimeEvent.model_validate(item) for item in self._load(self._events_path)]

    def save_backup_record(self, record: ImprovementBackupRecord) -> None:
        with self._lock:
            payload = self._load(self._backups_path)
            payload = [item for item in payload if item["candidate_id"] != record.candidate_id]
            payload.append(record.model_dump(mode="json"))
            self._save(self._backups_path, payload)

    def read_backup_records(self) -> list[ImprovementBackupRecord]:
        with self._lock:
            return [ImprovementBackupRecord.model_validate(item) for item in self._load(self._backups_path)]

    def append_tool_execution(
        self,
        *,
        execution_id: str,
        tool_name: str,
        status: str,
        attempts: int,
        duration_ms: float,
        output: Any = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        record = ToolExecutionRecord(
            execution_id=execution_id,
            tool_name=tool_name,
            status=status,
            attempts=attempts,
            duration_ms=duration_ms,
            output=output,
            error=RuntimeFailure.model_validate(error) if error else None,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            payload = self._load(self._tool_executions_path)
            payload.append(record.model_dump(mode="json"))
            self._save(self._tool_executions_path, payload)

    def read_tool_executions(self) -> list[ToolExecutionRecord]:
        with self._lock:
            return [ToolExecutionRecord.model_validate(item) for item in self._load(self._tool_executions_path)]

    def save_goal(self, record: GoalRecord) -> None:
        with self._lock:
            payload = self._load(self._goals_path)
            payload = [item for item in payload if item["goal_id"] != record.goal_id]
            payload.append(record.model_dump(mode="json"))
            self._save(self._goals_path, payload)

    def read_goals(self) -> list[GoalRecord]:
        with self._lock:
            return [GoalRecord.model_validate(item) for item in self._load(self._goals_path)]

    def save_routine(self, record: RoutineRecord) -> None:
        with self._lock:
            payload = self._load(self._routines_path)
            payload = [item for item in payload if item["routine_id"] != record.routine_id]
            payload.append(record.model_dump(mode="json"))
            self._save(self._routines_path, payload)

    def read_routines(self) -> list[RoutineRecord]:
        with self._lock:
            return [RoutineRecord.model_validate(item) for item in self._load(self._routines_path)]