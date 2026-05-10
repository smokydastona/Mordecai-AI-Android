# Mordecai

Mordecai-AI-Android is a modular Android-native AI operating layer focused on automation, hardware integration, hybrid local/cloud routing, and intelligent device control across supported Android phones.

This repository is the canonical home of the Mordecai Android runtime project. It currently contains the working Mordecai runtime plus the device, sandbox, voice, proxy, and self-modification structure that the broader multi-phone system will grow into.

Mordecai itself is a policy-bound AI runtime for Android phones. The current implementation provides a formal assistant identity, a restricted outbound network surface, a dashboard and HTTP API, git-backed backups, Android control hooks, a sandboxed self-improvement workflow, and a Phase 1 Termux installer for portable Mode A deployment.

For the most capable local deployment path, the intended target remains a rooted Android VM or Linux chroot hosting Termux plus `proot-distro` Ubuntu, so Mordecai can run Linux-hosted AI runtimes such as Whisper and Piper while the Android shell supervises the localhost backend.

## Project hygiene

- `CHANGELOG.md` tracks notable repository changes.
- `README.md`, `docs/`, and `.github/copilot-instructions.md` are treated as first-class project surfaces and must be updated with implementation and workflow changes.
- CI now includes a documentation sync gate that fails when implementation changes are pushed without the changelog and required docs updates.
- Recent CI workflow fixes also require matching README, changelog, and docs updates even when the code change is only in `.github/`, including the Android shell rolling-release publication path handling.

## What is implemented

- FastAPI dashboard and API surface for chat, status, policy, memory, git state, outbound fetches, web search, GitHub search, runtime events, proxy logs, and self-improvement candidates
- Structured long-term memory for preferences, projects, tasks, facts, contacts, and episodic context, with explicit save/search endpoints and retrieval-backed chat context construction
- Structured planning and agent execution on top of the tool registry, with plan generation, tool execution, and context assembly from both memory retrieval and the latest Android perception snapshot
- Operator-facing dashboard surfaces for live perception state, planner inspection/execution, and active voice-session inspection and event injection
- Planner history is now persisted and operator-visible through the dashboard and API, with per-record selection in the dashboard for full inspection after the latest response scrolls away, while the permanent avatar remains part of the operator surface
- Formal Mordecai identity with wake words and personality modes
- Policy engine that protects core safety files and execution surfaces, blocks destructive shell patterns, and enforces an outbound domain allowlist
- Outbound policy now also blocks commerce/checkout endpoints and personal-data exfiltration patterns, even on otherwise allowlisted hosts
- Safe HTTP client with per-minute request throttling and request logging
- Git integration for local backups and optional pushes
- Self-improvement manager that stages file changes in a sandbox workspace, runs tests there, supports rollback, previews diffs, and only applies candidates whose tests passed
- Self-improvement perimeter with protected-path enforcement, hidden-persistence diff filters, sandboxed test gating, and rollback snapshots
- Resource watchdog that reports CPU and memory usage
- Android control hooks through `adb` for safe allowlisted actions when explicitly enabled
- Direct Android screen injection for `tap`, `swipe`, and `type` is now policy-blocked so Mordecai cannot automate purchases or enter personal/payment data into arbitrary apps
- Structured Android perception ingestion for app package, activity, visible text, clickable actions, clipboard hints, notifications, and parsed accessibility UI dumps so planning can reason over current screen context
- Perception snapshots now also preserve focused-node metadata and notification action metadata when the shell producer can collect them
- Canonical architecture foundations for a unified tool registry, replaceable provider contracts, and an observable event bus in `mordecai_core/`
- Structured tool execution engine with runtime context, permission checks, validation, retries, timeouts, cooperative cancellation, and execution telemetry
- Developer trace and capability surfaces for provider routing, tool policy metadata, and runtime event inspection
- Formal runtime contract exports for providers and tools through `/api/runtime/provider-registry`, `/api/runtime/tool-manifest`, and `python -m mordecai.runtime_contracts`
- Persisted execution history and an operator-facing dashboard tool runner for direct invocation of registered tools
- Phase 1 Termux installer and lifecycle scripts for portable Mode A deployment under `$HOME/mordecai`
- Native Android shell app with a WebView dashboard, foreground supervision service, wake-phrase listening, Termux command bridge, and root-gated advanced mode controls
- The Android shell now includes a first-run welcome screen, explicit permission review popups, and a settings cog that opens a dedicated in-app settings screen with a permissions/status summary plus cloud/local AI provider controls, so shell setup stays guided instead of exposing all operator controls at launch
- The Android shell voice and settings Kotlin surfaces are kept aligned with CI compile validation, including explicit wake-phrase callback wiring, single-source partial transcript handling, and a single settings companion block for AI profile preferences
- Android shell voice command loop with wake phrase, speech capture, backend chat dispatch, spoken replies, notification action entrypoint, and quick-settings tile activation
- Android shell now streams continuous accessibility-derived perception snapshots and wake/command transcript events into the localhost backend so planning and memory can use live device context instead of only manual API posts
- Android shell accessibility service with lock-screen overlay feedback, accessibility onboarding actions, and overlay-backed voice command delegation
- Accessibility overlay now supports a restricted local action set for back, home, notifications, quick settings, recents, and a center-screen tap without bypassing the backend policy surface
- Accessibility overlay now renders as a compact top-corner card so lock-screen feedback stays visible without covering a large part of the phone screen
- Android shell accessibility resource config now uses the platform-correct `android:accessibilityFlags` attribute so CI Android resource linking succeeds
- Android shell release publication now resolves the downloaded artifact path dynamically before invoking `gh release create`, so the rolling `android-shell-latest` asset survives artifact-directory nesting in GitHub Actions
- Permanent avatar system with immutable old-man emotion frames, asset-driven SVG discovery, backend emotion selection, and dashboard rendering
- Local dashboard memory browser for recent conversation inspection, plus API-visible long-term memory records and ranked retrieval for assistant context reuse
- Persisted long-term goals and daily routines surfaced through API and dashboard panels
- Local model registry is now exposed through the runtime API and capabilities dashboard, including Whisper, Piper, cloud, Ollama, `llama.cpp`, and `llamafile` chat profiles
- Voice runtime APIs now support local engine discovery, Piper-based speech synthesis, and Whisper CLI transcription with explicit error reporting when binaries or model files are missing
- Background voice sessions now support wake-word detection, streaming partial/final transcript events, interruption handling, planner-backed command execution, and persisted session state through `/api/voice/sessions`
- The dashboard now exposes those voice sessions directly so operators can start sessions, inspect active state, and inject transcript events without leaving the console
- Voice ecosystem discovery is now exposed through `GET /api/voice/catalog` and the dashboard, with categorized open-source repositories spanning TTS, cloning, ASR, pipelines, training toolkits, enhancement, and multimodal audio research
- Voice catalog discovery now supports filtering by query, category, runtime fit, and runtime-supported status so operators can narrow the ecosystem view to phone-safe or currently integrated stacks
- The dashboard model installer now shows bundle metadata and supports explicit approval acknowledgement for gated voice bundles before install
- The dashboard now includes operator-facing transcription controls so local audio files can be run through `whisper`, `whisper.cpp`, or `sherpa-onnx` directly from the console
- Mode B rooted shell automation for Galaxy S10e reference device, with two-tier control: Magisk-based input injection and settings queries, plus custom TWRP recovery tree integration for boot-time state capture and device verification
- Mode B API endpoints for rooted actions: input tap/swipe, property queries, settings get, dumpsys battery/display, and process queries, all gated behind `enable_mode_b=True` configuration and policy enforcement
- Mode B recovery state API queries boot-time device state including bootloader status, ROM fingerprint, system-as-root detection, and Magisk presence
- Mode B comprehensive documentation at `docs/mode-b-automation.md` covering two-tier architecture, safe defaults, operational checklists, and custom device tree build instructions for S10e

## Reliability and Security

- Self-improvement test execution now includes comprehensive error handling, timeouts, and detailed failure reporting
- State store uses atomic file operations and now raises explicit failures when persistence or state reads break
- Long-term memory remains operator-visible and stored in explicit state files instead of hidden prompt-only context, so remembered preferences and project context can be inspected, searched, and audited
- Planner and voice-session state are also explicit and inspectable: perception snapshots, generated plans, and background voice session status are surfaced through typed APIs rather than hidden in transient prompt glue
- Policy engine uses immutable collections to prevent runtime tampering
- Configuration validation detects incomplete optional configs and logs warnings
- Exception handling preserves system interrupts for graceful shutdown
- Git operations handle binary output and encoding errors gracefully
- Runtime composition now resolves through a dedicated bootstrap module so the core execution layer no longer depends on the FastAPI entrypoint for wiring

## Strategic direction

- Mordecai is being positioned as an Android-native control layer for supported Android phones, not a generic chat app.
- The strongest differentiation is hardware integration, device automation, controller and HID workflows, and hybrid local/cloud AI routing.
- Architectural growth is anchored on modular interfaces, execution observability, and progressive permission unlocking.

## Project layout

```text
docs/
android/
android-shell/
sandbox/
mordecai_core/
self_mod/
net_proxy/
voice/
providers/
src/mordecai/
  agent.py
  android_control.py
  config.py
  dashboard.py
  git_tools.py
  main.py
  models.py
  policy.py
  providers.py
  proxy.py
  self_improvement.py
  store.py
  voice.py
  watchdog.py
prompts/system_prompt.txt
scripts/proot-setup.sh
scripts/first_boot.sh
scripts/start.sh
scripts/stop.sh
scripts/start_server.ps1
scripts/termux_boot.sh
scripts/update.sh
tests/
```

## Canonical repo structure

- `docs/` holds high-level architecture, persona, and device setup guidance.
- `android/` is reserved for device-specific operating-system and control notes.
- `android-shell/` contains the native Android app shell that supervises the portable localhost backend.
- `sandbox/` contains compatibility wrappers and Linux bootstrap notes for Termux and proot.
- `mordecai_core/` defines the logical home of the AI runtime while the packaged implementation remains in `src/mordecai/`.
- `providers/` holds concrete tool-provider implementations that bind safe runtime services into the unified execution engine.
- `self_mod/` documents the self-improvement subsystem and its guardrails.
- `net_proxy/` captures the safe internet boundary and its configuration model.
- `voice/` defines the wake-word, STT, and TTS expansion surface.
- `scripts/` contains the supported Phase 1 installer and lifecycle entry points.

## Architecture priorities

- Unified tool registry: self-describing tools with stable contracts and explicit permission requirements.
- Tool execution engine: registry-backed execution IDs, structured failures, retries, and timeout boundaries.
- High-risk execution providers: shell and accessibility-class tooling now share the same permission, sandbox, and failure taxonomy.
- Event bus: observable execution flow and loose coupling between runtime subsystems.
- Replaceable provider layer: cloud and local providers routed behind stable contracts and a declared capability matrix.
- Reliable Android integration: progressive permissions, defensive automation, and OEM-fragility isolation.
- Structured runtime context: execution metadata, provider state, permission state, and device state travel through a typed execution surface instead of ad hoc dictionaries.
- Developer observability: runtime trace and capability inspection are exposed through the API and dashboard for debugging-first operation.
- Operator control surface: the dashboard can invoke registered tools directly and review persisted execution history across restarts.

## Quick start

1. Create or reuse the workspace virtual environment.
2. Install the project in editable mode:

```powershell
python -m pip install -e .[dev]
```

3. Copy `.env.example` to `.env` and fill in any optional values.
4. Start the API:

```powershell
./scripts/start_server.ps1
```

5. Open `http://127.0.0.1:8000`.

## Android shell build

The repository now includes a checked-in Gradle wrapper, so the native shell can be built from a clean checkout without a system Gradle install.

1. Install JDK 17.
2. Install Android SDK platform 35, build-tools 35.0.0, and platform-tools.
3. Set `ANDROID_SDK_ROOT` or open the project in Android Studio.
4. Build the debug APK:

```powershell
.\gradlew.bat :android-shell:assembleDebug
```

On Unix-like shells:

```bash
./gradlew :android-shell:assembleDebug
```

The output APK is written under `android-shell/build/outputs/apk/debug/`.

## Phase 1 phone install

Phase 1 is the portable Mode A backend contract for Termux-based Android installs.

On Android and Termux, the installer now prepares the runtime inside a pinned `ubuntu-24.04` `proot-distro` layer instead of relying on Android-native Python packaging or the moving upstream `ubuntu` alias. The runtime also falls back to a standard-library resource watchdog when `psutil` is unavailable.

If a previous failed Termux-native install already created `$HOME/mordecai/env`, rerunning the installer now detects that Android-native virtual environment and rebuilds it inside the Linux `proot-distro` layer automatically.

The pinned `ubuntu-24.04` profile is generated locally by the installer and targets Canonical `cloud-images.ubuntu.com` `noble` root tarballs instead of the current upstream `ubuntu` alias, which now tracks Ubuntu 25.10.

If the configured `proot-distro` rootfs download host fails, the installer reads the distro plug-in URL directly, downloads the rootfs itself with `curl --http1.1`, verifies the plug-in SHA-256 when one is present, and retries `proot-distro` from that local archive.
The fallback still exports an empty `PD_OVERRIDE_TARBALL_SHA256`, which is required by `proot-distro` when overriding the tarball URL.

Install from Termux with one command:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/smokydastona/Mordecai-AI-Android/main/scripts/proot-setup.sh)
```

Then start the backend:

```bash
$HOME/mordecai/scripts/start.sh
```

Or use the first-boot verifier to export the runtime contracts, save the live policy report, verify the baseline proxy allowlist, and start the dashboard in one pass:

```bash
$HOME/mordecai/scripts/first_boot.sh
```

This install flow creates:

- `$HOME/mordecai/backend`
- `$HOME/mordecai/env`
- `$HOME/mordecai/data`
- `$HOME/mordecai/scripts`

The virtual environment is created and used inside the Linux `proot-distro` layer, while the checked-out files and runtime state stay under `$HOME/mordecai`.

If you need a different distro alias, set `MORDECAI_PROOT_DISTRO` before running the installer. If you need to retarget the pinned Ubuntu profile to a different `noble` image serial or mirror, set `MORDECAI_UBUNTU_24_04_RELEASE` and optionally `MORDECAI_UBUNTU_24_04_BASE_URL` before running `proot-setup.sh`.

Phase 1 runs only on `127.0.0.1` by default and does not expose Android automation, daemon mode, or other Mode B-only behavior.

Mode B remains an explicit advanced-device path layered on top of a working Mode A install. The install split and operational expectations are documented in `docs/modeA-vs-modeB.md`.

## Important operating constraints

- Core policy modules are protected from self-modification.
- Git pushes are disabled unless `MORDECAI_ALLOW_GIT_PUSH=true`.
- Android control is disabled unless `MORDECAI_ENABLE_ANDROID_CONTROL=true`.
- Outbound networking is restricted to the configured allowlist in `config.py` or environment overrides.

## On-device models

Mordecai does not silently ship a bundled LLM, Whisper checkpoint, Piper voice, or wake-word neural model onto the phone by default.

What exists in the repository today is a local model registry and integration surface:

- `mordecai-cloud` uses the configured OpenAI-compatible backend and downloads nothing onto the phone by itself
- `ollama-local` expects an Ollama-managed local chat model if you install Ollama separately
- `llama.cpp-qwen2.5-3b` expects a `Qwen2.5-3B-Instruct-Q4_K_M.gguf` file under Mordecai's models directory and a `llama.cpp` CLI such as `llama-cli`
- `llamafile-gemma-3-1b` expects a `gemma-3-1b-it-Q4_K_M.llamafile` executable model under Mordecai's models directory
- `whisper-cli` expects the Whisper CLI and whatever Whisper checkpoint you choose to download separately
- `piper-tts` expects a Piper voice model and config that you place under the models directory or reference directly

The runtime now includes a managed `phone-starter` local model bundle that installs:

- `Qwen2.5-3B-Instruct-Q4_K_M.gguf` for the `llama.cpp-qwen2.5-3b` profile
- `en_US-lessac-medium.onnx` and `en_US-lessac-medium.onnx.json` for the `piper-tts` profile

You can install that bundle explicitly from the runtime environment with:

```bash
python -m mordecai.local_models --install-root "$HOME/mordecai" --install-bundle phone-starter
```

The phone installer now downloads that bundle automatically by default. Set `MORDECAI_INSTALL_DEFAULT_MODELS=false` before running `scripts/proot-setup.sh` if you want to skip the model download.

On a phone install, Mordecai creates the models directory under `$HOME/mordecai/data/models` and now populates it with the default bundle unless you disable that step.

The one-command phone installer now also provisions the default phone-supported local runtime binaries by default:

- `llama.cpp` built locally to provide `llama-cli`
- `openai-whisper` to provide the `whisper` CLI
- `piper-tts` to provide the `piper` CLI

The runtime also exposes a policy-aware voice ecosystem catalog at `GET /api/voice/catalog`. That catalog does not auto-install or auto-enable upstream projects; it exists to make operator-visible routing, evaluation, and future explicit integrations possible without hiding model choices behind prompt state.

The local model registry now also promotes additional explicit voice integrations beyond the Piper and Whisper CLI defaults, including `whisper.cpp` and `sherpa-onnx` profiles plus phone-oriented install bundles. Some bundles are policy-gated and require explicit operator acknowledgement before download. Archive-based bundles now extract into a managed helper directory, emit a machine-readable sherpa manifest, and write a setup note so they become runnable preparation paths instead of download-only blobs.

`POST /api/voice/transcribe` now supports an explicit `provider` selection. The default remains `whisper`, `whisper.cpp` is available as a second offline transcription path when the `whisper-cli` binary and managed ggml model are present, and `sherpa-onnx` is available as a third offline path when the managed archive has been extracted and the `sherpa-onnx-offline` binary is present.

Set `MORDECAI_INSTALL_LOCAL_MODEL_BINARIES=false` before running `scripts/proot-setup.sh` if you want to skip that provisioning step. The optional `ollama-local` and `llamafile-gemma-3-1b` profiles remain external integrations and are not part of the one-command phone bootstrap.

## Cloud model configuration

Mordecai supports OpenAI-compatible chat providers through the same safe proxy used for other outbound traffic.

Set these environment values in `.env`:

```text
MORDECAI_OPENAI_BASE_URL=https://api.openai.com/v1
MORDECAI_OPENAI_API_KEY=your-key
MORDECAI_OPENAI_MODEL=gpt-4o-mini
```

Notes:

- Requests still flow through the allowlist and request-rate controls in the proxy layer.
- The default allowlist includes common model API hosts such as `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com`, and `openrouter.ai`.
- If `MORDECAI_OPENAI_*` values are unset, Mordecai falls back to the built-in rule-based provider.

## Android deployment notes

This codebase is designed to run inside the sandboxed Linux layer described in the blueprint, such as Termux plus proot Ubuntu on the target phone. `scripts/proot-setup.sh` is now the canonical public installer entry point for the portable Phase 1 backend, while `sandbox/proot-setup.sh` remains a compatibility wrapper for older references. The native shell app in `android-shell/` supervises that localhost backend from Android.

The Phase 1 installer now also downloads the latest published Android shell APK release asset by default. On rooted devices it attempts a silent `pm install -r`; otherwise it launches the normal Android package installer through `termux-open` so the shell app can be installed from the same Termux flow.

The installer can also add an optional debugging toolkit when you set `MORDECAI_INSTALL_DEBUG_TOOLKIT=true` before running `scripts/proot-setup.sh`. That toolkit installs `py-spy`, `viztracer`, and `mitmproxy` into the Linux runtime plus core Linux debugging utilities such as `strace`, `lsof`, and `procps`.

## CI and debugging

- GitHub Actions now runs cross-platform install, compile, test, and app-smoke checks through `.github/workflows/ci.yml`.
- GitHub Actions now compiles every shipped Python package surface and builds wheel plus sdist artifacts during CI.
- GitHub Actions now also builds the native Android shell debug APK through the checked-in Gradle wrapper and uploads the APK artifact.
- GitHub Actions now also republishes a rolling `android-shell-latest` release asset on pushes to `main`, staging the built APK to a stable `android-shell-debug.apk` filename before publication so the phone installer has a fixed download URL.
- A Mordecai-specific debugging guide now lives in `docs/debugging-guide.md`, including a top-5-by-scenario matrix for startup issues, battery drain, slow replies, APK install failures, and model download failures.
- Android SDK provisioning in CI now uses `android-actions/setup-android@v4` package installation directly, which avoids the fragile manual `sdkmanager --licenses` pipe.
- Linux CI jobs now also force `chmod +x ./gradlew`, and the repository tracks `gradlew` as executable so wrapper-based Android builds survive Windows-authored commits.
- The Android shell module now declares the AndroidX lifecycle service dependency required by the foreground supervision service.
- Workflow dependencies now track current major versions for artifact uploads and CodeQL so Node 24 migration warnings do not accumulate in CI.
- GitHub Actions now runs a documentation sync gate before test execution.
- Every CI run uploads debug artifacts including pytest output, JUnit XML, Python version, and `pip freeze`.
- Manual deep triage is available through `.github/workflows/debug-smoke.yml`, which now also captures Android build output and uploads the debug APK when available.
- Security scanning is handled by `.github/workflows/codeql.yml`.
- GitHub issue templates in `.github/ISSUE_TEMPLATE/` now match Mordecai and are structured around reproducible debugging evidence.

## Reference docs

- `docs/architecture.md`
- `docs/android_setup.md`
- `docs/android-shell.md`
- `docs/debugging-guide.md`
- `docs/phase1-contract.md`
- `docs/phase1-install.md`
- `docs/modeA-vs-modeB.md`
- `docs/persona.md`
- `docs/mordecai_persona.md`
- `docs/architecture/modular-foundations.md`
- `docs/roadmap/foundation.md`
- `net_proxy/config.md`

## Diagnostics surface

- `GET /api/events` returns recent runtime events such as candidate creation, apply, rollback, and proxy activity.
- `GET /api/proxy/logs` returns the outbound request log with allow / deny decisions.
- `GET /api/runtime/trace` returns recent execution and provider-routing events from the modular runtime surface.
- `GET /api/runtime/trace` also returns persisted tool execution history so completed tool chains survive process restarts.
- `GET /api/runtime/capabilities` returns the provider capability matrix plus tool permission and sandbox metadata.
- `GET /api/avatar` returns the immutable avatar style, current emotion, and all protected frame assets.
- `POST /api/tools/execute` is the operator and agent execution spine for registered tools.
- `GET /api/improvement/backups` lists rollback metadata for applied candidates.
- `POST /api/improvement/rollback/{candidate_id}` restores backed-up files for a previously applied candidate.
