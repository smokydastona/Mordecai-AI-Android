from __future__ import annotations

import re
from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlparse
from uuid import uuid4

from mordecai.config import Settings
from mordecai.models import ImprovementFileChange, PolicyAuditRecord, PolicyReport

if TYPE_CHECKING:
    from mordecai.store import StateStore


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class PolicyEngine:
    SAFE_DOWNLOAD_QUERY_HOSTS = frozenset({
        "huggingface.co",
        "hf.co",
        "cas-bridge.xethub.hf.co",
        "cdn-lfs.hf.co",
        "cdn-lfs-us-1.hf.co",
        "cdn-lfs-eu-1.hf.co",
    })
    FORBIDDEN_ANDROID_ACTIONS = frozenset({"tap", "swipe", "type"})
    FORBIDDEN_PURCHASE_PATH_PATTERNS = [
        r"/(checkout|cart|payment|billing|invoice|subscribe|subscription|order)(/|$)",
        r"/(buy|purchase|donate|tip)(/|$)",
    ]
    SENSITIVE_QUERY_KEY_PATTERNS = [
        r"(^|_)(email|phone|address|ssn|social_security|card|card_number|credit_card|cvv|cvc|expiry|billing|shipping|dob|birthdate)(_|$)",
    ]
    SAFE_DOWNLOAD_QUERY_KEY_PATTERNS = [
        r"^download$",
        r"^expires$",
        r"^policy$",
        r"^signature$",
        r"^key-pair-id$",
        r"^x-amz-[a-z0-9-]+$",
        r"^x-xet-[a-z0-9-]+$",
    ]
    SENSITIVE_FIELD_PATTERNS = [
        r'"?(email|phone|address|ssn|social_security|card|card_number|credit_card|cvv|cvc|expiry|billing_address|shipping_address|full_name|first_name|last_name|dob|birthdate)"?\s*[:=]',
    ]
    SENSITIVE_VALUE_PATTERNS = [
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
        r"\b(?:\+?\d[\d\s().-]{7,}\d)\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b(?:\d[ -]*?){13,19}\b",
    ]
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
        self.store: StateStore | None = None
        self.protected_paths = frozenset({
            "src/mordecai/agent.py",
            "src/mordecai/android_control.py",
            "src/mordecai/config.py",
            "src/mordecai/dashboard.py",
            "src/mordecai/git_tools.py",
            "src/mordecai/local_models.py",
            "src/mordecai/main.py",
            "src/mordecai/models.py",
            "src/mordecai/policy.py",
            "src/mordecai/providers.py",
            "src/mordecai/proxy.py",
            "src/mordecai/self_improvement.py",
            "src/mordecai/avatar.py",
            "src/mordecai/store.py",
            "src/mordecai/voice.py",
            "src/mordecai/watchdog.py",
            "prompts/system_prompt.txt",
        })
        self.protected_prefixes = (
            "assets/avatar/",
            "mordecai_core/",
            "providers/",
        )

    def attach_store(self, store: StateStore) -> None:
        self.store = store

    def validate_url(self, url: str, *, audit: bool = True) -> PolicyDecision:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            decision = PolicyDecision(False, "Only http and https URLs are allowed")
            return self._record_decision("url", url, decision) if audit else decision
        if parsed.hostname not in self.settings.allowed_domains:
            decision = PolicyDecision(False, f"Domain '{parsed.hostname}' is not on the allowlist")
            return self._record_decision("url", url, decision) if audit else decision
        decision = PolicyDecision(True, "allowed")
        return self._record_decision("url", url, decision) if audit else decision

    def validate_outbound_request(self, method: str, url: str, payload: object | None = None) -> PolicyDecision:
        decision = self.validate_url(url, audit=False)
        if not decision.allowed:
            return self._record_decision("outbound-request", f"{method.upper()} {url}", decision)

        parsed = urlparse(url)
        normalized_path = parsed.path.lower()
        for pattern in self.FORBIDDEN_PURCHASE_PATH_PATTERNS:
            if re.search(pattern, normalized_path, flags=re.IGNORECASE):
                return self._record_decision(
                    "outbound-request",
                    f"{method.upper()} {url}",
                    PolicyDecision(False, "Outbound commerce or checkout endpoints are blocked by policy"),
                )

        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if any(re.search(pattern, key, flags=re.IGNORECASE) for pattern in self.SENSITIVE_QUERY_KEY_PATTERNS):
                return self._record_decision(
                    "outbound-request",
                    f"{method.upper()} {url}",
                    PolicyDecision(False, "Outbound personal data fields are blocked by policy"),
                )
            if self._is_safe_download_query_parameter(parsed.hostname, key):
                continue
            if self._contains_sensitive_value(value):
                return self._record_decision(
                    "outbound-request",
                    f"{method.upper()} {url}",
                    PolicyDecision(False, "Outbound personal data values are blocked by policy"),
                )

        if method.upper() not in {"GET", "HEAD"}:
            if self._contains_sensitive_payload(payload):
                return self._record_decision(
                    "outbound-request",
                    f"{method.upper()} {url}",
                    PolicyDecision(False, "Outbound personal data payloads are blocked by policy"),
                )
            if self._contains_purchase_payload(payload):
                return self._record_decision(
                    "outbound-request",
                    f"{method.upper()} {url}",
                    PolicyDecision(False, "Outbound purchase or payment payloads are blocked by policy"),
                )

        return self._record_decision("outbound-request", f"{method.upper()} {url}", PolicyDecision(True, "allowed"))

    def validate_android_action(self, action: str, arguments: list[str]) -> PolicyDecision:
        if action in self.FORBIDDEN_ANDROID_ACTIONS:
            return self._record_decision(
                "android-action",
                action,
                PolicyDecision(
                    False,
                    "Direct screen input actions are blocked to prevent purchases and personal-data entry",
                ),
            )
        if action == "open_app" and arguments:
            package = arguments[0].strip().lower()
            if any(token in package for token in ("vending", "play", "store", "shop", "pay", "wallet", "amazon")):
                return self._record_decision(
                    "android-action",
                    action,
                    PolicyDecision(False, "Commerce-oriented app launches are blocked by policy"),
                    {"package": package},
                )
        return self._record_decision("android-action", action, PolicyDecision(True, "allowed"), {"arguments": arguments})

    def validate_command(self, command: str) -> PolicyDecision:
        for pattern in self.FORBIDDEN_COMMAND_PATTERNS:
            if re.search(pattern, command, flags=re.IGNORECASE):
                return self._record_decision(
                    "command",
                    command,
                    PolicyDecision(False, f"Command blocked by policy pattern: {pattern}"),
                )
        return self._record_decision("command", command, PolicyDecision(True, "allowed"))

    def validate_file_changes(self, changes: list[ImprovementFileChange]) -> PolicyDecision:
        touched = {self._normalize_path(change.path) for change in changes}
        blocked = sorted(
            path for path in touched if path in self.protected_paths or any(path.startswith(prefix) for prefix in self.protected_prefixes)
        )
        if blocked:
            return self._record_decision(
                "file-change",
                ", ".join(sorted(touched)),
                PolicyDecision(False, f"Protected paths cannot be changed: {', '.join(blocked)}"),
            )
        return self._record_decision("file-change", ", ".join(sorted(touched)), PolicyDecision(True, "allowed"))

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
            return self._record_decision(
                "diff-content",
                ", ".join(self._normalize_path(change.path) for change in changes),
                PolicyDecision(False, f"Diff filters blocked changes: {', '.join(blocked)}"),
            )
        return self._record_decision(
            "diff-content",
            ", ".join(self._normalize_path(change.path) for change in changes),
            PolicyDecision(True, "allowed"),
        )

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
            "commerce-transactions",
            "personal-data-exfiltration",
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

    def _contains_sensitive_payload(self, payload: object | None) -> bool:
        text = self._stringify_payload(payload)
        if not text:
            return False
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in self.SENSITIVE_FIELD_PATTERNS):
            return True
        return self._contains_sensitive_value(text)

    def _contains_purchase_payload(self, payload: object | None) -> bool:
        text = self._stringify_payload(payload)
        if not text:
            return False
        purchase_patterns = [
            r'"?(card|card_number|credit_card|cvv|cvc|expiry|billing_address|shipping_address|payment_method|checkout_token|purchase|order_total|amount)"?\s*[:=]',
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in purchase_patterns)

    def _contains_sensitive_value(self, value: str) -> bool:
        return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in self.SENSITIVE_VALUE_PATTERNS)

    def _is_safe_download_query_parameter(self, hostname: str | None, key: str) -> bool:
        if hostname not in self.SAFE_DOWNLOAD_QUERY_HOSTS:
            return False
        return any(re.search(pattern, key, flags=re.IGNORECASE) for pattern in self.SAFE_DOWNLOAD_QUERY_KEY_PATTERNS)

    @staticmethod
    def _stringify_payload(payload: object | None) -> str:
        if payload is None:
            return ""
        if isinstance(payload, str):
            return payload
        return repr(payload)

    def _record_decision(
        self,
        surface: str,
        target: str,
        decision: PolicyDecision,
        metadata: dict[str, object] | None = None,
    ) -> PolicyDecision:
        if self.store is not None:
            self.store.append_policy_audit(
                PolicyAuditRecord(
                    audit_id=uuid4().hex[:12],
                    surface=surface,
                    target=target,
                    allowed=decision.allowed,
                    reason=decision.reason,
                    metadata=metadata or {},
                    created_at=datetime.now(UTC),
                )
            )
        return decision