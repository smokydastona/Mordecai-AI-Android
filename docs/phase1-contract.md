# Phase 1 Contract

Phase 1 defines the portable backend contract for Mordecai on Android phones running Termux.

## Goal

On any supported Android phone, the operator installs Termux, runs one command, and gets:

- Mordecai installed into a predictable layout under `$HOME/mordecai`
- Python dependencies resolved into a dedicated virtual environment
- Mode A configuration written into a local `.env`
- FastAPI running on `127.0.0.1` only
- the dashboard reachable on `http://127.0.0.1:8000`
- no Android automation, daemon mode, or other Mode B features exposed by default

## Prerequisites

- Android 10 or newer
- current Termux from F-Droid or GitHub releases
- at least 2 GB of free storage for the backend, logs, cache, and future model assets
- outbound internet access for the first install
- no root required

## Canonical Installer Command

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/smokydastona/Mordecai-AI-Android/main/scripts/proot-setup.sh)
```

## Canonical Layout

```text
$HOME/mordecai/
  .env
  backend/
  env/
  data/
    cache/
    logs/
    models/
    state/
  scripts/
    proot-setup.sh
    start.sh
    stop.sh
    termux_boot.sh
    update.sh
```

## Expected End State

- `backend/` contains the checked-out Mordecai repository
- `env/` contains the Python virtual environment used for runtime execution
- `data/state/` contains runtime persistence, including backups and candidate sandboxes
- `data/logs/backend.log` contains server startup and runtime output
- `scripts/start.sh` starts the backend idempotently and writes a PID file to `data/logs/backend.pid`
- `scripts/stop.sh` stops the running backend cleanly when the PID file is valid
- `scripts/update.sh` pulls the backend forward and refreshes the installed scripts

## Supported In Phase 1

- localhost-only FastAPI server
- dashboard and API access on the phone
- proxy-mediated web fetch and web search
- local git backup flows with push still disabled by default
- local and cloud provider routing through the existing policy and proxy layers

## Explicitly Not Supported In Phase 1

- Android automation via `adb`
- root-only behaviors
- background daemon mode beyond the explicit Termux process started by `start.sh`
- APK shell packaging
- automatic startup without operator opt-in
- widened network policy beyond the configured allowlist

## Acceptance Criteria

- one-command install completes on a clean Termux environment
- `scripts/start.sh` can be run twice without starting duplicate servers
- the dashboard loads on `http://127.0.0.1:8000`
- logs are written to `data/logs/backend.log`
- Mode B-only controls remain unavailable in Mode A