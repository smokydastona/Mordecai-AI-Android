# Mordecai Debugging Guide

This guide is the operator-facing reference for debugging Mordecai on a phone, inside the Termux plus `proot-distro` backend, and across the guarded outbound network surface.

## Built-In Diagnostics First

Before reaching for external profilers or Android tracing tools, inspect Mordecai's built-in diagnostics surface:

1. `GET /api/runtime/trace` for recent provider routing, tool execution history, policy audits, request-latency samples, execution timelines, and cached provider-health snapshots.
2. `GET /api/runtime/latency` for percentile summaries and per-path latency rollups when the runtime feels slow but not obviously broken.
3. `GET /api/policy/audits` when a command, URL, file change, or Android action appears blocked and you need the exact policy reason.
4. `GET /api/proxy/logs` with query filters when outbound traffic is failing, rate-limited, or unexpectedly redirected.
5. `GET /api/improvement/candidates/{candidate_id}/test-output` when sandbox candidates fail and the dashboard summary is not enough.
6. `GET /api/android/diagnostics` or `POST /api/android/diagnostics/{category}` on Mode B devices for persisted battery, logcat, process-memory, and thermal captures.

The dashboard now exposes these same surfaces directly through dedicated panels for policy audit, provider health, latency, timelines, filtered proxy activity, Android diagnostics, and candidate test output.

## Top 5 Tools For Mordecai

1. `google/perfetto`
   Best for Android shell startup timing, service churn, wake-phrase latency, overlay jank, and battery-cost investigations on the phone itself.

2. `benfred/py-spy`
   Best for sampling the live Python backend without editing the runtime or restarting it under a profiler.

3. `gaogaotiantian/viztracer`
   Best for deep Python execution traces when a request path is correct but slow or unexpectedly noisy.

4. `mitmproxy/mitmproxy`
   Best for diagnosing guarded outbound requests, redirect chains, model downloads, and API traffic in a controlled development environment.

5. `jlfwong/speedscope`
   Best for reading profiler output once you have a captured trace or flamegraph from backend sampling tools.

## Scenario Matrix

| Scenario | Primary Tool | Secondary Tool | What To Check First |
| --- | --- | --- | --- |
| Backend startup issues | `py-spy` | `strace` | `data/logs/backend.log`, `GET /health`, process tree inside `proot-distro` |
| Battery drain or Android shell churn | `Perfetto` | `adb logcat` | foreground service restarts, wake phrase loops, overlay redraw frequency |
| Slow replies or API latency | `py-spy` | `VizTracer` | provider-routing events, local model availability, recent tool execution history |
| APK install failures | `adb logcat` | `pm install -r` output | release asset URL, package installer prompt path, unknown-sources permissions |
| Model download failures | `mitmproxy` | proxy logs at `GET /api/proxy/logs` | allowlisted host, redirect target, disk space, `data/models` contents |

## Optional Debugging Toolkit

The Phase 1 installer can provision an optional debugging toolkit into the Linux runtime by setting:

```bash
MORDECAI_INSTALL_DEBUG_TOOLKIT=true
```

When enabled, the installer adds:

- Python tools: `py-spy`, `viztracer`, `mitmproxy`
- Linux tools inside `proot-distro`: `procps`, `lsof`, `strace`, `iproute2`, `net-tools`
- an installed-tool manifest at `$HOME/mordecai/tools/debug-toolkit.txt`

This toolkit is intentionally optional because it increases install time and should only be present on devices where you actually need profiling or trace capture.

## Phone Issues

### Android Shell Fails To Launch Or Keeps Restarting

1. Confirm the backend is actually up at `http://127.0.0.1:8000` in the phone browser.
2. Inspect Termux logs:

```bash
tail -n 200 $HOME/mordecai/data/logs/backend.log
```

3. If the shell app is installed but unstable, capture Android logs:

```bash
adb logcat | grep -i mordecai
```

4. Use Perfetto when the issue is timing-related rather than a hard crash.

### Overlay Or Accessibility Problems

1. Check whether the accessibility service is enabled in Android settings.
2. Confirm the shell app still points at the localhost backend contract.
3. Use `adb logcat` first for permission or service binding failures.
4. Use Perfetto when the overlay appears but causes visible jank or stalls the UI.

### APK Install Failures

1. Confirm the release asset URL resolves and the APK was downloaded into `$HOME/mordecai/data/cache`.
2. On rooted phones, rerun:

```bash
su -c "pm install -r $HOME/mordecai/data/cache/android-shell-debug.apk"
```

3. On non-root phones, ensure Android allows the installer prompt to open and that unknown-sources permissions are granted to the package installer path Termux invokes.
4. If installation still fails, collect `adb logcat` while retrying.

## Backend Issues

### Backend Does Not Start

1. Check whether the PID file is stale:

```bash
cat $HOME/mordecai/data/logs/backend.pid
```

2. Check the runtime log:

```bash
tail -n 200 $HOME/mordecai/data/logs/backend.log
```

3. Check the process list inside `proot-distro`:

```bash
proot-distro login ubuntu-24.04 --shared-tmp -- /bin/bash -lc "ps aux | grep uvicorn"
```

4. If it starts and then stalls, sample it:

```bash
proot-distro login ubuntu-24.04 --shared-tmp -- /bin/bash -lc "$HOME/mordecai/env/bin/py-spy top --pid \$(pgrep -f uvicorn)"
```

### Slow Replies

1. Call `GET /api/runtime/trace` and `GET /api/runtime/latency` from the dashboard or curl.
2. Check whether the runtime is waiting on cloud traffic, local model availability, a degraded provider-health snapshot, or a slow tool execution timeline.
3. Use `py-spy` for a quick sample.
4. Use `viztracer` when you need a full request trace:

```bash
proot-distro login ubuntu-24.04 --shared-tmp -- /bin/bash -lc "$HOME/mordecai/env/bin/viztracer -o /tmp/mordecai-trace.json -m uvicorn mordecai.main:app --host 127.0.0.1 --port 8000"
```

Then open the resulting trace in `speedscope` or another compatible viewer.

## Network And Model Download Issues

### Guarded Outbound Requests Fail

1. Check `GET /api/proxy/logs` to see the allow or deny reason, then narrow with query, method, domain, or decision filters.
2. Confirm the target host and any redirect host are both on the allowlist. Managed Hugging Face downloads can currently redirect through `cas-bridge.xethub.hf.co` as well as the direct `huggingface.co` host.
3. Check `GET /api/policy/audits` if the failure reason suggests a policy block rather than a transport or DNS failure.
4. Use `mitmproxy` only in a controlled development environment where rerouting traffic is acceptable.

### Sandbox Candidate Fails Tests

1. Inspect `GET /api/improvement/candidates/{candidate_id}/test-output` or the dashboard candidate test-output panel.
2. Confirm whether the failure came from actual pytest stderr, a timeout, or a missing runtime dependency.
3. Reproduce locally only after the preserved candidate output is no longer sufficient.

### Android Diagnostics On Mode B

1. Start with the dashboard Android diagnostics panel or `POST /api/android/diagnostics/{category}`.
2. Use `battery` for quick power state captures, `logcat` when the shell or accessibility service looks unstable, `process-memory` for allowlisted package memory spikes, and `thermal` when the device appears throttled.
3. Only escalate to `adb logcat`, `Perfetto`, or deeper system tools after the built-in captures stop narrowing the issue.

### Model download fails or stalls

1. Confirm free space under `$HOME/mordecai/data/models` and `$HOME/mordecai/data/cache`.
2. Confirm the matching runtime binaries exist in `$HOME/mordecai/tools/bin` for `llama-cli`, `whisper`, and `piper`.
2. Check the latest proxy log entries for a blocked redirect or rate-limited host. Current managed bundle installs can hop from `huggingface.co` to `cas-bridge.xethub.hf.co` before the asset download starts.
3. Re-run the model installer explicitly:

```bash
proot-distro login ubuntu-24.04 --shared-tmp -- /bin/bash -lc "$HOME/mordecai/env/bin/python -m mordecai.local_models --install-root $HOME/mordecai --install-bundle phone-starter"
```

4. If the failure is intermittent, use `mitmproxy` or the runtime proxy logs to capture the exact redirect chain.

If the asset files exist but the commands themselves are missing, rerun the installer with:

```bash
MORDECAI_INSTALL_LOCAL_MODEL_BINARIES=true bash proot-setup.sh
```

## Quick Command Set

```bash
tail -n 200 $HOME/mordecai/data/logs/backend.log
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/runtime/trace
curl -s http://127.0.0.1:8000/api/runtime/latency
curl -s http://127.0.0.1:8000/api/policy/audits?allowed=false
curl -s http://127.0.0.1:8000/api/proxy/logs
proot-distro login ubuntu-24.04 --shared-tmp -- /bin/bash -lc "$HOME/mordecai/env/bin/py-spy top --pid \$(pgrep -f uvicorn)"
```