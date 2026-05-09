# Phase 1 Install

This is the supported install flow for the portable Mode A backend.

## 1. Install Termux

- install Termux from F-Droid or the official GitHub releases
- open Termux once and allow its first-run storage and package initialization to complete

## 2. Run The Installer

Paste this into Termux:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/smokydastona/Mordecai-AI-Android/main/scripts/proot-setup.sh)
```

The installer will:

- install `git`, `curl`, and `proot-distro` in Termux
- install or reuse the pinned `ubuntu-24.04` `proot-distro` runtime layer
- clone or update Mordecai into `$HOME/mordecai/backend`
- create a Python environment in `$HOME/mordecai/env` from inside the Linux layer
- install the backend package into that Linux-hosted environment
- create `$HOME/mordecai/data` and `$HOME/mordecai/scripts`
- write a local `$HOME/mordecai/.env` scaffold if one does not already exist

On Android, the install no longer depends on Android-native Python wheels for `psutil` or `pydantic-core`. The backend is installed inside the Linux `proot-distro` environment, and Mordecai still uses a standard-library watchdog fallback when `psutil` is unavailable.

By default, Mordecai now pins its Termux runtime to a generated `ubuntu-24.04` profile so the install does not track the moving upstream `ubuntu` alias.

If an earlier failed install already created `$HOME/mordecai/env` from Termux Python, the installer now detects that Android-native virtual environment and rebuilds it inside `proot-distro` automatically.

If the configured `proot-distro` rootfs host still fails, the installer downloads the rootfs itself with `curl --http1.1`, verifies the checksum from the distro plug-in when one is present, and retries `proot-distro` from that local file.
That retry intentionally sets an empty `PD_OVERRIDE_TARBALL_SHA256` because `proot-distro` requires the override variable to exist when a custom tarball URL is supplied.

If you want to override the pinned profile, set `MORDECAI_PROOT_DISTRO` before running the installer. For the bundled Ubuntu 24.04 profile, you can also override `MORDECAI_UBUNTU_24_04_RELEASE` and `MORDECAI_UBUNTU_24_04_BASE_URL` before running `proot-setup.sh`.

## 3. Start Mordecai

```bash
$HOME/mordecai/scripts/start.sh
```

What this does:

- loads the local `.env`
- exports the Phase 1 Mode A settings
- starts the backend from inside the configured `proot-distro` in the background
- writes the PID file to `data/logs/backend.pid`
- writes runtime output to `data/logs/backend.log`

## 4. Open The Dashboard

From a browser on the phone, open:

```text
http://127.0.0.1:8000
```

If you change the port in `$HOME/mordecai/.env`, use that port instead.

## 5. Stop Or Update The Backend

Stop the running backend:

```bash
$HOME/mordecai/scripts/stop.sh
```

Update the backend checkout and refresh the installed scripts:

```bash
$HOME/mordecai/scripts/update.sh
```

## What You Should See

- the dashboard home page renders
- `GET /health` returns `status: ok`
- `data/logs/backend.log` exists and grows when the backend handles requests
- Android automation stays unavailable unless a later phase explicitly enables it

## Troubleshooting

- if `start.sh` says the backend is already running, inspect `data/logs/backend.pid` and `data/logs/backend.log`
- if the install fails during package setup, run `pkg update -y` and retry the installer
- if `pip` reports Android-native build failures such as `psutil` or `pydantic-core`, update the backend checkout and rerun the installer so the `proot-distro` install path is picked up
- if `proot-distro` fails to fetch a rootfs archive for the pinned `ubuntu-24.04` profile, confirm the Ubuntu Base mirror is reachable or override `MORDECAI_UBUNTU_24_04_BASE_URL` before rerunning the installer
- if the dashboard does not load, confirm the service is bound to `127.0.0.1` and that the port in `.env` matches the URL you opened