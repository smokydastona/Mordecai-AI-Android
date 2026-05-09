from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import asdict
from dataclasses import dataclass, field
from inspect import isawaitable, signature
from threading import Event
from time import perf_counter
from typing import Any, Callable, Literal
from uuid import uuid4

from mordecai_core.events import EventBus


ToolHandler = Callable[..., Any]

_SCHEMA_TYPES: dict[str, type[Any]] = {
    "array": list,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
    "object": dict,
    "string": str,
}


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    session_id: str
    granted_permissions: frozenset[str] = field(default_factory=frozenset)
    provider_state: dict[str, object] = field(default_factory=dict)
    memory_refs: tuple[str, ...] = ()
    active_overlays: tuple[str, ...] = ()
    device_state: dict[str, object] = field(default_factory=dict)
    execution_metadata: dict[str, object] = field(default_factory=dict)
    safe_mode: bool = True
    cancellation: Event | None = None


@dataclass(frozen=True, slots=True)
class ToolExecutionRequest:
    tool_name: str
    arguments: dict[str, object] = field(default_factory=dict)
    context: RuntimeContext = field(default_factory=lambda: RuntimeContext(session_id="default"))
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    timeout_seconds: float = 10.0
    max_retries: int = 0


@dataclass(frozen=True, slots=True)
class ToolExecutionError:
    code: str
    message: str
    retryable: bool = False
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    execution_id: str
    tool_name: str
    status: Literal["completed", "failed", "cancelled"]
    output: Any = None
    error: ToolExecutionError | None = None
    attempts: int = 1
    duration_ms: float = 0.0


class ToolExecutionFailure(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}

    def to_error(self) -> ToolExecutionError:
        return ToolExecutionError(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            details=self.details,
        )


class ToolValidationFailure(ToolExecutionFailure):
    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__("ValidationFailure", message, details=details)


class PermissionDenied(ToolExecutionFailure):
    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__("PermissionDenied", message, details=details)


class ToolTimeout(ToolExecutionFailure):
    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__("ToolTimeout", message, retryable=True, details=details)


class ToolCancelled(ToolExecutionFailure):
    def __init__(self, message: str = "Tool execution was cancelled.", *, details: dict[str, object] | None = None) -> None:
        super().__init__("ExecutionCancelled", message, details=details)


class ProviderUnavailable(ToolExecutionFailure):
    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__("ProviderUnavailable", message, details=details)


class AutomationMismatch(ToolExecutionFailure):
    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__("AutomationMismatch", message, details=details)


class RateLimited(ToolExecutionFailure):
    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__("RateLimited", message, retryable=True, details=details)


class ContextOverflow(ToolExecutionFailure):
    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__("ContextOverflow", message, details=details)


@dataclass(frozen=True, slots=True)
class ToolManifest:
    tool: str
    permissions: tuple[str, ...]
    description: str
    provider: str = "runtime"
    input_schema: dict[str, object] = field(default_factory=dict)
    output_schema: dict[str, object] = field(default_factory=dict)
    risk_level: Literal["low", "moderate", "high"] = "low"
    confirmation_policy: Literal["never", "on-request", "always"] = "never"
    safe_mode_behavior: Literal["allow", "deny", "read-only"] = "allow"
    sandbox_profile: Literal["trusted", "workspace-write", "networked", "device-control"] = "trusted"
    default_timeout_seconds: float = 10.0
    default_max_retries: int = 0


class ToolRegistry:
    def __init__(self, event_bus: EventBus | None = None, execution_recorder: Callable[..., None] | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self.execution_recorder = execution_recorder
        self._manifests: dict[str, ToolManifest] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, manifest: ToolManifest, handler: ToolHandler) -> None:
        self._manifests[manifest.tool] = manifest
        self._handlers[manifest.tool] = handler
        self.event_bus.publish(
            "tool.registered",
            {"tool": manifest.tool, "permissions": list(manifest.permissions)},
        )

    def list_tools(self) -> list[ToolManifest]:
        return [self._manifests[name] for name in sorted(self._manifests)]

    def capability_manifest(self) -> list[dict[str, object]]:
        return [
            {
                "tool": manifest.tool,
                "provider": manifest.provider,
                "permissions": list(manifest.permissions),
                "description": manifest.description,
                "input_schema": manifest.input_schema,
                "output_schema": manifest.output_schema,
                "risk_level": manifest.risk_level,
                "confirmation_policy": manifest.confirmation_policy,
                "safe_mode_behavior": manifest.safe_mode_behavior,
                "sandbox_profile": manifest.sandbox_profile,
                "default_timeout_seconds": manifest.default_timeout_seconds,
                "default_max_retries": manifest.default_max_retries,
            }
            for manifest in self.list_tools()
        ]

    def describe(self, tool_name: str) -> ToolManifest:
        return self._manifests[tool_name]

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        started = perf_counter()
        attempts = 0
        last_error: ToolExecutionError | None = None
        manifest = self.describe(request.tool_name)
        self.event_bus.publish(
            "tool.execution.started",
            {
                "execution_id": request.execution_id,
                "tool": manifest.tool,
                "permissions": list(manifest.permissions),
                "session_id": request.context.session_id,
            },
        )
        try:
            self._validate_request(manifest, request)
            while attempts <= request.max_retries:
                attempts += 1
                self._check_cancellation(request)
                try:
                    output = self._run_with_timeout(request, self._handlers[request.tool_name])
                    duration_ms = (perf_counter() - started) * 1000
                    result = ToolExecutionResult(
                        execution_id=request.execution_id,
                        tool_name=request.tool_name,
                        status="completed",
                        output=output,
                        attempts=attempts,
                        duration_ms=duration_ms,
                    )
                    self.event_bus.publish(
                        "tool.execution.completed",
                        {
                            "execution_id": request.execution_id,
                            "tool": manifest.tool,
                            "attempts": attempts,
                            "duration_ms": duration_ms,
                        },
                    )
                    self._record_execution(result)
                    return result
                except ToolExecutionFailure as exc:
                    last_error = exc.to_error()
                    if attempts <= request.max_retries and exc.retryable:
                        self.event_bus.publish(
                            "tool.execution.retrying",
                            {
                                "execution_id": request.execution_id,
                                "tool": manifest.tool,
                                "attempt": attempts,
                                "error_code": exc.code,
                            },
                        )
                        continue
                    break
                except Exception as exc:  # pragma: no cover - exercised through retry path tests
                    last_error = ToolExecutionError(
                        code="ExecutionFailed",
                        message=str(exc),
                        retryable=attempts <= request.max_retries,
                        details={"tool": manifest.tool},
                    )
                    if attempts <= request.max_retries:
                        self.event_bus.publish(
                            "tool.execution.retrying",
                            {
                                "execution_id": request.execution_id,
                                "tool": manifest.tool,
                                "attempt": attempts,
                                "error_code": last_error.code,
                            },
                        )
                        continue
                    break
        except ToolExecutionFailure as exc:
            last_error = exc.to_error()

        duration_ms = (perf_counter() - started) * 1000
        status = "cancelled" if last_error and last_error.code == "ExecutionCancelled" else "failed"
        self.event_bus.publish(
            "tool.execution.failed",
            {
                "execution_id": request.execution_id,
                "tool": manifest.tool,
                "attempts": attempts,
                "duration_ms": duration_ms,
                "error_code": last_error.code if last_error else "ExecutionFailed",
            },
        )
        result = ToolExecutionResult(
            execution_id=request.execution_id,
            tool_name=request.tool_name,
            status=status,
            error=last_error,
            attempts=max(attempts, 1),
            duration_ms=duration_ms,
        )
        self._record_execution(result)
        return result

    def invoke(self, tool_name: str, *args: object, **kwargs: object) -> Any:
        manifest = self.describe(tool_name)
        self.event_bus.publish("tool.invoked", {"tool": manifest.tool})
        result = self._handlers[tool_name](*args, **kwargs)
        self.event_bus.publish("tool.completed", {"tool": manifest.tool})
        return result

    def _validate_request(self, manifest: ToolManifest, request: ToolExecutionRequest) -> None:
        missing_permissions = sorted(set(manifest.permissions) - set(request.context.granted_permissions))
        if missing_permissions:
            raise PermissionDenied(
                "Tool execution denied by permission policy.",
                details={"missing_permissions": missing_permissions},
            )
        if request.context.safe_mode and manifest.safe_mode_behavior == "deny":
            raise PermissionDenied(
                "Tool is disabled while runtime is in safe mode.",
                details={"tool": manifest.tool, "safe_mode_behavior": manifest.safe_mode_behavior},
            )
        self._validate_arguments(manifest, request.arguments)

    def _validate_arguments(self, manifest: ToolManifest, arguments: dict[str, object]) -> None:
        for name, schema_name in manifest.input_schema.items():
            if name not in arguments:
                raise ToolValidationFailure(
                    f"Missing required tool argument: {name}",
                    details={"argument": name, "tool": manifest.tool},
                )
            expected_type = _SCHEMA_TYPES.get(str(schema_name))
            if expected_type is not None and not isinstance(arguments[name], expected_type):
                raise ToolValidationFailure(
                    f"Invalid type for tool argument: {name}",
                    details={
                        "argument": name,
                        "expected": schema_name,
                        "received": type(arguments[name]).__name__,
                    },
                )
        extra_arguments = sorted(set(arguments) - set(manifest.input_schema))
        if extra_arguments and manifest.input_schema:
            raise ToolValidationFailure(
                "Unexpected tool arguments supplied.",
                details={"arguments": extra_arguments, "tool": manifest.tool},
            )

    def _check_cancellation(self, request: ToolExecutionRequest) -> None:
        if request.context.cancellation is not None and request.context.cancellation.is_set():
            raise ToolCancelled(details={"tool": request.tool_name})

    def _run_with_timeout(self, request: ToolExecutionRequest, handler: ToolHandler) -> Any:
        parameters = signature(handler).parameters
        if "runtime_context" in parameters:
            call = lambda: handler(runtime_context=request.context, **request.arguments)
        elif "context" in parameters and "context" not in request.arguments:
            call = lambda: handler(context=request.context, **request.arguments)
        else:
            call = lambda: handler(**request.arguments)

        def invoke_handler() -> Any:
            result = call()
            if isawaitable(result):
                return asyncio.run(result)
            return result

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(invoke_handler)
        try:
            return future.result(timeout=request.timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise ToolTimeout(
                f"Tool execution exceeded {request.timeout_seconds} seconds.",
                details={"tool": request.tool_name, "timeout_seconds": request.timeout_seconds},
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _record_execution(self, result: ToolExecutionResult) -> None:
        if self.execution_recorder is None:
            return
        self.execution_recorder(
            execution_id=result.execution_id,
            tool_name=result.tool_name,
            status=result.status,
            attempts=result.attempts,
            duration_ms=result.duration_ms,
            output=result.output,
            error=asdict(result.error) if result.error else None,
        )