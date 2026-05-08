from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from mordecai.config import Settings
from mordecai.models import ImprovementFileChange, PolicyReport


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    FORBIDDEN_COMMAND_PATTERNS = [
        r"\b(reboot|shutdown|poweroff|halt)\b",
        r"\bmkfs\b",
        r"\bdd if=",
        r"\bsvc\s+(wifi|data|bluetooth)\b",
        r"\bsettings\s+put\s+global\s+airplane_mode_on\b",
        r"\biptables\b",
        r"\brm\s+-rf\s+/(?!tmp)",
    ]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.protected_paths = {
            "src/mordecai/policy.py",
            "src/mordecai/proxy.py",
            "src/mordecai/self_improvement.py",
            "src/mordecai/config.py",
            "prompts/system_prompt.txt",
        }

    def validate_url(self, url: str) -> PolicyDecision:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return PolicyDecision(False, "Only http and https URLs are allowed")
        if parsed.hostname not in self.settings.allowed_domains:
            return PolicyDecision(False, f"Domain '{parsed.hostname}' is not on the allowlist")
        return PolicyDecision(True, "allowed")

    def validate_command(self, command: str) -> PolicyDecision:
        for pattern in self.FORBIDDEN_COMMAND_PATTERNS:
            if re.search(pattern, command, flags=re.IGNORECASE):
                return PolicyDecision(False, f"Command blocked by policy pattern: {pattern}")
        return PolicyDecision(True, "allowed")

    def validate_file_changes(self, changes: list[ImprovementFileChange]) -> PolicyDecision:
        touched = {self._normalize_path(change.path) for change in changes}
        blocked = sorted(touched & self.protected_paths)
        if blocked:
            return PolicyDecision(False, f"Protected paths cannot be changed: {', '.join(blocked)}")
        return PolicyDecision(True, "allowed")

    def report(self) -> PolicyReport:
        return PolicyReport(
            protected_paths=sorted(self.protected_paths),
            forbidden_command_patterns=self.FORBIDDEN_COMMAND_PATTERNS,
            allowed_domains=self.settings.allowed_domains,
            wake_words=self.settings.wake_words,
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        return Path(path).as_posix().lstrip("./")