from __future__ import annotations

from dataclasses import dataclass

from mordecai.agent import MordecaiRuntime
from mordecai.android_control import AndroidController
from mordecai.git_tools import GitService
from mordecai.main import build_runtime
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.self_improvement import SelfImprovementManager
from mordecai.store import StateStore


@dataclass(frozen=True, slots=True)
class RuntimeComponents:
    runtime: MordecaiRuntime
    proxy: SafeHttpClient
    git_service: GitService
    improvement_manager: SelfImprovementManager
    android_controller: AndroidController
    policy: PolicyEngine
    store: StateStore


def get_runtime_components() -> RuntimeComponents:
    runtime, proxy, git_service, improvement_manager, android, policy, store = build_runtime()
    return RuntimeComponents(
        runtime=runtime,
        proxy=proxy,
        git_service=git_service,
        improvement_manager=improvement_manager,
        android_controller=android,
        policy=policy,
        store=store,
    )