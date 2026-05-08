# Modular Foundations

Mordecai is being steered away from the shape of a chat application and toward a modular Android-native AI operating layer. The purpose of this document is to pin the first architectural primitives that keep the project scalable.

## Foundation Systems

### Unified tool registry

The canonical runtime now exposes a registry of self-describing tools. Each tool advertises:

- stable tool name
- permission requirements
- description
- input schema
- output schema
- risk level
- confirmation policy
- safe-mode behavior
- sandbox profile

This is the backbone for agent planning, plugin compatibility, debugging, and future MCP-style interoperability.

### Tool execution engine

The registry now backs a structured execution layer rather than a raw function call. Each execution request carries:

- execution ID
- typed runtime context
- argument validation
- timeout boundary
- retry budget
- permission checks
- cooperative cancellation token

Each execution returns a structured result with status, output, attempts, duration, and a standardized failure payload when the call does not complete normally.

Completed executions are also persisted into runtime state so the execution trail survives process restarts and can be replayed from the dashboard trace surface.

The current failure taxonomy begins with:

- `PermissionDenied`
- `ValidationFailure`
- `ToolTimeout`
- `ExecutionCancelled`
- `ExecutionFailed`

### Developer trace surface

The event bus is now consumed as a first-class debugging surface. The runtime publishes trace events for:

- tool registration
- tool execution start, retry, completion, and failure
- provider selection and fallback decisions

The dashboard and API expose these traces directly so execution paths can be inspected without reading logs from disk.

The operator dashboard can also invoke registered tools directly against the same execution endpoint used by agents and tests.

### Event bus

Direct feature coupling is being replaced with an event stream model. The event bus supports publish, subscribe, and recent-history inspection so execution can be traced instead of guessed.

Target event families include:

- `tool.registered`
- `tool.execution.started`
- `tool.execution.retrying`
- `tool.execution.completed`
- `tool.execution.failed`
- `provider.selected`
- `provider.fallback`
- `notification.received`
- `accessibility.action_failed`
- `provider.changed`

### Replaceable provider contracts

Provider routing is now driven by a provider contract rather than provider-specific branching alone. Each provider declares a capability matrix including:

- streaming support
- vision support
- tool-calling support
- context window
- local versus remote execution

This keeps the runtime from hard-wiring itself to a single model vendor, makes degraded-mode fallback explicit, and reduces future migration cost.

## Architectural rules

1. Tools stay self-contained and communicate through registries or events rather than by reaching into each other.
2. Providers stay replaceable behind a stable request and response contract.
3. Agent execution stays observable through explicit events and traceable tool invocations.
4. Android automation must validate state, fail safely, and never assume a stable UI layout.
5. Permission escalation remains progressive and task-driven.
6. Runtime execution context must stay typed and explicit rather than expanding through arbitrary dictionaries.
7. High-risk providers such as shell and accessibility tools must use the same execution registry, permission checks, and failure taxonomy as lower-risk tools.