# Mordecai

Mordecai-AI-Android is a modular Android-native AI operating layer focused on automation, hardware integration, hybrid local/cloud routing, and intelligent device control.

This repository is the canonical home of the Galaxy S10e AI OS project. It currently contains the working Mordecai runtime plus the device, sandbox, voice, proxy, and self-modification structure that the broader system will grow into.

Mordecai itself is a policy-bound AI runtime for a repurposed Android device. The current implementation provides a formal assistant identity, a restricted outbound network surface, a dashboard and HTTP API, git-backed backups, Android control hooks, and a sandboxed self-improvement workflow.

## Project hygiene

- `CHANGELOG.md` tracks notable repository changes.
- `README.md`, `docs/`, and `.github/copilot-instructions.md` are treated as first-class project surfaces and must be updated with implementation and workflow changes.
- CI now includes a documentation sync gate that fails when implementation changes are pushed without the changelog and required docs updates.

## What is implemented

- FastAPI dashboard and API surface for chat, status, policy, memory, git state, outbound fetches, web search, GitHub search, Android actions, and self-improvement candidates
- FastAPI dashboard and API surface for chat, status, policy, memory, git state, outbound fetches, web search, GitHub search, Android actions, runtime events, proxy logs, and self-improvement candidates
- Formal Mordecai identity with wake words and personality modes
- Policy engine that protects core safety files, blocks destructive shell patterns, and enforces an outbound domain allowlist
- Safe HTTP client with per-minute request throttling and request logging
- Git integration for local backups and optional pushes
- Self-improvement manager that stages file changes in a sandbox, runs tests, previews diffs, and only applies approved candidates
- Self-improvement manager that stages file changes in a sandbox workspace, runs tests there, supports rollback, previews diffs, and only applies approved candidates
- Resource watchdog that reports CPU and memory usage
- Android control hooks through `adb` for safe allowlisted actions when explicitly enabled
- Canonical architecture foundations for a unified tool registry, replaceable provider contracts, and an observable event bus in `mordecai_core/`
- Structured tool execution engine with runtime context, permission checks, validation, retries, timeouts, cooperative cancellation, and execution telemetry
- Developer trace and capability surfaces for provider routing, tool policy metadata, and runtime event inspection

## Strategic direction

- Mordecai is being positioned as an Android-native control layer, not a generic chat app.
- The strongest differentiation is hardware integration, device automation, controller and HID workflows, and hybrid local/cloud AI routing.
- Architectural growth is anchored on modular interfaces, execution observability, and progressive permission unlocking.

## Project layout

```text
docs/
android/
sandbox/
mordecai_core/
self_mod/
net_proxy/
voice/
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
scripts/start_server.ps1
scripts/termux_boot.sh
tests/
```

## Canonical repo structure

- `docs/` holds high-level architecture, persona, and device setup guidance.
- `android/` is reserved for device-specific operating-system and control notes.
- `sandbox/` contains the Linux bootstrap layer for Termux and proot.
- `mordecai_core/` defines the logical home of the AI runtime while the packaged implementation remains in `src/mordecai/`.
- `self_mod/` documents the self-improvement subsystem and its guardrails.
- `net_proxy/` captures the safe internet boundary and its configuration model.
- `voice/` defines the wake-word, STT, and TTS expansion surface.

## Architecture priorities

- Unified tool registry: self-describing tools with stable contracts and explicit permission requirements.
- Tool execution engine: registry-backed execution IDs, structured failures, retries, and timeout boundaries.
- Event bus: observable execution flow and loose coupling between runtime subsystems.
- Replaceable provider layer: cloud and local providers routed behind stable contracts and a declared capability matrix.
- Reliable Android integration: progressive permissions, defensive automation, and OEM-fragility isolation.
- Structured runtime context: execution metadata, provider state, permission state, and device state travel through a typed execution surface instead of ad hoc dictionaries.
- Developer observability: runtime trace and capability inspection are exposed through the API and dashboard for debugging-first operation.

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

This codebase is designed to run inside the sandboxed Linux layer described in the blueprint, such as Termux plus proot Ubuntu on the target phone. The included shell script is a starting point for bootstrapping that runtime.

## CI and debugging

- GitHub Actions now runs cross-platform install, compile, test, and app-smoke checks through `.github/workflows/ci.yml`.
- GitHub Actions now runs a documentation sync gate before test execution.
- Every CI run uploads debug artifacts including pytest output, JUnit XML, Python version, and `pip freeze`.
- Manual deep triage is available through `.github/workflows/debug-smoke.yml`, which produces a bundled diagnostics artifact.
- Security scanning is handled by `.github/workflows/codeql.yml`.
- GitHub issue templates in `.github/ISSUE_TEMPLATE/` now match Mordecai and are structured around reproducible debugging evidence.

## Reference docs

- `docs/architecture.md`
- `docs/architecture/modular-foundations.md`
- `docs/roadmap/foundation.md`

## Diagnostics surface

- `GET /api/events` returns recent runtime events such as candidate creation, apply, rollback, and proxy activity.
- `GET /api/proxy/logs` returns the outbound request log with allow / deny decisions.
- `GET /api/runtime/trace` returns recent execution and provider-routing events from the modular runtime surface.
- `GET /api/runtime/capabilities` returns the provider capability matrix plus tool permission and sandbox metadata.
- `GET /api/improvement/backups` lists rollback metadata for applied candidates.
- `POST /api/improvement/rollback/{candidate_id}` restores backed-up files for a previously applied candidate.
