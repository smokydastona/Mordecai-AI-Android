# Copilot Instructions — Mordecai

This repository is a **policy-bound AI runtime** for a repurposed Android device.

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
   - `README.md`
   - `prompts/system_prompt.txt` when identity or directives change
   - `.github/*` when workflows, templates, or debugging processes change

3) Re-validate after fixes
   - Re-run diagnostics.
   - Re-run the same focused executable check.

4) Keep the repo shippable
   - Do not commit generated state from `.mordecai/`, `.pytest_cache/`, `.venv/`, or `*.egg-info/`.
   - Do not leave broken workflows in `.github/workflows/`.

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

- Android control changes (`src/mordecai/android_control.py`)
  - Confirm unsafe commands remain blocked by policy.
  - Confirm package allowlists still apply.

## CI-first default

- Treat GitHub Actions as the authoritative clean build.
- If CI fails, inspect logs, reproduce locally when possible, and fix the root cause before moving on.
- Preserve debugging artifacts on failure when workflows support uploads.

## Common commands

- Install: `python -m pip install -e .[dev]`
- Test: `.venv/Scripts/python.exe -m pytest -q`
- Run app: `./scripts/start_server.ps1`
- Direct app server: `.venv/Scripts/python.exe -m uvicorn mordecai.main:app --reload`

