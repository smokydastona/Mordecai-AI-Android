from __future__ import annotations

import json
import re
from uuid import uuid4

from mordecai.models import AgentPlanRecord, AgentPlanRequest, AgentPlanResponse, AgentPlanStep, RuntimeFailure, RuntimeEvent
from mordecai.perception import PerceptionService
from mordecai_core.runtime import RuntimeComponents
from mordecai_core.tool_registry import RuntimeContext


class PlannerService:
    def __init__(self, components: RuntimeComponents, perception: PerceptionService) -> None:
        self.components = components
        self.perception = perception

    def build_plan(self, request: AgentPlanRequest) -> AgentPlanResponse:
        goal = request.goal.strip()
        perception = self.perception.latest_snapshot()
        memory_query = self._build_memory_query(goal, perception)
        memory_hits = self.components.runtime.search_memory(memory_query, limit=4)
        steps: list[AgentPlanStep] = []

        if memory_hits:
            steps.append(
                AgentPlanStep(
                    step_id="context-memory",
                    title="Recall relevant memory",
                    rationale="Use stored preferences, projects, and prior context before choosing tools.",
                    status="completed",
                    result=[item.record.content for item in memory_hits],
                )
            )
        if perception is not None:
            steps.append(
                AgentPlanStep(
                    step_id="context-perception",
                    title="Inspect current device context",
                    rationale="Use the latest app and visible screen state while planning.",
                    status="completed",
                    result={
                        "app_package": perception.app_package,
                        "activity": perception.activity,
                        "screen_title": perception.screen_title,
                        "visible_text": perception.visible_text[:8],
                        "action_labels": perception.action_labels[:8],
                    },
                )
            )

        for index, step in enumerate(self._tool_candidates(goal, perception)[: request.max_steps], start=1):
            steps.append(
                AgentPlanStep(
                    step_id=f"tool-{index}",
                    title=step["title"],
                    rationale=step["rationale"],
                    tool_name=step["tool_name"],
                    arguments=step["arguments"],
                )
            )

        if not any(step.tool_name for step in steps):
            steps.append(
                AgentPlanStep(
                    step_id="respond-only",
                    title="Respond from available context",
                    rationale="No registered tool matched the goal, so respond using memory and current context.",
                    status="planned",
                )
            )

        return AgentPlanResponse(
            plan_id=uuid4().hex[:12],
            session_id=request.session_id,
            goal=goal,
            memory_hits=memory_hits,
            perception=perception,
            steps=steps,
        )

    def run(self, request: AgentPlanRequest) -> AgentPlanResponse:
        plan = self.build_plan(request)
        if not request.auto_execute:
            plan.final_response = self._compose_response(plan)
            self._persist_plan(plan)
            return plan

        memory_refs = tuple(item.record.memory_id for item in plan.memory_hits)
        device_state = self.perception.device_state(plan.perception)

        for step in plan.steps:
            if not step.tool_name:
                continue
            result = self.components.execute_tool(
                step.tool_name,
                arguments=step.arguments,
                context=RuntimeContext(
                    session_id=request.session_id,
                    granted_permissions=frozenset(request.granted_permissions),
                    memory_refs=memory_refs,
                    device_state=device_state,
                    safe_mode=request.safe_mode,
                    execution_metadata={"goal": plan.goal, "planner_step_id": step.step_id},
                ),
            )
            if result.status == "completed":
                step.status = "completed"
                step.result = result.output
                continue
            step.status = result.status
            step.error = RuntimeFailure.model_validate(result.error.model_dump(mode="json")) if result.error else None
            break

        plan.executed = True
        plan.final_response = self._compose_response(plan)
        self.components.store.append_event(
            RuntimeEvent(
                category="planner",
                detail=f"executed:{request.session_id}:{len([step for step in plan.steps if step.status == 'completed' and step.tool_name])}",
            )
        )
        self._persist_plan(plan)
        return plan

    def history(self) -> list[AgentPlanRecord]:
        return self.components.store.read_plans()

    def get_plan(self, plan_id: str) -> AgentPlanRecord:
        record = self.components.store.get_plan(plan_id)
        if record is None:
            raise KeyError(plan_id)
        return record

    def _tool_candidates(self, goal: str, perception) -> list[dict[str, object]]:
        available_tools = {manifest.tool for manifest in self.components.tool_registry.list_tools()}
        lowered = goal.lower()
        steps: list[dict[str, object]] = []

        android_actions = self._android_action_candidates(goal, perception)
        if "android.control" in available_tools and android_actions is not None:
            steps.append(android_actions)

        if "git.status" in available_tools and any(token in lowered for token in ("git", "repo", "branch", "status")):
            steps.append(
                {
                    "title": "Inspect repository state",
                    "rationale": "Check current repository state before answering a repo-status question.",
                    "tool_name": "git.status",
                    "arguments": {},
                }
            )

        if "filesystem.read" in available_tools:
            path = self._extract_workspace_path(goal)
            if path is not None:
                steps.append(
                    {
                        "title": "Read referenced workspace file",
                        "rationale": "Use the explicit file path mentioned in the goal.",
                        "tool_name": "filesystem.read",
                        "arguments": {"path": path},
                    }
                )

        if "github.search" in available_tools and "github" in lowered:
            steps.append(
                {
                    "title": "Search GitHub repositories",
                    "rationale": "The goal explicitly references GitHub.",
                    "tool_name": "github.search",
                    "arguments": {"query": goal, "limit": 5},
                }
            )

        if "web.search" in available_tools and any(token in lowered for token in ("search", "look up", "lookup", "research", "web")):
            query = goal
            if perception is not None and ("current screen" in lowered or "this screen" in lowered):
                query = f"{goal} app:{perception.app_package or 'unknown'} screen:{perception.screen_title or 'unknown'} {' '.join(perception.visible_text[:5])}".strip()
            steps.append(
                {
                    "title": "Search the web",
                    "rationale": "The goal asks for external information.",
                    "tool_name": "web.search",
                    "arguments": {"query": query},
                }
            )

        if perception is None and "android.accessibility_dump" in available_tools and any(token in lowered for token in ("screen", "button", "visible", "app", "ui")):
            steps.append(
                {
                    "title": "Capture live accessibility dump",
                    "rationale": "No ingested screen context exists, so capture a read-only UI dump.",
                    "tool_name": "android.accessibility_dump",
                    "arguments": {},
                }
            )

        return steps

    def _android_action_candidates(self, goal: str, perception) -> dict[str, object] | None:
        lowered = goal.lower()
        if any(token in lowered for token in ("notifications", "notification shade", "show notifications")):
            return {
                "title": "Open notifications",
                "rationale": "The goal explicitly asks for a notification workflow.",
                "tool_name": "android.control",
                "arguments": {"action": "show_notifications", "arguments": []},
            }
        if any(token in lowered for token in ("quick settings", "show quick settings")):
            return {
                "title": "Open quick settings",
                "rationale": "The goal explicitly asks for quick settings.",
                "tool_name": "android.control",
                "arguments": {"action": "show_quick_settings", "arguments": []},
            }
        if any(token in lowered for token in ("go home", "return home", "home screen")):
            return {
                "title": "Return to home screen",
                "rationale": "The goal is a direct navigation action.",
                "tool_name": "android.control",
                "arguments": {"action": "home", "arguments": []},
            }
        if any(token in lowered for token in ("go back", "navigate back")):
            return {
                "title": "Navigate back",
                "rationale": "The goal is a direct back action.",
                "tool_name": "android.control",
                "arguments": {"action": "back", "arguments": []},
            }
        if "recent" in lowered or "app switcher" in lowered:
            return {
                "title": "Open recent apps",
                "rationale": "The goal references recent apps or the app switcher.",
                "tool_name": "android.control",
                "arguments": {"action": "recents", "arguments": []},
            }
        if any(token in lowered for token in ("open ", "launch ", "start app")):
            package = self._match_allowed_package(goal, perception)
            if package is not None:
                return {
                    "title": f"Launch {package}",
                    "rationale": "The goal asks to launch an allowlisted Android package.",
                    "tool_name": "android.control",
                    "arguments": {"action": "open_app", "arguments": [package]},
                }
        return None

    def _match_allowed_package(self, goal: str, perception) -> str | None:
        lowered = goal.lower()
        allowed_packages = list(self.components.runtime.settings.allowed_android_packages)
        for package in allowed_packages:
            package_key = package.lower()
            alias = package_key.rsplit(".", 1)[-1]
            if package_key in lowered or alias in lowered:
                return package
        if perception is not None and perception.app_package in allowed_packages and any(token in lowered for token in ("open current app", "reopen app", "launch current app")):
            return perception.app_package
        if "termux" in lowered and "com.termux" in allowed_packages:
            return "com.termux"
        return None

    def _build_memory_query(self, goal: str, perception) -> str:
        parts = [goal]
        if perception is not None:
            if perception.app_package:
                parts.append(perception.app_package)
            if perception.screen_title:
                parts.append(perception.screen_title)
            parts.extend(perception.visible_text[:6])
        return " ".join(parts)

    def _extract_workspace_path(self, goal: str) -> str | None:
        matches = re.findall(r"([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)", goal)
        workspace = self.components.runtime.settings.workspace_dir
        for match in matches:
            candidate = (workspace / match.replace("\\", "/")).resolve()
            try:
                candidate.relative_to(workspace)
            except ValueError:
                continue
            if candidate.exists() and candidate.is_file():
                return candidate.as_posix()
        return None

    def _compose_response(self, plan: AgentPlanResponse) -> str:
        lines = [f"Goal: {plan.goal}"]
        if plan.perception is not None:
            lines.append(
                f"Current app: {plan.perception.app_package or 'unknown'}"
                + (f" ({plan.perception.screen_title})" if plan.perception.screen_title else "")
            )
        if plan.memory_hits:
            lines.append("Relevant memory:")
            for item in plan.memory_hits[:3]:
                lines.append(f"- [{item.record.category}] {item.record.content}")
        tool_steps = [step for step in plan.steps if step.tool_name]
        if tool_steps:
            lines.append("Plan execution:")
            for step in tool_steps:
                if step.status == "completed":
                    payload = json.dumps(step.result, default=str)[:280]
                    lines.append(f"- {step.title}: {payload}")
                elif step.error is not None:
                    lines.append(f"- {step.title}: {step.error.code} - {step.error.message}")
                else:
                    lines.append(f"- {step.title}: {step.status}")
        else:
            lines.append("No matching tool was required; answer is based on stored context and the current screen state.")
        return "\n".join(lines)

    def _persist_plan(self, plan: AgentPlanResponse) -> None:
        self.components.store.save_plan(
            AgentPlanRecord(
                plan_id=plan.plan_id or uuid4().hex[:12],
                session_id=plan.session_id or "agent-api",
                goal=plan.goal,
                created_at=plan.created_at,
                executed=plan.executed,
                final_response=plan.final_response,
                memory_hits=plan.memory_hits,
                perception=plan.perception,
                steps=plan.steps,
            )
        )