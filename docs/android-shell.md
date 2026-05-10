# Android Shell

The Android shell is the native app layer that supervises the portable Termux-backed Mordecai runtime.

## Scope

- native Android entrypoint for Phase 2
- WebView shell over the localhost dashboard
- foreground service for runtime supervision
- wake-phrase listening through Android speech recognition
- Termux command bridge for install, start, stop, and update operations
- root-gated advanced mode toggles for Mode B enablement

## Current Implementation

- `android-shell/` is a standalone Android application module built with Kotlin and Gradle
- `MainActivity` provides install, start, stop, update, and refresh controls, now behind a first-run welcome flow with the shell configuration moved into a dedicated in-app settings screen opened from the settings cog
- `SettingsActivity` now provides a permissions/status summary card, permission review actions, shell toggles, backend URL and wake-phrase configuration, and AI routing controls for cloud and local OpenAI-compatible endpoints
- `MordecaiShellService` polls the localhost backend and can auto-start it through Termux when offline
- `WakePhraseManager` listens for the configured wake phrase and triggers backend startup when it is heard
- `SpeechCommandProcessor` now emits partial transcript updates while capturing the next spoken command and streams the final command into the backend voice-session API instead of only dispatching through chat
- `SpeechOutput` now reports playback completion back into the backend voice-session state so background sessions can move out of speaking mode explicitly
- `TermuxCommandClient` invokes the Phase 1 scripts through the Termux run-command API
- `RootDetector` gates advanced mode toggles so Mode B activation remains explicit
- `MordecaiTileService` gives the shell a quick-settings entrypoint for voice command activation
- `MordecaiAccessibilityService` exposes a lock-screen-safe accessibility overlay, can own voice command capture when accessibility mode is enabled, and now streams continuous perception snapshots to the backend from active windows and notification events
- `MordecaiOverlay` renders avatar feedback and backend replies through `TYPE_ACCESSIBILITY_OVERLAY` as a compact top-corner card instead of a full-width panel so the phone remains usable underneath it
- the overlay now includes a restricted local action set for safe navigation gestures and can resolve matching voice commands locally before escalating to backend chat

## Runtime Contract

- the shell assumes the backend is exposed at a configurable localhost URL, defaulting to `http://127.0.0.1:8000`
- runtime install and lifecycle operations still flow through the Termux-managed scripts under `$HOME/mordecai/scripts`
- advanced mode updates `.env` through Termux and restarts the backend after changing mode flags
- when the accessibility service is enabled, notification and wake-phrase voice commands can delegate into the overlay path so replies, avatar emotion, and TTS stay aligned on the lock screen
- both the foreground shell service and the accessibility service now create backend voice sessions and stream wake-word, partial transcript, final transcript, interruption, and playback-finished events into `/api/voice/sessions/*`
- accessibility events now also feed `/api/android/perception`, letting the backend maintain current app, visible text, clickable action labels, and notification summaries without waiting for manual operator ingestion
- the shell now starts with a dedicated welcome screen on first launch and uses explicit rationale popups before requesting microphone, notification, or accessibility access, keeping permission escalation visible and intentional; the cog in the main shell opens a dedicated settings screen for backend URL, wake phrase, permission review, shell toggles, live status summaries, and AI profile selection
- AI settings are now applied explicitly through the shell by writing the selected provider mode and OpenAI-compatible endpoint settings into the Termux-managed runtime `.env`, then restarting the backend so cloud or local model routing changes take effect visibly

## Build Surface

- root Gradle files: `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`
- Gradle wrapper: `gradlew`, `gradlew.bat`, `gradle/wrapper/`
- app module: `android-shell/`

## Build And Validation

- local builds no longer require a system Gradle install because the repository ships the Gradle wrapper
- required local tooling is JDK 17 plus Android SDK platform 35, build-tools 35.0.0, and platform-tools
- build command on Windows: `./gradlew.bat :android-shell:assembleDebug`
- build command on Unix-like shells: `./gradlew :android-shell:assembleDebug`
- CI now runs the wrapper-backed Android build and uploads the debug APK as an artifact
- pushes to `main` now also republish a rolling `android-shell-latest` GitHub release asset so the Termux installer has a stable APK download target, with the workflow staging the built APK to a deterministic filename before release publication
- the release-publication job now resolves the downloaded APK with `find` under the artifact directory before calling `gh release create`, which avoids path mismatches caused by retained upload directory structure
- this release-publication path handling is part of the required documentation-sync surface, because the installer depends on the rolling `android-shell-latest` asset remaining stable across CI changes
- CI provisions Android SDK packages through `android-actions/setup-android@v4` instead of a manual `sdkmanager --licenses` pipe, which avoids broken-pipe failures under `bash -o pipefail`
- the repository tracks `gradlew` with the executable bit, and Linux CI still applies `chmod +x ./gradlew` defensively before invoking it
- the app module depends on `androidx.lifecycle:lifecycle-service` because the foreground supervisor is implemented as a `LifecycleService`

## Limitations

- the shell supervises the existing backend contract rather than replacing it with an embedded Python runtime
- Android automation remains bound by the backend policy layer and only becomes available when advanced mode is explicitly enabled
- local APK validation still depends on a configured Android SDK; without `ANDROID_HOME` or `local.properties`, `assembleDebug` cannot run on this machine
- accessibility service metadata now uses `android:accessibilityFlags` in `mordecai_accessibility_config.xml`, matching Android resource-link requirements in CI, and now subscribes to notification-state events so shell-side perception can include notification summaries

## Debugging

For phone-specific service, overlay, battery, and APK-install debugging, use `docs/debugging-guide.md` as the primary operations guide. Perfetto is the highest-value Android-side tool for shell startup latency, overlay churn, and battery analysis, while the optional installer debug toolkit focuses on backend and network debugging inside the Linux runtime.