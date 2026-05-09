# Changelog

## Unreleased

### Added

- **Voice Model Ecosystem Index**: Added a curated open-source AI voice model index to `voice/README.md` covering TTS, voice-cloning, and audio-generation repositories (Awesome AI Voice, WhisperSpeech, Kokoro, XTTS v2, Bark, Piper, Fish Speech, Dia, F5-TTS, Parler-TTS, OmniVoice), plus practical integration guidance for Mordecai.
- **Mode B Ecosystem Resources**: Comprehensive GitHub index added to `docs/mode-b-automation.md` cataloging 20+ device tree, kernel, recovery, rooting, and flashing tool repositories. Includes critical path (ExtremeXT device tree + Magisk + TWRP), alternatives (SHRP, KernelSU, Heimdall), and reference resources (security research, TrustZone).
- **Mode B Rooted Shell Automation**: Extended `AndroidController` with rooted shell actions (getprop, settings queries, dumpsys, process queries) gated behind `enable_mode_b=True` configuration flag. All Mode B commands require explicit policy enforcement and operator approval. Added comprehensive input validation and command injection prevention.
- **Mode B Recovery State API**: New `GET /api/android/mode-b/state` endpoint queries recovery-layer initialization state written by custom device tree during boot. Returns bootloader status, ro.secure, build fingerprint, system-as-root detection, and Magisk presence.
- **Mode B Action Endpoint**: New `POST /api/android/mode-b/action` endpoint executes privileged rooted shell commands with policy enforcement. Actions include: `mode_b_get_property`, `mode_b_get_setting`, `mode_b_query_battery`, `mode_b_query_display`, `mode_b_query_processes`.
- **Mode B Documentation**: New `docs/mode-b-automation.md` provides comprehensive two-tier automation architecture guide covering rooted Magisk layer and custom TWRP recovery tree integration for Galaxy S10e reference device. Includes safety boundaries, operational checklists, and build instructions for custom device tree.
- **Config Extension**: Added `enable_mode_b` boolean setting to control Mode B automation access at runtime.

### Changed

- `AndroidController.perform()` now logs errors and provides detailed failure context for debugging.
- Input validation now enforces coordinate bounds (0-2000), swipe duration limits (100-5000ms), and character whitelisting for text input.

- enforce self-improvement test gating on every apply path, including manual promotion of sandbox candidates
- expand self-improvement protected-path coverage to core execution and provider surfaces
- surface state store corruption and save failures as explicit runtime errors instead of silent fallbacks
- decouple runtime composition from the FastAPI entrypoint through a dedicated bootstrap module
- compile all shipped Python packages and build wheel plus sdist artifacts in CI

All notable changes to Mordecai-AI-Android are documented in this file.

## 2026-05-08 (Continued)

### Fixed

- **CRITICAL**: Self-improvement test runner now captures detailed error information instead of silently marking tests as failed. Added comprehensive exception handling, timeout detection (30s), and environment validation to `_run_tests()`.
- **CRITICAL**: StateStore now uses atomic file writes with temporary file + rename pattern to prevent data loss under concurrent access (TOCTOU race condition fixed).
- **HIGH**: The `android-shell-latest` release job now stages the built APK to a deterministic artifact path and checks out repository context before invoking `gh`, fixing the failing release publication step in CI.
- **HIGH**: Follow-up docs sync now explicitly records the Android shell rolling-release path-resolution workflow behavior so `.github`-only CI fixes satisfy the repository documentation gate.
- **CRITICAL**: Avatar emotion classification now uses comprehensive token scoring across all emotions instead of early return pattern that fell back to neutral 30% of the time.
- **HIGH**: Workspace directory is now automatically created during config initialization instead of failing with validation error.
- **HIGH**: Exception handling in FastAPI endpoints now properly preserves and re-raises system exceptions (KeyboardInterrupt, SystemExit) instead of masking them as HTTP 500 errors.
- **HIGH**: Policy engine's `protected_paths` now uses immutable `frozenset` instead of mutable `set` to prevent runtime modification.
- **HIGH**: OpenAI provider configuration now validates all three required fields (api_key, base_url, model) at startup and logs detailed warning about missing fields instead of silent fallback.
- **MEDIUM**: Git subprocess calls now use `errors='replace'` to handle binary output gracefully instead of crashing on decode errors.
- **MEDIUM**: LocalModelService now returns consistent boolean type for `model_available` field instead of mixed bool/None.

## 2026-05-08

### Added

- Android-safe watchdog fallback that uses the standard library for resource reporting when `psutil` is unavailable.
- Phase 1 installer now provisions and uses a `proot-distro` Ubuntu runtime layer for backend dependency installation and execution on Android.
- Phase 1 installer now replaces a previously created Android-native virtual environment with a `proot-distro` Linux virtual environment automatically.
- Phase 1 installer now retries `proot-distro` rootfs installs from a locally downloaded rootfs archive when the default host fails.
- Phase 1 installer now sets `PD_OVERRIDE_TARBALL_SHA256` during tarball URL overrides so `proot-distro` fallback installs do not abort under `set -u`.
- Phase 1 installer now falls back by downloading the rootfs archive itself with `curl --http1.1`, verifying the plugin SHA-256, and handing `proot-distro` a local `file://` tarball when the default host fails.
- Phase 1 installer now generates and defaults to a pinned `ubuntu-24.04` `proot-distro` profile so phone installs do not follow the moving upstream Ubuntu alias.
- The pinned `ubuntu-24.04` profile now follows Canonical `cloud-images.ubuntu.com/noble/<serial>` root tarballs with known arm64 and armhf checksums instead of a generic Ubuntu Base URL pattern.
- Local model registry now includes default `llama.cpp` and `llamafile` chat profiles, and docs now clarify that Mordecai does not bundle model weights onto the phone by default.
- Mordecai now ships a policy-gated managed local model asset layer, including a `phone-starter` bundle for Qwen2.5 3B GGUF plus Piper voice files, dashboard/API installation controls, and an opt-in Termux installer hook via `MORDECAI_INSTALL_DEFAULT_MODELS=true`.
- The Termux installer now downloads the default local model bundle automatically, downloads the rolling `android-shell-latest` APK release asset automatically, and installs the shell app through silent root install or the Android package installer when running on standard phones.
- Mordecai now includes a dedicated debugging guide with a top-5-by-scenario matrix for phone, backend, and network failures, and the Termux installer now supports an optional `MORDECAI_INSTALL_DEBUG_TOOLKIT=true` path that installs backend and network debugging tools into the Linux runtime.
- The one-command Termux installer now provisions the default phone-supported local model runtime binaries by default, building `llama.cpp` and installing `openai-whisper` plus `piper-tts` so the bundled phone-starter assets are actually runnable after install.

- Permanent avatar assets under `assets/avatar/` plus backend avatar state and dashboard rendering.
- Android shell voice command loop with one-shot speech capture, backend chat dispatch, TTS reply playback, notification action entrypoint, and quick-settings tile support.
- Dashboard memory browser panel backed by the existing `/api/memory` endpoint.
- Persisted goals and routines with API endpoints, status counters, and dashboard panels.
- Local model registry exposure through `/api/local-models` and runtime capabilities, with dashboard visibility for configured Whisper, Piper, cloud, and local chat profiles.
- Android accessibility service, lock-screen accessibility overlay, setup actions, and overlay-backed voice command delegation in the shell app.
- Restricted accessibility action set for overlay buttons and local voice commands, covering back, home, recents, notifications, quick settings, and center-screen tap.
- Fixed Android shell accessibility resource linking by replacing `android:flags` with `android:accessibilityFlags` in the accessibility service config.
- Fixed Android shell rolling release publication by resolving the downloaded APK path dynamically before calling `gh release create`.
- Accessibility overlay is now rendered as a compact top-corner card with constrained width and shorter content so it no longer blocks a large part of the phone screen.
- Policy-enforced self-improvement diff filters for hidden persistence and boot-time autostart patterns.
- Generic Android setup guidance in `docs/android_setup.md` and proxy configuration guidance in `net_proxy/config.md`.
- Native Android shell app under `android-shell/` with a WebView dashboard, foreground supervision service, Termux command bridge, wake-phrase listening, and root-gated advanced mode controls.
- Checked-in Gradle wrapper and root Android build files so the native shell can build from a clean repository checkout.
- Phase 1 portable Termux backend contract docs in `docs/phase1-contract.md`, `docs/phase1-install.md`, and `docs/modeA-vs-modeB.md`.
- Canonical Termux lifecycle scripts for install, start, stop, update, and optional boot integration under `scripts/`.

### Changed

- Packaging now installs `psutil` only on supported non-Android platforms, allowing the Termux Phase 1 backend install to complete on Android.
- Phase 1 Termux lifecycle scripts now launch and update the backend through the Linux `proot-distro` layer instead of Android-native Python.
- Phase 1 Termux lifecycle scripts now default to the pinned `ubuntu-24.04` profile, while still allowing `MORDECAI_PROOT_DISTRO` overrides for other distros.
- README now documents automatic replacement of a previously created Android-native virtual environment during Phase 1 reinstalls.

- Avatar profile wiring now discovers every SVG under `assets/avatar/`, keeps a stable preferred display order, and exposes the full asset set through `/api/avatar` instead of a fixed seven-frame list.
- Project positioning now frames Mordecai as a multi-phone Android runtime, with the Galaxy S10e retained as an advanced reference device instead of the implied default target.
- Documentation sync rules now treat the Android shell module and root Gradle files as first-class implementation surface.
- CI and debug-smoke workflows now build the Android shell debug APK through the Gradle wrapper and publish Android build artifacts.
- Android workflows now use `android-actions/setup-android@v4` package installation directly instead of a manual `sdkmanager --licenses` pipe that failed under GitHub Actions `pipefail`.
- `gradlew` is now tracked as executable and Linux workflows apply `chmod +x ./gradlew` before Android builds, fixing wrapper permission failures on GitHub runners.
- The Android shell module now includes `androidx.lifecycle:lifecycle-service`, fixing `LifecycleService` and service-scope compilation failures in CI.
- CI now uses `actions/upload-artifact@v7` and `github/codeql-action@v4`, and the CodeQL workflow opts into Node 24 to remove current action deprecation warnings.
- Runtime settings now define explicit install, data, log, host, port, mode, and advanced-capability flags instead of relying on the process working directory alone.
- Mode A now binds the backend to `127.0.0.1` by default and hides Android control tools from the registry unless explicitly enabled.
- `sandbox/proot-setup.sh` now delegates to the public installer in `scripts/proot-setup.sh`.
- README, architecture docs, sandbox docs, S10e setup docs, and `.env.example` now reflect the Phase 1 Termux contract.

### Added

- Observable architecture foundations for a unified event bus, self-describing tool registry, and replaceable provider contracts.
- New architecture and roadmap documents for the modular Android-native operating-layer direction.
- Structured tool execution engine with runtime context, permission verification, validation, retries, timeout handling, cooperative cancellation, and execution telemetry.
- Runtime trace and capability-inspection endpoints, including provider capability matrices and tool sandbox metadata.
- First concrete tool-provider package for Android control, git operations, local LLM execution, and cloud LLM execution.
- Dedicated self-mod enforcement tests for policy protection, tool contracts, sandbox apply/rollback, and proxy allowlists.
- Tool-execution API endpoint with structured runtime failure responses.
- High-risk shell and accessibility providers with the same execution taxonomy as the rest of the runtime.
- Persisted tool execution history surfaced through runtime trace responses and the dashboard.

### Changed

- README positioning now emphasizes Mordecai as an Android-native AI operating layer rather than a generic assistant.
- Runtime components now expose direct tool execution and capability discovery from the modular runtime layer.
- Provider routing now selects against declared provider capabilities and emits observable routing events.
- `docs/architecture.md` and new `docs/persona.md` now act as the architectural and behavioral constitution for Mordecai.
- The dashboard now includes a direct tool runner and execution-history surface for operator-driven debugging.

### Added

- Initial Mordecai policy-bound FastAPI runtime with guarded outbound networking, dashboard, git backup, Android control hooks, and sandboxed self-improvement.
- Runtime diagnostics including events, proxy logs, improvement backups, and rollback support.
- GitHub Actions CI, CodeQL, and debug-bundle workflows with artifact upload.
- Canonical S10e AI OS repository structure: `docs/`, `android/`, `sandbox/`, `mordecai_core/`, `self_mod/`, `net_proxy/`, and `voice/`.
- Canonical executable modules for `mordecai_core`, `self_mod`, `net_proxy`, and `voice`.
- Android ADB preflight script, sandbox Dockerfile and environment manifests, and validation coverage for the canonical structure.

### Changed

- Repository README now reflects the repo as the canonical home of the Galaxy S10e AI OS project.
- Packaging now exports the canonical top-level packages and includes YAML-backed proxy configuration.
- CI now runs on pushes to `main`, CodeQL supports manual dispatch, and the debug smoke bundle runs on pushes as well.

### Quality

- Full local test suite passing: `16 passed`.