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

## Exit criteria by phase

### Phase 1 exit criteria

- portable Mode A install is reproducible from the public Termux command
- first boot exports provider and tool contracts successfully
- dashboard, policy report, and localhost API all come up from the deployed scripts
- core provider and tool surfaces are discoverable without reading source code
- docs explain Mode A install and Mode B gating clearly enough that operators do not need to infer the difference

### Phase 2 exit criteria

- Android-native shell supervision is reliable on supported devices
- advanced automation remains opt-in and policy-auditable
- failure paths preserve enough evidence for device debugging and rollback

### Phase 3 exit criteria

- planner and executor slices use the formal tool manifest instead of ad hoc tool assumptions
- provider routing decisions are traceable and debuggable through the runtime API
- replay and verification flows can explain why a tool chain succeeded or failed

### Phase 4 exit criteria

- extension points consume the same provider and tool contracts already used by the core runtime
- no plugin path bypasses permission checks, safe mode, or policy enforcement

## Current high-impact priorities

- keep the Mode A install surface honest and fully documented
- treat exported contracts as part of the shipped operator surface
- harden first boot and recovery procedures before widening automation scope
- make Mode B documentation precise enough that rooted-device work does not bleed into the default install story