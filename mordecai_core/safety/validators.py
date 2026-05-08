from __future__ import annotations

from mordecai.config import get_settings
from mordecai.models import ImprovementFileChange, PolicyReport
from mordecai.policy import PolicyDecision, PolicyEngine


class SafetyValidators:
    def __init__(self, policy: PolicyEngine | None = None) -> None:
        self.policy = policy or PolicyEngine(get_settings())

    def validate_url(self, url: str) -> PolicyDecision:
        return self.policy.validate_url(url)

    def validate_command(self, command: str) -> PolicyDecision:
        return self.policy.validate_command(command)

    def validate_file_change(self, path: str, content: str) -> PolicyDecision:
        return self.policy.validate_file_changes([ImprovementFileChange(path=path, content=content)])

    def report(self) -> PolicyReport:
        return self.policy.report()