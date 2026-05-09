import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from mordecai.config import ensure_state_dirs, get_settings
from mordecai.bootstrap import build_runtime
from mordecai.dashboard import render_dashboard
from mordecai.local_models import LocalModelService
from mordecai.models import AndroidActionRequest, ApiErrorResponse, ChatRequest, FetchRequest, GithubSearchRequest, GitBackupRequest, GoalRequest, ImprovementRequest, LocalModelInstallRequest, RoutineRequest, RuntimeFailure, ToolExecutionApiRequest, ToolExecutionApiResponse, VoiceSynthesizeRequest, VoiceTranscribeRequest, WebSearchRequest
from mordecai.store import StateStoreError
from mordecai.voice import VoiceService
from mordecai_core.tool_registry import RuntimeContext


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    from mordecai_core.runtime import get_runtime_components

    components = get_runtime_components()
    runtime = components.runtime
    proxy = components.proxy
    git_service = components.git_service
    improvement_manager = components.improvement_manager
    android = components.android_controller
    policy = components.policy
    local_models = LocalModelService(settings, proxy=proxy, store=components.store)
    voice_service = VoiceService(settings)
    app.state.local_models = local_models
    app.state.voice_service = voice_service

    def raise_api_error(status_code: int, code: str, message: str, details: dict[str, object] | None = None) -> None:
        raise HTTPException(
            status_code=status_code,
            detail=ApiErrorResponse(error=RuntimeFailure(code=code, message=message, details=details or {})).model_dump(mode="json"),
        )

    def raise_mapped_exception(exc: Exception) -> None:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(exc, StateStoreError):
            raise_api_error(500, "StateStoreFailure", str(exc))
        if isinstance(exc, PermissionError):
            raise_api_error(403, "PermissionDenied", str(exc))
        if isinstance(exc, FileNotFoundError):
            raise_api_error(404, "NotFound", str(exc))
        if isinstance(exc, KeyError):
            raise_api_error(404, "NotFound", str(exc).strip("'"))
        if isinstance(exc, ValueError):
            raise_api_error(400, "ValidationFailure", str(exc))
        if isinstance(exc, RuntimeError):
            lowered = str(exc).lower()
            if "rate limit" in lowered:
                raise_api_error(429, "RateLimited", str(exc))
            raise_api_error(400, "ExecutionFailed", str(exc))
        raise_api_error(500, "ExecutionFailed", str(exc))

    def status_code_for_failure(code: str) -> int:
        if code in {"PermissionDenied"}:
            return 403
        if code in {"ValidationFailure", "AutomationMismatch", "ContextOverflow"}:
            return 400
        if code in {"ToolTimeout"}:
            return 408
        if code in {"RateLimited"}:
            return 429
        if code in {"ProviderUnavailable"}:
            return 503
        if code in {"ExecutionCancelled"}:
            return 409
        return 500

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        return render_dashboard()

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_alias() -> str:
        return render_dashboard()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "name": settings.app_name, "environment": settings.environment}

    @app.get("/api/status")
    async def status() -> dict[str, object]:
        return runtime.status().model_dump(mode="json")

    @app.get("/api/policy")
    async def policy_report() -> dict[str, object]:
        return policy.report().model_dump(mode="json")

    @app.get("/api/memory")
    async def memory() -> list[dict[str, object]]:
        return [entry.model_dump(mode="json") for entry in runtime.memory()]

    @app.get("/api/goals")
    async def goals() -> list[dict[str, object]]:
        return [goal.model_dump(mode="json") for goal in runtime.goals()]

    @app.post("/api/goals")
    async def create_goal(request: GoalRequest) -> dict[str, object]:
        return runtime.create_goal(request).model_dump(mode="json")

    @app.get("/api/routines")
    async def routines() -> list[dict[str, object]]:
        return [routine.model_dump(mode="json") for routine in runtime.routines()]

    @app.post("/api/routines")
    async def create_routine(request: RoutineRequest) -> dict[str, object]:
        return runtime.create_routine(request).model_dump(mode="json")

    @app.get("/api/events")
    async def events() -> list[dict[str, object]]:
        return runtime.events()

    @app.get("/api/runtime/trace")
    async def runtime_trace() -> dict[str, object]:
        return components.trace_snapshot()

    @app.get("/api/runtime/capabilities")
    async def runtime_capabilities() -> dict[str, object]:
        return components.discover_capabilities()

    @app.get("/api/proxy/logs")
    async def proxy_logs() -> list[dict[str, object]]:
        return [entry.model_dump(mode="json") for entry in components.store.read_proxy_records()]

    @app.get("/api/voice")
    async def voice() -> dict[str, object]:
        return runtime.voice().__dict__

    @app.get("/api/voice/engines")
    async def voice_engines() -> dict[str, object]:
        return app.state.voice_service.engines()

    @app.get("/api/voice/catalog")
    async def voice_catalog(
        query: str | None = Query(default=None),
        category: str | None = Query(default=None),
        runtime_fit: str | None = Query(default=None),
        integration_tier: str | None = Query(default=None),
        supported_only: bool = Query(default=False),
        approval_required: bool | None = Query(default=None),
        limit: int | None = Query(default=None, ge=1, le=500),
    ) -> dict[str, object]:
        return app.state.voice_service.catalog(
            query=query,
            category=category,
            runtime_fit=runtime_fit,
            integration_tier=integration_tier,
            supported_only=supported_only,
            approval_required=approval_required,
            limit=limit,
        )

    @app.post("/api/voice/synthesize")
    async def voice_synthesize(request: VoiceSynthesizeRequest) -> dict[str, object]:
        try:
            return app.state.voice_service.synthesize(request.text, output_filename=request.output_filename)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    @app.post("/api/voice/transcribe")
    async def voice_transcribe(request: VoiceTranscribeRequest) -> dict[str, object]:
        try:
            return app.state.voice_service.transcribe(request.audio_path, model=request.model, provider=request.provider)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    @app.get("/api/avatar")
    async def avatar() -> dict[str, object]:
        return runtime.avatar().model_dump(mode="json")

    @app.get("/api/local-models")
    async def local_models_catalog() -> dict[str, object]:
        return app.state.local_models.catalog_snapshot().model_dump(mode="json")

    @app.post("/api/local-models/install")
    async def local_models_install(request: LocalModelInstallRequest) -> dict[str, object]:
        try:
            result = await app.state.local_models.install(request)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)
        return result.model_dump(mode="json")

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, object]:
        try:
            response = await runtime.chat(request.message)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)
        return response.model_dump(mode="json")

    @app.post("/api/github/search")
    async def github_search(request: GithubSearchRequest) -> list[dict[str, object]]:
        try:
            return await proxy.github_search_repositories(request.query, request.limit)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    @app.post("/api/web/search")
    async def web_search(request: WebSearchRequest) -> dict[str, object]:
        try:
            return await proxy.web_search(request.query)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    @app.post("/api/fetch")
    async def fetch(request: FetchRequest) -> dict[str, object]:
        try:
            text = await proxy.fetch_text(str(request.url))
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)
        return {"url": str(request.url), "content": text[:5000]}

    @app.post("/api/tools/execute", response_model=ToolExecutionApiResponse)
    async def tools_execute(request: ToolExecutionApiRequest) -> dict[str, object]:
        try:
            result = components.execute_tool(
                request.tool,
                arguments=request.arguments,
                context=RuntimeContext(
                    session_id=request.session_id,
                    granted_permissions=frozenset(request.granted_permissions),
                    provider_state=request.provider_state,
                    memory_refs=tuple(request.memory_refs),
                    active_overlays=tuple(request.active_overlays),
                    device_state=request.device_state,
                    execution_metadata=request.execution_metadata,
                    safe_mode=request.safe_mode,
                ),
                timeout_seconds=request.timeout_seconds,
                max_retries=request.max_retries,
            )
        except KeyError as exc:
            raise_api_error(404, "NotFound", f"Tool '{request.tool}' is not available in the current mode")
        if result.status != "completed":
            code = result.error.code if result.error else "ExecutionFailed"
            raise_api_error(
                status_code_for_failure(code),
                code,
                result.error.message if result.error else "Tool execution failed.",
                details={
                    **(result.error.details if result.error else {}),
                    "execution_id": result.execution_id,
                    "tool": result.tool_name,
                    "attempts": result.attempts,
                    "duration_ms": result.duration_ms,
                },
            )
        return ToolExecutionApiResponse(
            execution_id=result.execution_id,
            tool_name=result.tool_name,
            status=result.status,
            output=result.output,
            attempts=result.attempts,
            duration_ms=result.duration_ms,
        ).model_dump(mode="json")

    @app.get("/api/git/status")
    async def git_status() -> dict[str, object]:
        return git_service.status()

    @app.post("/api/git/backup")
    async def git_backup(request: GitBackupRequest) -> dict[str, object]:
        if request.push and not settings.allow_git_push:
            raise_api_error(403, "PermissionDenied", "Push is disabled by configuration")
        try:
            return git_service.backup(request.message, push=request.push)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    @app.post("/api/improvement/propose")
    async def improvement_propose(request: ImprovementRequest) -> dict[str, object]:
        try:
            candidate = improvement_manager.create_candidate(request)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)
        return candidate.model_dump(mode="json")

    @app.get("/api/improvement/candidates")
    async def improvement_candidates() -> list[dict[str, object]]:
        return [candidate.model_dump(mode="json") for candidate in improvement_manager.list_candidates()]

    @app.get("/api/improvement/backups")
    async def improvement_backups() -> list[dict[str, object]]:
        return [backup.model_dump(mode="json") for backup in improvement_manager.list_backups()]

    @app.post("/api/improvement/apply/{candidate_id}")
    async def improvement_apply(candidate_id: str) -> dict[str, object]:
        try:
            candidate = improvement_manager.apply_candidate(candidate_id)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)
        return candidate.model_dump(mode="json")

    @app.post("/api/improvement/rollback/{candidate_id}")
    async def improvement_rollback(candidate_id: str) -> dict[str, object]:
        try:
            candidate = improvement_manager.rollback_candidate(candidate_id)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)
        return candidate.model_dump(mode="json")

    @app.post("/api/android/action")
    async def android_action(request: AndroidActionRequest) -> dict[str, object]:
        try:
            return android.perform(request.action, request.arguments)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    @app.get("/api/android/mode-b/state")
    async def mode_b_state() -> dict[str, object]:
        """Query recovery-layer Mode B initialization state."""
        try:
            return android.get_mode_b_state()
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    @app.post("/api/android/mode-b/action")
    async def mode_b_action(request: AndroidActionRequest) -> dict[str, object]:
        """Execute Mode B rooted shell actions."""
        try:
            # Ensure action is a Mode B action
            if not request.action.startswith("mode_b_"):
                raise ValueError(f"Use /api/android/action for non-Mode-B actions; use 'mode_b_' prefix for Mode B actions")
            return android.perform(request.action, request.arguments)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise_mapped_exception(exc)

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    ensure_state_dirs(settings)
    uvicorn.run(app, host=settings.service_host, port=settings.service_port)


if __name__ == "__main__":
    run()