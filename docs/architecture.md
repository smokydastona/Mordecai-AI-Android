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

The runtime now includes local voice execution APIs for:

- engine discovery (`GET /api/voice/engines`)
- ecosystem discovery (`GET /api/voice/catalog`)
- text-to-speech synthesis through Piper (`POST /api/voice/synthesize`)
- speech-to-text transcription through Whisper CLI (`POST /api/voice/transcribe`)

These voice operations remain explicit and fail loudly when required binaries or model assets are missing.

The voice layer now also carries a structured catalog of open-source speech repositories grouped by TTS, voice cloning, ASR, pipelines, training frameworks, enhancement, multimodal audio, and master indexes. This keeps model discovery operator-visible and policy-aware: cloning-capable repos can be marked as approval-gated, and only explicitly supported runtimes such as Piper and Whisper are treated as active integrations.

That discovery layer now feeds the local model registry directly for selected phone-safe stacks. The runtime exposes explicit install manifests for `whisper.cpp` and `sherpa-onnx` model packages, policy-sensitive bundles require an operator acknowledgement before the proxy is allowed to download them, and archive-backed manifests now expand into managed setup directories with a machine-readable sherpa manifest instead of remaining opaque downloads.

The voice execution layer now has three explicit offline ASR paths: the existing Whisper CLI route, a `whisper.cpp` route that uses managed ggml model assets plus optional local VAD, and a `sherpa-onnx` route that uses the extracted whisper encoder/decoder/tokens manifest from the managed archive. This keeps execution explicit and inspectable while allowing multiple phone-targeted transcription paths.

The permanent avatar also anchors here as a policy-protected identity surface whose assets and behavior are not mutable through the self-improvement path. The runtime derives its available expressions directly from the protected SVG set in `assets/avatar/`, so identity updates require explicit asset changes rather than silent prompt-only drift.

### 9. Self-modification and operator layer

Candidate proposal, sandbox execution, promotion, rollback, observability, and the human approval path for anything with real impact.

The runtime also persists long-term goals and routine triggers as operator-visible state, keeping task memory explicit instead of hidden in prompt-only context.

Local model profiles are also surfaced as first-class runtime state so operators can inspect configured chat, STT, and TTS backends through the same dashboard and API used for the live system. These profiles are declarative integration targets, not proof that the corresponding model weights are already present on-device.

The runtime also exposes managed local model assets and bundles. Model downloads remain explicit and opt-in, and every redirect target is validated against the outbound allowlist before bytes are written into the models directory.

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

## Deployment contracts

### Mode A contract

Mode A is the portable deployment path that ships today. Its contract is:

- Termux hosts the public install entrypoint.
- `proot-distro` provides the Linux runtime boundary.
- the backend lives under `$HOME/mordecai/backend`
- the runtime environment lives under `$HOME/mordecai/env`
- state, cache, logs, models, and exported runtime contracts live under `$HOME/mordecai/data`
- lifecycle entrypoints live under `$HOME/mordecai/scripts`

Mode A intentionally keeps Android automation and root-only actions off by default. The runtime must remain fully usable even when the phone is non-rooted and only the localhost dashboard plus API are available.

### Mode B contract

Mode B is the advanced-device path for rooted or specially prepared hardware. It extends the same runtime core rather than replacing it. Its contract is:

- Mode A remains the foundation and recovery path.
- root-dependent control is additive, not baseline.
- rooted shell actions stay permission-gated and policy-visible.
- any recovery-tree or Magisk integration must leave a recoverable route back to Mode A behavior.

Mode B must never become a silent bypass around the policy, proxy, provider, or tool-manifest layers.

## Formal runtime contracts

Mordecai now exposes two explicit machine-readable runtime contracts:

- provider registry: `/api/runtime/provider-registry`
- tool manifest: `/api/runtime/tool-manifest`

These contracts are also exportable through `python -m mordecai.runtime_contracts` into the runtime state directory. They are meant to support:

- dashboard and shell introspection
- first-boot verification
- future plugin and extension compatibility checks
- operator-visible debugging without source inspection

The provider registry records which providers exist, whether they are local or remote, which one is currently preferred, and the capability boundaries the runtime will route against.

The tool manifest records the canonical tool name, owning provider, permission requirements, input and output schemas, confirmation policy, sandbox profile, and default execution policy values surfaced by the runtime.

## First-boot flow

Phase 1 now has a formal first-boot verifier in `scripts/first_boot.sh`. That entrypoint exists to turn the install contract into an observable startup contract:

- verify backend and environment layout
- ensure the runtime environment is Linux-hosted rather than Android-native
- initialize git metadata if the portable checkout lacks it
- export provider and tool contracts into state
- start the dashboard runtime
- query the live policy report
- verify the expected proxy allowlist hosts needed by the shipped install path

This keeps first boot explicit and debuggable instead of assuming that a successful installer run means the runtime is operator-ready.