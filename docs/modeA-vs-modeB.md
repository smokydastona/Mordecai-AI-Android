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