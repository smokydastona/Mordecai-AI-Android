# Mode A Vs Mode B

Mordecai now has two planned deployment modes.

## Mode A

Mode A is the portable Android backend delivered through Termux.

### Mode A includes

- localhost FastAPI server
- dashboard and API
- native Android shell supervision through the `android-shell/` app module
- policy-bound outbound web access through the proxy
- local git backup support with push disabled by default
- the existing reversible self-improvement surface subject to the current policy protections

### Mode A excludes

- Android automation
- `adb`-driven control features
- daemon mode
- root-only behaviors
- APK-specific service orchestration

Mode A is the default runtime mode shipped by the Phase 1 installer.

## Mode B

Mode B is the future advanced-device mode for rooted or specially configured phones.

### Mode B may include later

- deeper device automation
- broadened long-running service behavior
- rooted-device integrations
- expanded Android shell controls once rooted-device policy and automation paths are verified

Mode B is not part of Phase 1 and must remain explicitly gated.

## Current Enforcement

- `MORDECAI_MODE=mode-a` is the default
- Android control remains disabled unless `MORDECAI_ENABLE_ANDROID_CONTROL=true`
- advanced self-improvement and daemon mode remain disabled unless later phases explicitly enable them
- the runtime tool registry hides Android control tools in Mode A
- the Android shell only enables advanced-mode toggles when root is available on the device

## Installation paths

### Mode A install path

Mode A is the only public one-command install path today.

Prerequisites:

- Termux installed on the phone
- outbound access to GitHub, Hugging Face, and the pinned Ubuntu cloud-image host
- enough storage for the backend, Linux runtime, and optional model assets

Install sequence:

1. Run `bash <(curl -fsSL https://raw.githubusercontent.com/smokydastona/Mordecai-AI-Android/main/scripts/proot-setup.sh)` from Termux.
2. Run `$HOME/mordecai/scripts/first_boot.sh` to verify the runtime contract, export the provider and tool manifests, and start the dashboard.
3. Open `http://127.0.0.1:8000` from the device browser or Android shell.

Mode A is the correct path for:

- non-rooted phones
- initial install validation
- portable backend debugging
- local voice and model runtime bring-up

### Mode B install path

Mode B is a manual advanced-device path, not a public one-command bootstrap.

Prerequisites:

- a supported rooted or specially prepared phone
- validated recovery path back to a clean bootable state
- explicit operator intent to enable rooted-device behavior
- device-specific setup such as Magisk, recovery-tree data capture, and trusted adb access where required

Install sequence:

1. Complete the Mode A install and first-boot verification first.
2. Apply the rooted-device preparation documented in `docs/mode-b-automation.md`.
3. Enable the required runtime flags only after the device-side control path has been validated.
4. Verify that rooted actions appear only when Mode B gating is explicitly enabled.

Mode B is the correct path for:

- Galaxy S10e reference-device work
- rooted automation experiments
- recovery-tree verification and deeper device state capture

## Decision rule

If the user is asking for a portable install, local dashboard, voice, local models, or safe API access, the answer is Mode A.

If the user is asking for rooted control, Magisk-backed automation, recovery-tree state capture, or advanced-device experimentation, the answer starts with Mode A as the base and then layers in Mode B explicitly.