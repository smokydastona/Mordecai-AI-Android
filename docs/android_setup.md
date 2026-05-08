# Android Setup

This document describes the generic Android device setup path for Mordecai across supported phones.

For the advanced reference-device path, use `docs/s10e-setup.md`. For the portable backend install contract, use `docs/phase1-install.md`.

## Goals

- keep the phone recoverable
- keep the Mordecai backend local-first and policy-bound
- support Phase 1 Mode A installs on more than one Android device family
- preserve a clear upgrade path to the native shell and later advanced-device features

## Baseline Requirements

- Android phone with enough free storage for the backend, environment, logs, and model caches
- Developer Options enabled
- USB debugging available for host-assisted setup and recovery
- Termux installed from a trusted source
- working network access for initial package and repository bootstrap

## Recommended Preparation

1. Update the phone to a stable, supportable Android build.
2. Enable Developer Options and USB debugging.
3. Confirm the device can be recovered through normal OEM flashing or recovery methods before enabling deeper automation.
4. Install Termux and update its package index.
5. Decide whether the phone will remain in Mode A or later graduate to rooted advanced-mode use.

## Phase 1 Setup Path

Phase 1 is the standard portable backend path for supported phones.

Use the canonical installer from Termux:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/smokydastona/Mordecai-AI-Android/main/scripts/proot-setup.sh)
```

This provisions the stable `$HOME/mordecai` layout:

- `backend/`
- `env/`
- `data/`
- `scripts/`

Start the backend with:

```bash
$HOME/mordecai/scripts/start.sh
```

## Native Shell Path

The native Android shell in `android-shell/` supervises the localhost backend from Android.

Use it when you want:

- a foreground service to keep supervision explicit
- a WebView shell over the local dashboard
- wake phrase listening on the device
- rooted advanced-mode toggles that stay behind explicit gating

The shell does not replace the backend policy layer. It supervises the existing localhost service contract.

## Safety And Recovery Rules

- keep outbound networking behind the Mordecai proxy and allowlist model
- do not enable Android automation unless the runtime config explicitly allows it
- prefer Mode A on generic phones unless you have a tested recovery path
- do not treat root as required for baseline deployment

## Related Docs

- `docs/phase1-install.md`
- `docs/modeA-vs-modeB.md`
- `docs/android-shell.md`
- `docs/s10e-setup.md`