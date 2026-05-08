from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from mordecai.agent import MordecaiRuntime
from mordecai.android_control import AndroidController
from mordecai.config import ensure_state_dirs, get_settings
from mordecai.dashboard import render_dashboard
from mordecai.git_tools import GitService
from mordecai.models import AndroidActionRequest, ChatRequest, FetchRequest, GithubSearchRequest, GitBackupRequest, ImprovementRequest, WebSearchRequest
from mordecai.policy import PolicyEngine
from mordecai.providers import ProviderRouter
from mordecai.proxy import SafeHttpClient
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore
from mordecai.watchdog import Watchdog


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
    runtime, proxy, git_service, improvement_manager, android, policy, _ = build_runtime()

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

    @app.get("/api/proxy/logs")
    async def proxy_logs() -> list[dict[str, object]]:
        return [entry.model_dump(mode="json") for entry in build_runtime()[-1].read_proxy_records()]

    @app.get("/api/voice")
    async def voice() -> dict[str, object]:
        return runtime.voice().__dict__

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, object]:
        try:
            response = await runtime.chat(request.message)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return response.model_dump(mode="json")

    @app.post("/api/github/search")
    async def github_search(request: GithubSearchRequest) -> list[dict[str, object]]:
        try:
            return await proxy.github_search_repositories(request.query, request.limit)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/web/search")
    async def web_search(request: WebSearchRequest) -> dict[str, object]:
        try:
            return await proxy.web_search(request.query)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/fetch")
    async def fetch(request: FetchRequest) -> dict[str, object]:
        try:
            text = await proxy.fetch_text(str(request.url))
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"url": str(request.url), "content": text[:5000]}

    @app.get("/api/git/status")
    async def git_status() -> dict[str, object]:
        return git_service.status()

    @app.post("/api/git/backup")
    async def git_backup(request: GitBackupRequest) -> dict[str, object]:
        if request.push and not settings.allow_git_push:
            raise HTTPException(status_code=403, detail="Push is disabled by configuration")
        try:
            return git_service.backup(request.message, push=request.push)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/improvement/propose")
    async def improvement_propose(request: ImprovementRequest) -> dict[str, object]:
        try:
            candidate = improvement_manager.create_candidate(request)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return candidate.model_dump(mode="json")

    @app.post("/api/improvement/rollback/{candidate_id}")
    async def improvement_rollback(candidate_id: str) -> dict[str, object]:
        try:
            candidate = improvement_manager.rollback_candidate(candidate_id)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return candidate.model_dump(mode="json")

    @app.post("/api/android/action")
    async def android_action(request: AndroidActionRequest) -> dict[str, object]:
        try:
            return android.perform(request.action, request.arguments)
        except Exception as exc:  # pragma: no cover - surfaced for API clients
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()