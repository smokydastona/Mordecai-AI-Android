from __future__ import annotations

from typing import Any

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


class MemoryRecord(BaseModel):
    memory_id: str
    category: str = Field(pattern="^(preference|project|contact|task|fact|episode)$")
    content: str = Field(min_length=3)
    tags: list[str] = Field(default_factory=list)
    source: str = "runtime"
    importance: int = Field(default=1, ge=1, le=5)
    pinned: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryWriteRequest(BaseModel):
    category: str = Field(pattern="^(preference|project|contact|task|fact|episode)$")
    content: str = Field(min_length=3)
    tags: list[str] = Field(default_factory=list)
    source: str = "api"
    importance: int = Field(default=1, ge=1, le=5)
    pinned: bool = False


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=25)
    categories: list[str] = Field(default_factory=list)
    pinned_only: bool = False


class MemorySearchResult(BaseModel):
    record: MemoryRecord
    score: float


class PerceptionElement(BaseModel):
    text: str | None = None
    content_desc: str | None = None
    resource_id: str | None = None
    class_name: str | None = None
    package: str | None = None
    clickable: bool = False
    enabled: bool = True
    bounds: str | None = None


class NotificationActionMetadata(BaseModel):
    title: str
    action_type: str = "notification-action"


class FocusedNodeSnapshot(BaseModel):
    text: str | None = None
    content_desc: str | None = None
    resource_id: str | None = None
    class_name: str | None = None
    package: str | None = None
    clickable: bool = False
    enabled: bool = True
    bounds: str | None = None


class AndroidPerceptionIngestRequest(BaseModel):
    source: str = "android-shell"
    app_package: str | None = None
    activity: str | None = None
    screen_title: str | None = None
    visible_text: list[str] = Field(default_factory=list)
    action_labels: list[str] = Field(default_factory=list)
    focused_text: str | None = None
    clipboard_text: str | None = None
    notification_summaries: list[str] = Field(default_factory=list)
    notification_actions: list[NotificationActionMetadata] = Field(default_factory=list)
    focused_node: FocusedNodeSnapshot | None = None
    ui_dump_xml: str | None = None
    screenshot_path: str | None = None
    interactive: bool = True


class AndroidPerceptionSnapshot(BaseModel):
    snapshot_id: str
    source: str
    app_package: str | None = None
    activity: str | None = None
    screen_title: str | None = None
    visible_text: list[str] = Field(default_factory=list)
    action_labels: list[str] = Field(default_factory=list)
    focused_text: str | None = None
    focused_node: FocusedNodeSnapshot | None = None
    clipboard_text: str | None = None
    notification_summaries: list[str] = Field(default_factory=list)
    notification_actions: list[NotificationActionMetadata] = Field(default_factory=list)
    ui_elements: list[PerceptionElement] = Field(default_factory=list)
    screenshot_path: str | None = None
    interactive: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentPlanStep(BaseModel):
    step_id: str
    title: str
    rationale: str
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str = "planned"
    result: Any = None
    error: RuntimeFailure | None = None


class AgentPlanRequest(BaseModel):
    goal: str = Field(min_length=3)
    auto_execute: bool = False
    granted_permissions: list[str] = Field(default_factory=list)
    session_id: str = "agent-api"
    safe_mode: bool = True
    max_steps: int = Field(default=5, ge=1, le=10)


class AgentPlanResponse(BaseModel):
    goal: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    plan_id: str | None = None
    session_id: str | None = None
    memory_hits: list[MemorySearchResult] = Field(default_factory=list)
    perception: AndroidPerceptionSnapshot | None = None
    steps: list[AgentPlanStep] = Field(default_factory=list)
    executed: bool = False
    final_response: str = ""


class AgentPlanRecord(BaseModel):
    plan_id: str
    session_id: str
    goal: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    executed: bool = False
    final_response: str = ""
    memory_hits: list[MemorySearchResult] = Field(default_factory=list)
    perception: AndroidPerceptionSnapshot | None = None
    steps: list[AgentPlanStep] = Field(default_factory=list)


class VoiceSessionStartRequest(BaseModel):
    label: str = "background"
    background: bool = True


class VoiceSessionRecord(BaseModel):
    session_id: str
    label: str = "background"
    background: bool = True
    status: str = "awaiting-wake-word"
    last_wake_word: str | None = None
    last_transcript: str | None = None
    pending_command: str | None = None
    last_response: str | None = None
    last_audio_path: str | None = None
    last_plan_goal: str | None = None
    interrupted_count: int = 0
    last_error: RuntimeFailure | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VoiceSessionEventRequest(BaseModel):
    transcript: str = ""
    is_final: bool = False
    interrupt: bool = False
    playback_finished: bool = False
    auto_execute: bool = True
    synthesize_response: bool = False
    granted_permissions: list[str] = Field(default_factory=list)
    safe_mode: bool = True


class VoiceSessionEventResponse(BaseModel):
    session: VoiceSessionRecord
    plan: AgentPlanResponse | None = None
    wake_word_detected: bool = False


class ProxyRequestRecord(BaseModel):
    request_id: str | None = None
    method: str
    url: str
    allowed: bool
    reason: str
    status_code: int | None = None
    latency_ms: float | None = None
    response_bytes: int | None = None
    redirect_count: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PolicyAuditRecord(BaseModel):
    audit_id: str
    surface: str
    target: str
    allowed: bool
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProviderHealthRecord(BaseModel):
    provider: str
    healthy: bool
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RequestLatencyRecord(BaseModel):
    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    provider: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RequestLatencySummary(BaseModel):
    request_count: int = 0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    max_ms: float = 0.0
    average_ms: float = 0.0


class ToolExecutionTimelineRecord(BaseModel):
    timeline_id: str
    session_id: str
    plan_id: str | None = None
    step_id: str | None = None
    step_title: str
    tool_name: str | None = None
    status: str
    duration_ms: float
    attempts: int = 0
    error: RuntimeFailure | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AndroidDiagnosticRecord(BaseModel):
    diagnostic_id: str
    category: str
    source: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StatusSnapshot(BaseModel):
    app_name: str
    mode: str
    provider: str
    environment: str
    git_branch: str | None
    git_dirty: bool
    pending_candidates: int
    wake_words: list[str]
    cpu_percent: float
    memory_mb: float
    recent_requests: int
    service_host: str
    service_port: int
    avatar_emotion: str
    active_goals: int = 0
    active_routines: int = 0


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


class VoiceSynthesizeRequest(BaseModel):
    text: str = Field(min_length=1)
    output_filename: str | None = None


class VoiceTranscribeRequest(BaseModel):
    audio_path: str = Field(min_length=1)
    model: str = "base"
    provider: str = "whisper"


class GitBackupRequest(BaseModel):
    message: str = Field(min_length=3)
    push: bool = False


class RuntimeFailure(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(BaseModel):
    error: RuntimeFailure


class ToolExecutionApiRequest(BaseModel):
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    granted_permissions: list[str] = Field(default_factory=list)
    session_id: str = "api"
    timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    max_retries: int = Field(default=0, ge=0, le=3)
    safe_mode: bool = True
    provider_state: dict[str, Any] = Field(default_factory=dict)
    memory_refs: list[str] = Field(default_factory=list)
    active_overlays: list[str] = Field(default_factory=list)
    device_state: dict[str, Any] = Field(default_factory=dict)
    execution_metadata: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionApiResponse(BaseModel):
    execution_id: str
    tool_name: str
    status: str
    output: Any = None
    error: RuntimeFailure | None = None
    attempts: int
    duration_ms: float


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
    diff_filters_blocked: list[str] = Field(default_factory=list)
    tests_passed: bool | None = None
    test_output: str = ""
    diff_preview: dict[str, str] = Field(default_factory=dict)
    applied: bool = False


class PolicyReport(BaseModel):
    mode: str
    protected_paths: list[str]
    forbidden_command_patterns: list[str]
    allowed_domains: list[str]
    wake_words: list[str]
    allowed_features: list[str] = Field(default_factory=list)
    blocked_features: list[str] = Field(default_factory=list)


class RuntimeEvent(BaseModel):
    category: str
    detail: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImprovementBackupRecord(BaseModel):
    candidate_id: str
    files: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolExecutionRecord(BaseModel):
    execution_id: str
    tool_name: str
    status: str
    attempts: int
    duration_ms: float
    output: Any = None
    error: RuntimeFailure | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GoalRecord(BaseModel):
    goal_id: str
    title: str
    description: str
    status: str = "active"
    priority: str = "normal"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RoutineRecord(BaseModel):
    routine_id: str
    title: str
    description: str
    trigger: str
    enabled: bool = True
    last_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GoalRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3)
    priority: str = Field(default="normal")


class RoutineRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3)
    trigger: str = Field(min_length=3)
    enabled: bool = True


class AvatarFrame(BaseModel):
    emotion: str
    label: str
    asset_path: str
    svg: str


class AvatarProfile(BaseModel):
    style: str
    immutable_assets: bool
    immutable_behavior: bool
    immutable_style: bool
    current_emotion: str
    frames: list[AvatarFrame] = Field(default_factory=list)


class LocalModelProfileSnapshot(BaseModel):
    name: str
    provider: str
    modality: str
    command: str
    context_window: int
    enabled: bool = True
    prompt_format: str | None = None
    model_path: str | None = None
    binary_available: bool = False
    model_available: bool | None = None
    catalog_slug: str | None = None
    runtime_fit: str | None = None
    integration_tier: str | None = None
    install_asset_ids: list[str] = Field(default_factory=list)


class LocalModelAssetSnapshot(BaseModel):
    asset_id: str
    display_name: str
    profile_name: str | None = None
    modality: str
    filename: str
    destination: str
    source_url: str
    description: str
    executable: bool = False
    installed: bool = False
    size_mb: float | None = None
    sha256: str | None = None
    catalog_slug: str | None = None
    runtime_fit: str | None = None
    integration_tier: str | None = None
    requires_operator_approval: bool = False
    install_notes: str | None = None
    archive_format: str | None = None


class LocalModelBundleSnapshot(BaseModel):
    bundle_id: str
    display_name: str
    description: str
    asset_ids: list[str] = Field(default_factory=list)
    installed_assets: int = 0
    total_assets: int = 0
    runtime_fit: str | None = None
    integration_tier: str | None = None
    requires_operator_approval: bool = False
    install_notes: str | None = None
    catalog_slugs: list[str] = Field(default_factory=list)


class LocalModelCatalogSnapshot(BaseModel):
    models_dir: str
    available_profiles: int
    configured_profiles: int
    profiles: list[LocalModelProfileSnapshot] = Field(default_factory=list)
    assets: list[LocalModelAssetSnapshot] = Field(default_factory=list)
    bundles: list[LocalModelBundleSnapshot] = Field(default_factory=list)


class LocalModelInstallRequest(BaseModel):
    bundle_id: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    overwrite: bool = False
    acknowledge_operator_approval: bool = False


class LocalModelInstallResult(BaseModel):
    bundle_id: str | None = None
    installed_assets: list[LocalModelAssetSnapshot] = Field(default_factory=list)
    skipped_assets: list[LocalModelAssetSnapshot] = Field(default_factory=list)
    approval_acknowledged: bool = False
    extracted_paths: list[str] = Field(default_factory=list)