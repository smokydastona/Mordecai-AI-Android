from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, HttpUrl


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    provider: str
    actions: list[str] = Field(default_factory=list)
    memory_count: int


class ConversationEntry(BaseModel):
    role: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProxyRequestRecord(BaseModel):
    method: str
    url: str
    allowed: bool
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StatusSnapshot(BaseModel):
    app_name: str
    provider: str
    environment: str
    git_branch: str | None
    git_dirty: bool
    pending_candidates: int
    wake_words: list[str]
    cpu_percent: float
    memory_mb: float
    recent_requests: int


class GithubSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class WebSearchRequest(BaseModel):
    query: str = Field(min_length=1)


class FetchRequest(BaseModel):
    url: HttpUrl


class AndroidActionRequest(BaseModel):
    action: str
    arguments: list[str] = Field(default_factory=list)


class GitBackupRequest(BaseModel):
    message: str = Field(min_length=3)
    push: bool = False


class ImprovementFileChange(BaseModel):
    path: str = Field(min_length=1)
    content: str


class ImprovementRequest(BaseModel):
    description: str = Field(min_length=3)
    changes: list[ImprovementFileChange] = Field(min_length=1)
    run_tests: bool = True
    auto_apply: bool = False


class ImprovementCandidate(BaseModel):
    candidate_id: str
    description: str
    created_at: datetime
    files: list[str]
    protected_paths_blocked: list[str] = Field(default_factory=list)
    tests_passed: bool | None = None
    test_output: str = ""
    diff_preview: dict[str, str] = Field(default_factory=dict)
    applied: bool = False


class PolicyReport(BaseModel):
    protected_paths: list[str]
    forbidden_command_patterns: list[str]
    allowed_domains: list[str]
    wake_words: list[str]


class RuntimeEvent(BaseModel):
    category: str
    detail: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImprovementBackupRecord(BaseModel):
    candidate_id: str
    files: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))