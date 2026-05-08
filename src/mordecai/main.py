from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from mordecai.agent import MordecaiRuntime
from mordecai.android_control import AndroidController
from mordecai.config import ensure_state_dirs, get_settings
from mordecai.dashboard import render_dashboard
from mordecai.git_tools import GitService
from mordecai.models import AndroidActionRequest, ApiErrorResponse, ChatRequest, FetchRequest, GithubSearchRequest, GitBackupRequest, ImprovementRequest, RuntimeFailure, ToolExecutionApiRequest, ToolExecutionApiResponse, WebSearchRequest
from mordecai.policy import PolicyEngine
from mordecai.providers import ProviderRouter
from mordecai.proxy import SafeHttpClient
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore
from mordecai.watchdog import Watchdog
from mordecai_core.tool_registry import RuntimeContext


@lru_cache(maxsize=1)
def build_runtime() -> tuple[MordecaiRuntime, SafeHttpClient, GitService, SelfImprovementManager, AndroidController, PolicyEngine, StateStore]:
    settings = get_settings()
    ensure_state_dirs(settings)
    store = StateStore(settings.state_dir, settings.max_log_entries)
    policy = PolicyEngine(settings)
    proxy = SafeHttpClient(settings, policy, store)
    git_service = GitService(settings.workspace_dir)
    improvement_manager = SelfImprovementManager(settings, policy, store)
    runtime = MordecaiRuntime(
        settings=settings,
        store=store,
        policy=policy,
        proxy=proxy,
        git_service=git_service,
        provider_router=ProviderRouter(settings, proxy),
        improvement_manager=improvement_manager,
        watchdog=Watchdog(settings),
    )
    android = AndroidController(settings, policy)
    return runtime, proxy, git_service, improvement_manager, android, policy, store


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

    def raise_api_error(status_code: int, code: str, message: str, details: dict[str, object] | None = None) -> None:
        raise HTTPException(
            status_code=status_code,
            detail=ApiErrorResponse(error=RuntimeFailure(code=code, message=message, details=details or {})).model_dump(mode="json"),
        )

    def raise_mapped_exception(exc: Exception) -> None:
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

    return app


app = create_app()