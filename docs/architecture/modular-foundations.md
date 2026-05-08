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

The current failure taxonomy begins with:

- `PermissionDenied`
- `ValidationFailure`
- `ToolTimeout`
- `ExecutionCancelled`
- `ExecutionFailed`

### Event bus

Direct feature coupling is being replaced with an event stream model. The event bus supports publish, subscribe, and recent-history inspection so execution can be traced instead of guessed.

Target event families include:

- `tool.registered`
- `tool.execution.started`
- `tool.execution.retrying`
- `tool.execution.completed`
- `tool.execution.failed`
- `notification.received`
- `accessibility.action_failed`
- `provider.changed`

### Replaceable provider contracts

Provider routing is now driven by a provider contract rather than provider-specific branching alone. This keeps the runtime from hard-wiring itself to a single model vendor and reduces future migration cost.

## Architectural rules

1. Tools stay self-contained and communicate through registries or events rather than by reaching into each other.
2. Providers stay replaceable behind a stable request and response contract.
3. Agent execution stays observable through explicit events and traceable tool invocations.
4. Android automation must validate state, fail safely, and never assume a stable UI layout.
5. Permission escalation remains progressive and task-driven.
6. Runtime execution context must stay typed and explicit rather than expanding through arbitrary dictionaries.