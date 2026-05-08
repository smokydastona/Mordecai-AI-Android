# Mordecai

Mordecai is a policy-bound AI runtime for a repurposed Android device. This repository implements the service layer described in the design blueprint: a formal assistant identity, a restricted outbound network surface, a dashboard and HTTP API, git-backed backups, Android control hooks, and a sandboxed self-improvement workflow.

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

## Project layout

```text
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
- Every CI run uploads debug artifacts including pytest output, JUnit XML, Python version, and `pip freeze`.
- Manual deep triage is available through `.github/workflows/debug-smoke.yml`, which produces a bundled diagnostics artifact.
- Security scanning is handled by `.github/workflows/codeql.yml`.
- GitHub issue templates in `.github/ISSUE_TEMPLATE/` now match Mordecai and are structured around reproducible debugging evidence.

## Diagnostics surface

- `GET /api/events` returns recent runtime events such as candidate creation, apply, rollback, and proxy activity.
- `GET /api/proxy/logs` returns the outbound request log with allow / deny decisions.
- `GET /api/improvement/backups` lists rollback metadata for applied candidates.
- `POST /api/improvement/rollback/{candidate_id}` restores backed-up files for a previously applied candidate.
