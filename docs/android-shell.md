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
- `MainActivity` provides install, start, stop, update, refresh, and settings controls
- `MordecaiShellService` polls the localhost backend and can auto-start it through Termux when offline
- `WakePhraseManager` listens for the configured wake phrase and triggers backend startup when it is heard
- `SpeechCommandProcessor` captures the next spoken command and dispatches it to the backend chat API
- `SpeechOutput` speaks backend replies through Android TTS with an older, slower default cadence
- `TermuxCommandClient` invokes the Phase 1 scripts through the Termux run-command API
- `RootDetector` gates advanced mode toggles so Mode B activation remains explicit
- `MordecaiTileService` gives the shell a quick-settings entrypoint for voice command activation
- `MordecaiAccessibilityService` exposes a lock-screen-safe accessibility overlay and can own voice command capture when accessibility mode is enabled
- `MordecaiOverlay` renders avatar feedback and backend replies over the lock screen through `TYPE_ACCESSIBILITY_OVERLAY`
- the overlay now includes a restricted local action set for safe navigation gestures and can resolve matching voice commands locally before escalating to backend chat

## Runtime Contract

- the shell assumes the backend is exposed at a configurable localhost URL, defaulting to `http://127.0.0.1:8000`
- runtime install and lifecycle operations still flow through the Termux-managed scripts under `$HOME/mordecai/scripts`
- advanced mode updates `.env` through Termux and restarts the backend after changing mode flags
- when the accessibility service is enabled, notification and wake-phrase voice commands can delegate into the overlay path so replies, avatar emotion, and TTS stay aligned on the lock screen

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
- CI provisions Android SDK packages through `android-actions/setup-android@v4` instead of a manual `sdkmanager --licenses` pipe, which avoids broken-pipe failures under `bash -o pipefail`
- the repository tracks `gradlew` with the executable bit, and Linux CI still applies `chmod +x ./gradlew` defensively before invoking it
- the app module depends on `androidx.lifecycle:lifecycle-service` because the foreground supervisor is implemented as a `LifecycleService`

## Limitations

- the shell supervises the existing backend contract rather than replacing it with an embedded Python runtime
- Android automation remains bound by the backend policy layer and only becomes available when advanced mode is explicitly enabled
- local APK validation still depends on a configured Android SDK; without `ANDROID_HOME` or `local.properties`, `assembleDebug` cannot run on this machine
- accessibility service metadata now uses `android:accessibilityFlags` in `mordecai_accessibility_config.xml`, matching Android resource-link requirements in CI