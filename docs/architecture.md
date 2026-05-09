# Mordecai AI OS Architecture

Mordecai is not being built as a feature-heavy assistant application. It is being built as an Android-native operating layer with explicit constitutions around policy, execution, observability, and reversibility. This document defines the architectural rules that keep that direction stable.

## Constitutional principles

1. Safety boundaries are real boundaries.
   Network, git, Android control, and self-modification must remain behind explicit policy and approval surfaces.

2. Capabilities stay decoupled from implementations.
   Tools, providers, and runtime services are selected through contracts and registries rather than hard-wired call chains.

3. Execution must be inspectable.
   High-impact actions need execution IDs, trace events, structured failures, and enough retained context to explain what happened.

4. Automation is progressive, not assumed.
   Device control, overlays, accessibility, and shell-class behaviors must unlock through explicit permissions and safe-mode constraints.

5. Self-modification is reversible or it does not ship.
   Candidates must stage in a sandbox, run tests there, surface diffs, and preserve rollback paths.

## Runtime stack

### 1. Device layer

Supported Android phone hardware, radios, sensors, power management, and physical recovery surfaces. The Galaxy S10e remains the advanced reference device, not the only target.

### 2. Android OS layer

The handset operating system, ideally a debloated base with explicit control over updates, radios, and developer access.

### 3. Control layer

ADB access, package allowlists, guarded automation hooks, and any future accessibility or overlay drivers. This layer must remain opt-in and recoverable.

### 4. Sandbox layer

The Termux plus proot Linux environment where Python services, model runtimes, and experiments run without mutating the base OS directly.

Phase 1 freezes this layer into a portable backend contract rooted at `$HOME/mordecai`, with `backend/`, `env/`, `data/`, and `scripts/` as the stable install layout for Mode A.

### 5. Runtime layer

The active FastAPI runtime currently implemented in `src/mordecai/`. This layer owns chat orchestration, API serving, dashboard rendering, state storage, and service wiring.

The native Android shell in `android-shell/` sits above this layer as the Phase 2 supervision surface, but it does not bypass the runtime or policy layers.

### 6. Execution layer

The modular execution surface in `mordecai_core/` and `providers/`. This includes:

- tool registry and manifests
- runtime context and execution IDs
- timeout and retry boundaries
- structured failure taxonomy
- provider capability routing
- developer trace surfaces

### 7. Policy layer

Protected paths, command guards, outbound allowlists, rate limits, and permission gating. This is the hard boundary that keeps experimentation from escaping into unsafe control.

### 8. Model and voice layer

Cloud and local model routing, future STT/TTS systems, wake-word handling, and persona enforcement.

The permanent avatar also anchors here as a policy-protected identity surface whose assets and behavior are not mutable through the self-improvement path. The runtime derives its available expressions directly from the protected SVG set in `assets/avatar/`, so identity updates require explicit asset changes rather than silent prompt-only drift.

### 9. Self-modification and operator layer

Candidate proposal, sandbox execution, promotion, rollback, observability, and the human approval path for anything with real impact.

The runtime also persists long-term goals and routine triggers as operator-visible state, keeping task memory explicit instead of hidden in prompt-only context.

Local model profiles are also surfaced as first-class runtime state so operators can inspect configured chat, STT, and TTS backends through the same dashboard and API used for the live system. These profiles are declarative integration targets, not proof that the corresponding model weights are already present on-device.

## Repository mapping

- `src/mordecai/` holds the working runtime implementation and HTTP/dashboard surface.
- `mordecai_core/` holds execution primitives, eventing, runtime composition, and provider contracts.
- `providers/` holds concrete tool providers such as Android control, git operations, and local/cloud LLM execution.
- `tests/` is the enforcement layer for API behavior, tool contracts, proxy allowlists, policy protection, and sandboxed self-modification.
- `prompts/system_prompt.txt` defines the active operator-facing directive surface.
- `scripts/proot-setup.sh` is the canonical public installer for the portable Termux backend.
- `scripts/start.sh` is the canonical runtime launcher for Phase 1.
- `scripts/termux_boot.sh` is an optional wrapper for users who later enable Termux:Boot.
- `android-shell/` contains the native Android shell that supervises the localhost backend, foreground lifecycle, wake phrase listening, and root-gated advanced mode toggles.
- `.github/workflows/` provides CI, documentation sync enforcement, and debug-bundle automation.

Workflow actions should stay on supported major versions so runner-runtime changes do not create avoidable CI churn.

## Architectural boundaries that must hold

- `src/mordecai/policy.py`, `src/mordecai/proxy.py`, `src/mordecai/self_improvement.py`, `src/mordecai/config.py`, and `prompts/system_prompt.txt` remain protected from self-modification.
- Core runtime composition and execution surfaces under `mordecai_core/`, `providers/`, and the runtime wiring modules in `src/mordecai/` remain protected from self-modification.
- Outbound networking flows through the safe proxy and allowlist model.
- Runtime failures surface with structured codes instead of free-form exception leakage.
- Tool execution happens through manifests, contexts, and permission checks rather than direct service reach-through.
- High-risk tools must declare confirmation policy, risk level, safe-mode behavior, and sandbox profile.
- Mode A must not advertise Android automation tools unless Android control is explicitly enabled.

## Near-term direction

- stabilize the tool-execution API as the developer and agent execution spine
- freeze the Phase 1 Mode A backend contract before starting APK-shell work
- keep the provider capability matrix honest as more local and cloud backends arrive
- extend trace surfaces into a real operational cockpit
- expand Android-native tool providers without weakening the permission model
- keep self-modification test-gated on every promotion path and rollback-first