from functools import lru_cache

from mordecai.agent import MordecaiRuntime
from mordecai.android_control import AndroidController
from mordecai.config import ensure_state_dirs, get_settings
from mordecai.git_tools import GitService
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
    policy.attach_store(store)
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
    android = AndroidController(settings, policy, store=store)
    return runtime, proxy, git_service, improvement_manager, android, policy, store