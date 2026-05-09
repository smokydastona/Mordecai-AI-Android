# Mordecai

Mordecai-AI-Android is a modular Android-native AI operating layer focused on automation, hardware integration, hybrid local/cloud routing, and intelligent device control across supported Android phones.

This repository is the canonical home of the Mordecai Android runtime project. It currently contains the working Mordecai runtime plus the device, sandbox, voice, proxy, and self-modification structure that the broader multi-phone system will grow into.

Mordecai itself is a policy-bound AI runtime for Android phones. The current implementation provides a formal assistant identity, a restricted outbound network surface, a dashboard and HTTP API, git-backed backups, Android control hooks, a sandboxed self-improvement workflow, and a Phase 1 Termux installer for portable Mode A deployment.

## Project hygiene

- `CHANGELOG.md` tracks notable repository changes.
- `README.md`, `docs/`, and `.github/copilot-instructions.md` are treated as first-class project surfaces and must be updated with implementation and workflow changes.
- CI now includes a documentation sync gate that fails when implementation changes are pushed without the changelog and required docs updates.

## What is implemented

- FastAPI dashboard and API surface for chat, status, policy, memory, git state, outbound fetches, web search, GitHub search, runtime events, proxy logs, and self-improvement candidates
- Formal Mordecai identity with wake words and personality modes
- Policy engine that protects core safety files, blocks destructive shell patterns, and enforces an outbound domain allowlist
- Safe HTTP client with per-minute request throttling and request logging
- Git integration for local backups and optional pushes
- Self-improvement manager that stages file changes in a sandbox workspace, runs tests there, supports rollback, previews diffs, and only applies approved candidates
- Self-improvement perimeter with protected-path enforcement, hidden-persistence diff filters, sandboxed test gating, and rollback snapshots
- Resource watchdog that reports CPU and memory usage
- Android control hooks through `adb` for safe allowlisted actions when explicitly enabled
- Canonical architecture foundations for a unified tool registry, replaceable provider contracts, and an observable event bus in `mordecai_core/`
- Structured tool execution engine with runtime context, permission checks, validation, retries, timeouts, cooperative cancellation, and execution telemetry
- Developer trace and capability surfaces for provider routing, tool policy metadata, and runtime event inspection
- Persisted execution history and an operator-facing dashboard tool runner for direct invocation of registered tools
- Phase 1 Termux installer and lifecycle scripts for portable Mode A deployment under `$HOME/mordecai`
- Native Android shell app with a WebView dashboard, foreground supervision service, wake-phrase listening, Termux command bridge, and root-gated advanced mode controls
- Android shell voice command loop with wake phrase, speech capture, backend chat dispatch, spoken replies, notification action entrypoint, and quick-settings tile activation
- Android shell accessibility service with lock-screen overlay feedback, accessibility onboarding actions, and overlay-backed voice command delegation
- Accessibility overlay now supports a restricted local action set for back, home, notifications, quick settings, recents, and a center-screen tap without bypassing the backend policy surface
- Android shell accessibility resource config now uses the platform-correct `android:accessibilityFlags` attribute so CI Android resource linking succeeds
- Permanent avatar system with immutable old-man emotion frames, asset-driven SVG discovery, backend emotion selection, and dashboard rendering
- Local dashboard memory browser for recent conversation inspection
- Persisted long-term goals and daily routines surfaced through API and dashboard panels
- Local model registry is now exposed through the runtime API and capabilities dashboard, including Whisper, Piper, cloud, and local chat profiles

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

On Android and Termux, the installer now prepares the runtime inside a `proot-distro` Ubuntu layer instead of relying on Android-native Python packaging. The runtime also falls back to a standard-library resource watchdog when `psutil` is unavailable.

If a previous failed Termux-native install already created `$HOME/mordecai/env`, rerunning the installer now detects that Android-native virtual environment and rebuilds it inside the Linux `proot-distro` layer automatically.

The installer forces `curl` to HTTP/1.1 for `proot-distro` rootfs downloads, which avoids the TLS negotiation failure some Termux environments hit against the default rootfs host.

If the default `proot-distro` rootfs download host still fails, the installer retries the distro fetch from the corresponding GitHub release tarball automatically.
The fallback also exports an empty `PD_OVERRIDE_TARBALL_SHA256`, which is required by `proot-distro` when overriding the tarball URL.

Install from Termux with one command:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/smokydastona/Mordecai-AI-Android/main/scripts/proot-setup.sh)
```

Then start the backend:

```bash
$HOME/mordecai/scripts/start.sh
```

This install flow creates:

- `$HOME/mordecai/backend`
- `$HOME/mordecai/env`
- `$HOME/mordecai/data`
- `$HOME/mordecai/scripts`

The virtual environment is created and used inside the Linux `proot-distro` layer, while the checked-out files and runtime state stay under `$HOME/mordecai`.

Phase 1 runs only on `127.0.0.1` by default and does not expose Android automation, daemon mode, or other Mode B-only behavior.

## Important operating constraints

- Core policy modules are protected from self-modification.
- Git pushes are disabled unless `MORDECAI_ALLOW_GIT_PUSH=true`.
- Android control is disabled unless `MORDECAI_ENABLE_ANDROID_CONTROL=true`.
- Outbound networking is restricted to the configured allowlist in `config.py` or environment overrides.

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

## CI and debugging

- GitHub Actions now runs cross-platform install, compile, test, and app-smoke checks through `.github/workflows/ci.yml`.
- GitHub Actions now also builds the native Android shell debug APK through the checked-in Gradle wrapper and uploads the APK artifact.
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
