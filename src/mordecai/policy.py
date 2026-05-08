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
    FORBIDDEN_DIFF_PATTERNS = [
        r"@reboot",
        r"systemctl\s+enable",
        r"crontab",
        r"schtasks",
        r"RECEIVE_BOOT_COMPLETED",
        r"BOOT_COMPLETED",
        r"TermuxBoot",
        r"Startup",
    ]
    FORBIDDEN_DIFF_PATH_PREFIXES = (
        ".termux/boot/",
        "init.d/",
        "systemd/",
        "cron.",
    )
    FORBIDDEN_DIFF_PATHS = {
        ".bashrc",
        ".bash_profile",
        ".profile",
        ".zshrc",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.protected_paths = {
            "src/mordecai/policy.py",
            "src/mordecai/proxy.py",
            "src/mordecai/self_improvement.py",
            "src/mordecai/config.py",
            "src/mordecai/avatar.py",
            "prompts/system_prompt.txt",
        }
        self.protected_prefixes = (
            "assets/avatar/",
        )

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
        blocked = sorted(
            path for path in touched if path in self.protected_paths or any(path.startswith(prefix) for prefix in self.protected_prefixes)
        )
        if blocked:
            return PolicyDecision(False, f"Protected paths cannot be changed: {', '.join(blocked)}")
        return PolicyDecision(True, "allowed")

    def validate_change_content(self, changes: list[ImprovementFileChange]) -> PolicyDecision:
        blocked: list[str] = []
        for change in changes:
            normalized_path = self._normalize_path(change.path)
            if normalized_path in self.FORBIDDEN_DIFF_PATHS or any(normalized_path.startswith(prefix) for prefix in self.FORBIDDEN_DIFF_PATH_PREFIXES):
                blocked.append(f"{normalized_path} (hidden persistence path)")
                continue
            for pattern in self.FORBIDDEN_DIFF_PATTERNS:
                if re.search(pattern, change.content, flags=re.IGNORECASE):
                    blocked.append(f"{normalized_path} (blocked diff pattern: {pattern})")
                    break
        if blocked:
            return PolicyDecision(False, f"Diff filters blocked changes: {', '.join(blocked)}")
        return PolicyDecision(True, "allowed")

    def report(self) -> PolicyReport:
        allowed_features = [
            "localhost-fastapi",
            "dashboard",
            "proxy-web-search",
            "local-git-backup",
        ]
        blocked_features = [
            "android-automation",
            "daemon-mode",
            "root-only-behaviors",
        ]
        allowed_features.append("permanent-avatar")
        if self.settings.allow_git_push:
            allowed_features.append("git-push")
        if self.settings.enable_android_control:
            allowed_features.append("android-automation")
            blocked_features.remove("android-automation")
        if self.settings.enable_daemon_mode:
            allowed_features.append("daemon-mode")
            blocked_features.remove("daemon-mode")
        return PolicyReport(
            mode=self.settings.mode,
            protected_paths=sorted(self.protected_paths),
            forbidden_command_patterns=self.FORBIDDEN_COMMAND_PATTERNS,
            allowed_domains=self.settings.allowed_domains,
            wake_words=self.settings.wake_words,
            allowed_features=allowed_features,
            blocked_features=blocked_features,
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        return Path(path).as_posix()