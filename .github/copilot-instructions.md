# Copilot Instructions — Mordecai

This repository is a **policy-bound AI runtime** for supported Android phones, with the Galaxy S10e kept as an advanced reference profile.

It provides:

- A FastAPI dashboard and API
- A guarded outbound network surface
- Sandbox-first self-improvement candidates
- Git-backed backups and reversibility
- Optional Android automation hooks behind explicit configuration

Non-negotiables:

- Do not bypass the policy layer for network, git, Android control, or self-improvement features.
- Do not add hidden persistence, hidden startup behavior, or silent self-replication.
- Do not let self-improvement modify safety, policy, config, or override mechanisms.
- Prefer transparent failure reporting over silent fallbacks.

## Where things live

- `android-shell/` — native Android shell app and supervision layer
- `src/mordecai/` — runtime code
- `tests/` — validation for API, policy, and future runtime behavior
- `prompts/` — system prompt and identity configuration
- `scripts/` — local startup and target-device bootstrap helpers
- `.mordecai/` — runtime state, candidate sandboxes, backups, request logs

## Runtime constraints

- Self-improvement must remain reversible and test-gated.
- Android control must remain opt-in and allowlist based.
- Outbound networking must flow through the safe proxy / allowlist model.
- Git pushes must remain disabled by default unless explicitly enabled.

## Implementation Standards

- Build complete features only. No placeholders, TODOs, or stub handlers.
- Keep behavior explicit and debuggable.
- Every new feature should have a validation path: tests, smoke checks, or both.
- Every failure path should preserve enough state to explain what happened.

## Workflow After Every Code Change

1) Run diagnostics first
   - Check workspace diagnostics for touched files.
   - Run the narrowest executable validation for the touched slice.

2) Update connected docs and templates
  - `CHANGELOG.md`
   - `README.md`
  - `docs/*` for architecture, setup, persona, or operational surface changes
   - `prompts/system_prompt.txt` when identity or directives change
   - `.github/*` when workflows, templates, or debugging processes change

3) Re-validate after fixes
   - Re-run diagnostics.
   - Re-run the same focused executable check.

4) Keep the repo shippable
   - Do not commit generated state from `.mordecai/`, `.pytest_cache/`, `.venv/`, or `*.egg-info/`.
   - Do not leave broken workflows in `.github/workflows/`.
  - Do not push implementation changes without updating `CHANGELOG.md`, `README.md`, and relevant files under `docs/`.

## Push Discipline

- Every completed pushed change must update `CHANGELOG.md`.
- Every completed pushed change that affects runtime behavior, tooling, workflows, setup, or architecture must update `README.md` and at least one relevant file under `docs/`.
- Workflow or repository process changes must also update `.github/copilot-instructions.md`.
- CI enforces this through `scripts/check_docs_sync.py` and the `Documentation Sync Gate` job in `.github/workflows/ci.yml`.
- The CI workflow also republishes a rolling `android-shell-latest` GitHub release asset from `main` so Termux installs have a stable APK URL; keep the release step aligned with the staged shell artifact name if the Android module output changes.
- The CI release-publication job must resolve the downloaded Android shell APK path from the artifact directory before invoking `gh release create`, because `download-artifact` can preserve upload subdirectories.
- The Android shell CI build must keep stamping monotonic APK version metadata into the Gradle build from workflow inputs so phone-side APK update checks can trust `versionCode` and `versionName` across pushes.

## Impact Radius Checklists

- Policy changes (`src/mordecai/policy.py`, `src/mordecai/config.py`)
  - Confirm protected paths still cover safety-critical modules.
  - Confirm allowed-domain behavior is documented and tested.

- Proxy / network changes (`src/mordecai/proxy.py`, `src/mordecai/providers.py`)
  - Confirm outbound requests still respect allowlists and rate limits.
  - Confirm errors are logged and surfaced to API clients.

- Self-improvement changes (`src/mordecai/self_improvement.py`, `tests/**`)
  - Confirm candidates remain sandboxed.
  - Confirm protected paths cannot be applied.
  - Confirm test execution still gates live promotion.

- API / dashboard changes (`src/mordecai/main.py`, `src/mordecai/dashboard.py`, `src/mordecai/models.py`)
  - Confirm endpoints still serialize correctly.
  - Confirm the dashboard reflects current API fields.
  - Confirm tests cover changed routes or contracts.

- Android shell changes (`android-shell/**`)
  - Confirm the shell still targets the localhost backend contract.
  - Confirm wake-phrase and foreground-service behavior remain explicit and debuggable.
  - Confirm advanced-mode controls stay gated behind root detection and do not bypass backend policy.

- Android control changes (`src/mordecai/android_control.py`)
  - Confirm unsafe commands remain blocked by policy.
  - Confirm package allowlists still apply.

## CI-first default

- Treat GitHub Actions as the authoritative clean build.
- If CI fails, inspect logs, reproduce locally when possible, and fix the root cause before moving on.
- Preserve debugging artifacts on failure when workflows support uploads.
- Keep CI compile and package validation aligned with the full shipped Python package surface, not just `src/` and `tests/`.
- Prefer first-party or current major-version GitHub Actions when they remove fragile shell glue, especially around Android SDK setup and license handling.
- For cross-platform wrapper scripts, preserve executable bits in git and add defensive CI bootstrap steps when Windows-authored commits can strip them.
- Keep workflow actions on supported major versions before deprecation windows force upgrades under incident conditions.

## Common commands

- Install: `python -m pip install -e .[dev]`
- Test: `.venv/Scripts/python.exe -m pytest -q`
- Run app: `./scripts/start_server.ps1`
- Direct app server: `.venv/Scripts/python.exe -m uvicorn mordecai.main:app --reload`
- Build Android shell: `./gradlew.bat :android-shell:assembleDebug`

