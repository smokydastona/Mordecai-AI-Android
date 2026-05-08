from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Callable


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    name: str
    payload: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


EventHandler = Callable[[EventEnvelope], None]


class EventBus:
    def __init__(self, max_history: int = 250) -> None:
        self.max_history = max_history
        self._history: deque[EventEnvelope] = deque(maxlen=max_history)
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers.setdefault(event_name, []).append(handler)

    def publish(self, event_name: str, payload: dict[str, object] | None = None) -> EventEnvelope:
        envelope = EventEnvelope(name=event_name, payload=payload or {})
        self._history.append(envelope)
        for handler in self._subscribers.get(event_name, []):
            handler(envelope)
        for handler in self._subscribers.get("*", []):
            handler(envelope)
        return envelope

    def recent(self) -> list[EventEnvelope]:
        return list(self._history)