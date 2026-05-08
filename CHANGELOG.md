# Changelog

All notable changes to Mordecai-AI-Android are documented in this file.

## 2026-05-08

### Added

- Native Android shell app under `android-shell/` with a WebView dashboard, foreground supervision service, Termux command bridge, wake-phrase listening, and root-gated advanced mode controls.
- Checked-in Gradle wrapper and root Android build files so the native shell can build from a clean repository checkout.
- Phase 1 portable Termux backend contract docs in `docs/phase1-contract.md`, `docs/phase1-install.md`, and `docs/modeA-vs-modeB.md`.
- Canonical Termux lifecycle scripts for install, start, stop, update, and optional boot integration under `scripts/`.

### Changed

- Project positioning now frames Mordecai as a multi-phone Android runtime, with the Galaxy S10e retained as an advanced reference device instead of the implied default target.
- Documentation sync rules now treat the Android shell module and root Gradle files as first-class implementation surface.
- CI and debug-smoke workflows now build the Android shell debug APK through the Gradle wrapper and publish Android build artifacts.
- Android workflows now use `android-actions/setup-android@v4` package installation directly instead of a manual `sdkmanager --licenses` pipe that failed under GitHub Actions `pipefail`.
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