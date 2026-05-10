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

## Preferred Full-Capability Runtime

For the most capable local deployment, prefer a rooted Android VM or Linux chroot hosting:

- Termux
- `proot-distro` Ubuntu
- the Mordecai backend under the Linux environment
- Linux-hosted AI runtimes such as Whisper, Piper, and related model tooling

That path keeps the runtime in a Linux userland with root-like flexibility for package management and runtime tooling, while still letting the Android shell supervise the localhost backend from the Android side.

The repository does not auto-provision a rooted Android VM from this workspace. The supported contract here is still the Termux plus `proot-distro` installer path and the Android shell supervision layer above it.

## Phase 1 Setup Path

Phase 1 is the standard portable backend path for supported phones.

The installer treats the `llama.cpp` CLI as a compatibility surface instead of assuming a single upstream target name. During local model runtime setup it builds the repository defaults, prefers `build/bin/llama-cli`, accepts `llama-run` or the older `main` when needed, and links the detected binary to Mordecai's stable `tools/bin/llama-cli` path. If the default build omits those front-ends, the installer makes one explicit `llama-cli` target build attempt before failing.

The installer is incremental by default, but it now also supports `MORDECAI_FORCE_REINSTALL=true` for a fresh runtime rebuild that preserves user data. That path removes only the backend checkout, runtime environment, copied scripts, and managed tool checkout under the install root, then rebuilds them while keeping models, state, logs, and caches intact.

To keep `openai-whisper` CPU-safe on the Linux runtime used by the portable installer, the bootstrap preinstalls CPU-only PyTorch before installing the Whisper package itself. That avoids unsupported CUDA/NVIDIA dependency chains in the portable runtime, including ARM/ARM64 Termux plus proot environments where NVIDIA CUDA wheels are not applicable.

It also performs explicit post-install verification before reporting success: the Python dependency graph is checked with `pip check`, the core Mordecai runtime modules are imported in the Linux environment, the installed Whisper stack is checked to confirm it is not CUDA-linked, local runtime build tools and CLIs are verified, and the default phone-starter bundle files are checked on disk when model installation is enabled.

On reruns, the installer now recreates missing standard runtime subdirectories automatically and attempts an in-place repair of a broken `tools/llama.cpp` checkout before asking you to use the heavier force-reinstall path.

It now applies the same repair model to the backend checkout: an invalid or incomplete `backend/` work tree is removed and recloned automatically instead of forcing a manual cleanup step.

After provisioning finishes, the installer runs a backend smoke check by reusing an already-running backend when one exists, otherwise starting the shipped service once, probing `http://127.0.0.1:<port>/api/status`, asserting the runtime provider-registry, tool-manifest, and voice-engine APIs return the expected contract shape, verifying the managed local-runtime commands are available on `PATH` when enabled, and stopping the service only if the smoke check started it. The installer writes a JSON verification report under `data/logs/install-verification-report.json`; that artifact includes a UTC timestamp, the installer version, the checkout commit, and on failure the last few lines of `data/logs/backend.log`.

The installer also treats the Android shell APK as an update surface instead of blindly reinstalling it. On reruns it queries the installed package version first, compares it to the downloaded APK version when APK metadata inspection is available, falls back to APK hash comparison when needed, and skips the install prompt when the downloaded APK is unchanged.

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