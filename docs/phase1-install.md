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
- build and install the default phone-supported local runtime binaries (`llama-cli`, `whisper`, and `piper`) by default
- download and install the recommended phone-sized local model bundle by default
- download the latest published Mordecai Android shell APK and install it automatically when Android permits it

On Android, the install no longer depends on Android-native Python wheels for `psutil` or `pydantic-core`. The backend is installed inside the Linux `proot-distro` environment, and Mordecai still uses a standard-library watchdog fallback when `psutil` is unavailable.

By default, Mordecai now pins its Termux runtime to a generated `ubuntu-24.04` profile backed by Canonical `cloud-images.ubuntu.com` `noble` root tarballs, so the install does not track the moving upstream `ubuntu` alias.

If an earlier failed install already created `$HOME/mordecai/env` from Termux Python, the installer now detects that Android-native virtual environment and rebuilds it inside `proot-distro` automatically.

If the configured `proot-distro` rootfs host still fails, the installer downloads the rootfs itself with `curl --http1.1`, verifies the checksum from the distro plug-in when one is present, and retries `proot-distro` from that local file.
That retry intentionally sets an empty `PD_OVERRIDE_TARBALL_SHA256` because `proot-distro` requires the override variable to exist when a custom tarball URL is supplied.

If you want to override the pinned profile, set `MORDECAI_PROOT_DISTRO` before running the installer. For the bundled Ubuntu 24.04 profile, you can also override `MORDECAI_UBUNTU_24_04_RELEASE` and `MORDECAI_UBUNTU_24_04_BASE_URL` before running `proot-setup.sh`.

The installer now prefetches Mordecai's recommended on-device model bundle by default. Set `MORDECAI_INSTALL_DEFAULT_MODELS=false` before running `proot-setup.sh` if you need to skip that download. The default bundle installs the `Qwen2.5 3B` GGUF chat model and the recommended Piper English voice files into `$HOME/mordecai/data/models`.

The installer now also provisions the default phone-supported local runtime binaries by default. Set `MORDECAI_INSTALL_LOCAL_MODEL_BINARIES=false` before running `proot-setup.sh` if you need to skip that step. This default runtime path installs `openai-whisper`, `piper-tts`, and builds `llama.cpp`, includes `ccache` in the Linux toolchain so the one-command flow avoids the missing-cache warning and reruns rebuild faster, keeps `setuptools` below the current CPU-only `torch` incompatibility ceiling so reruns still pass `pip check` after the local voice stack is installed, and now attempts a targeted `llama-cli` plus `llama-server` build before falling back to a broader upstream build when an older checkout still requires it.

Managed model bundle downloads remain behind the proxy and policy layers, but the signed Hugging Face/Xet query parameters used by those downloads are now treated as download metadata rather than user data, so the installer no longer false-positives on the signed redirect URL while fetching the default bundle.

The installer also downloads the latest published `android-shell-latest` APK release asset by default. On rooted phones it attempts a silent `pm install -r`. On standard phones it launches the normal Android package installer so you can approve the install prompt. Set `MORDECAI_INSTALL_SHELL_APK=false` before running `proot-setup.sh` if you want to skip the shell app install step.

If you want the installer to provision the optional Mordecai debugging toolkit inside the Linux runtime, set `MORDECAI_INSTALL_DEBUG_TOOLKIT=true` before running `proot-setup.sh`. That toolkit installs `py-spy`, `viztracer`, `mitmproxy`, and core Linux debugging utilities such as `strace`, `lsof`, and `procps`.

## 3. Start Mordecai

```bash
$HOME/mordecai/scripts/start.sh
```

Or run the full first-boot verifier instead:

```bash
$HOME/mordecai/scripts/first_boot.sh
```

What this does:

- loads the local `.env`
- exports the Phase 1 Mode A settings
- starts the backend from inside the configured `proot-distro` in the background
- writes the PID file to `data/logs/backend.pid`
- writes runtime output to `data/logs/backend.log`

The first-boot verifier goes further than `start.sh`. It exports `provider-registry.json` and `tool-manifest.json` into `$HOME/mordecai/data/state/contracts/`, saves the live policy report, and verifies the baseline proxy allowlist hosts used by the shipped install path, including the Hugging Face Xet bridge host `cas-bridge.xethub.hf.co` that current managed model bundle downloads can redirect through.

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
- if the default local models were downloaded but `whisper`, `piper`, or `llama-cli` still appear missing, rerun the installer with `MORDECAI_INSTALL_LOCAL_MODEL_BINARIES=true` and inspect `$HOME/mordecai/tools/local-model-runtime.txt`
- if `proot-distro` fails to fetch a rootfs archive for the pinned `ubuntu-24.04` profile, confirm `cloud-images.ubuntu.com` is reachable or override `MORDECAI_UBUNTU_24_04_BASE_URL` before rerunning the installer
- if the dashboard does not load, confirm the service is bound to `127.0.0.1` and that the port in `.env` matches the URL you opened