from __future__ import annotations

import re
from dataclasses import dataclass

from mordecai.config import get_settings


@dataclass(frozen=True, slots=True)
class WakeMatch:
    matched: bool
    wake_word: str | None
    command: str


class WakeWordDetector:
    def __init__(self, wake_words: list[str] | None = None) -> None:
        self.wake_words = wake_words or get_settings().wake_words
        escaped = "|".join(re.escape(word) for word in self.wake_words)
        self._pattern = re.compile(rf"^\s*({escaped})(?:(?:\b\s*)|(?:\s*[:,.-]\s*)|(?:\s+))(.*)$", re.IGNORECASE)

    def detect(self, text: str) -> WakeMatch:
        match = self._pattern.match(text.strip())
        if not match:
            return WakeMatch(False, None, text.strip())
        wake_word = next(word for word in self.wake_words if word.lower() == match.group(1).lower())
        command = match.group(2).lstrip(" :,-.\t").strip()
        return WakeMatch(True, wake_word, command)