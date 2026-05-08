from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from mordecai.models import ConversationEntry, ImprovementBackupRecord, ImprovementCandidate, ProxyRequestRecord, RuntimeEvent


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
        for path, default in (
            (self._conversation_path, []),
            (self._proxy_log_path, []),
            (self._candidates_path, []),
            (self._events_path, []),
            (self._backups_path, []),
        ):
            if not path.exists():
                path.write_text(json.dumps(default, indent=2), encoding="utf-8")

    def _load(self, path: Path) -> list[dict[str, Any]]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, value: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(value[-self.max_log_entries :], indent=2), encoding="utf-8")

    def append_conversation(self, entry: ConversationEntry) -> None:
        with self._lock:
            payload = self._load(self._conversation_path)
            payload.append(entry.model_dump(mode="json"))
            self._save(self._conversation_path, payload)

    def read_conversation(self) -> list[ConversationEntry]:
        with self._lock:
            return [ConversationEntry.model_validate(item) for item in self._load(self._conversation_path)]

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