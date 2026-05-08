# Foundation Roadmap

This roadmap translates the current strategic direction into execution order.

## Phase 1

- stabilize the modular runtime shell
- keep the provider contract replaceable
- expand the unified tool registry
- stabilize the execution engine with structured failures and timeout boundaries
- route execution traces through the event bus
- isolate permissions and Android capability boundaries
- expose runtime capability discovery for tools and providers
- harden the developer trace panel so tool chains and provider routing stay inspectable

## Phase 2

- add reliable notification, intent, overlay, filesystem, and accessibility tools
- add Bluetooth, USB, and controller-oriented tooling
- strengthen automation verification and failure handling
- expand the shell and accessibility surfaces without weakening permission or sandbox boundaries

## Phase 3

- add planner, executor, verifier, and tool-selection agent slices
- extend execution history into replay and deeper debugging workflows
- build hybrid local and cloud routing policies

## Phase 4

- add plugin SDK and manifest format
- support downloadable tool packs and provider packs
- expose community extension points only after the core contracts are stable