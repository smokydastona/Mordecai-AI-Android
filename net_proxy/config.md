# Proxy Configuration

This document explains the current configuration surface for Mordecai's guarded outbound network layer.

## Source Of Truth

The repository configuration file is `net_proxy/config.yaml`.

The active runtime enforcement is implemented in:

- `src/mordecai/proxy.py`
- `src/mordecai/policy.py`
- `src/mordecai/config.py`

## Current Configuration Shape

`config.yaml` currently defines three groups:

- `allowed_domains`
- `limits`
- `logging`

## Allowed Domains

`allowed_domains` is the explicit outbound allowlist for approved hosts.

Current examples include:

- model providers such as `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com`, and `openrouter.ai`
- search and code-search hosts such as `api.duckduckgo.com`, `duckduckgo.com`, `html.duckduckgo.com`, `api.github.com`, and `github.com`
- package and documentation hosts such as `pypi.org`, `docs.python.org`, `huggingface.co`, and the Hugging Face Xet bridge host `cas-bridge.xethub.hf.co` used by managed model downloads

Requests outside this allowlist must not be treated as normal outbound traffic.

## Limits

`limits` currently controls:

- `max_requests_per_minute`
- `timeout_seconds`

These values define the baseline request throttle and the maximum request lifetime for guarded outbound calls.

## Logging

`logging` controls whether proxy request history is written and where it is stored.

The current default destination is `.mordecai/proxy_log.json`.

## Operational Rules

- outbound requests should flow through the proxy layer rather than ad hoc direct HTTP clients
- allowlist changes are policy changes and should be reviewed with the same care as other safety-bound runtime changes
- failures should surface explicitly to operators and API clients instead of silently falling back to direct networking

## Change Guidance

When updating `config.yaml`:

1. keep the allowlist as small as possible
2. preserve enough logging to explain permit and deny decisions
3. confirm tests still cover proxy allowlist and rate-limit behavior
4. update `README.md`, `CHANGELOG.md`, and relevant docs when the network surface changes