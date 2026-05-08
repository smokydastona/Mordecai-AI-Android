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

This is the backbone for agent planning, plugin compatibility, debugging, and future MCP-style interoperability.

### Event bus

Direct feature coupling is being replaced with an event stream model. The event bus supports publish, subscribe, and recent-history inspection so execution can be traced instead of guessed.

Target event families include:

- `tool.registered`
- `tool.invoked`
- `tool.completed`
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