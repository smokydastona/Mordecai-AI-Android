# Mordecai AI OS Architecture

Mordecai-AI-Android is the canonical repository for the Galaxy S10e AI OS project. The repository is organized around a layered model so the physical phone, sandboxed runtime, policy engine, and assistant behavior remain separable and debuggable.

## Eight Layers

1. Device layer
   The Samsung Galaxy S10e hardware, radios, sensors, battery management, and physical recovery surface.

2. Android OS layer
   The phone operating system, ideally a debloated LineageOS-style base with explicit control over updates, radios, and developer access.

3. Root and control layer
   Optional Magisk-style elevation, guarded ADB access, and device automation hooks. This layer must stay opt-in and recoverable.

4. Sandbox layer
   The Termux plus proot Linux environment where Python services, model runtimes, and experiments execute without directly mutating the base OS.

5. Mordecai runtime layer
   The active FastAPI runtime and orchestration code currently implemented in `src/mordecai/`. This includes chat orchestration, policy enforcement, network proxying, git backup, dashboard serving, and self-improvement flow control.

6. Safety and policy layer
   Protected paths, command guards, outbound allowlists, rate limits, and rollback mechanisms. This is the hard boundary that keeps experimentation from escaping into unsafe control.

7. Model and voice layer
   Cloud or local model routing, future STT and TTS pipelines, wake-word handling, and persona-consistent response generation.

8. Self-improvement and operator layer
   Candidate changes, test-gated promotion, rollback, observability, and the human approval path for any high-impact modification.

## Current Mapping In This Repo

- `src/mordecai/` holds the working runtime implementation.
- `tests/` validates API behavior, policy enforcement, provider routing, and sandboxed self-improvement.
- `prompts/system_prompt.txt` defines the active assistant identity.
- `scripts/termux_boot.sh` bootstraps the Linux runtime inside the phone-side sandbox.
- `.github/workflows/` provides CI, CodeQL, and debug-bundle automation.

## Canonical Direction

The top-level directories `android/`, `sandbox/`, `mordecai_core/`, `self_mod/`, `net_proxy/`, and `voice/` are the long-term project compartments for the S10e AI OS. They document and stage the next layer of work without forcing a disruptive source-code move before the runtime is ready for it.