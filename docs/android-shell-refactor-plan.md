# Android Shell Refactor Plan

This note captures the next safe architecture step for the native Android shell.

Status as of 2026-05-10:

- step 1 is implemented: a shared `VoiceSessionController` now owns the duplicated voice-session lifecycle
- step 2 is partially implemented: backend HTTP transport and runtime command dispatch are now split behind the temporary `BackendSupervisor` facade
- step 3 is implemented: `ShellCoordinator` now owns the shared shell-state snapshot and cross-surface runtime/status orchestration
- step 4 is implemented: `StartupOrchestrator` now owns bounded startup recovery, startup phases, and backend verification
- main shell surfaces now consume coordinator state instead of recomputing root, permission, backend, and service summaries locally

It focuses on three goals:

- split orchestration from transport
- remove duplicated voice-session logic between the foreground shell service and the accessibility service
- keep the shell aligned with Mordecai's explicit, debuggable, policy-bound runtime model

## Current ownership map

The current shell is functional, but orchestration responsibilities are spread across a few classes:

- `MainActivity` owns shell dashboard launch and basic command buttons.
- `SettingsActivity` owns operator preferences, permission review, and mode/provider application.
- `MordecaiShellService` owns foreground supervision, backend polling, wake-phrase startup, notification state, and one voice-command path.
- `MordecaiAccessibilityService` owns overlay UI, restricted local actions, perception streaming, and a second voice-command path.
- `BackendSupervisor` owns both HTTP calls to the localhost backend and the Termux-backed runtime command bridge.
- `TermuxCommandClient` owns shell command dispatch into Termux.

The main architectural issue is that both long-lived Android services rebuild the same voice-session lifecycle on top of `BackendSupervisor`, while `BackendSupervisor` itself mixes two separate concerns:

- backend API transport
- runtime install/start/stop/update and configuration commands

## Exact duplication audit

The following responsibilities are duplicated today between `MordecaiShellService` and `MordecaiAccessibilityService`:

### 1. Backend client construction

Both services:

- load `mordecai-shell-prefs`
- create a `BackendSupervisor`
- resolve the same configurable backend URL from `PREF_BACKEND_URL`

### 2. Voice-session lifecycle

Both services:

- keep a local `voiceSessionId`
- lazily create a background voice session with `startVoiceSession(...)`
- reuse the same session across multiple commands

### 3. Playback completion reporting

Both services:

- create `SpeechOutput`
- wire `onCompleted` to `postVoiceSessionEvent(... playbackFinished = true, autoExecute = false)`

### 4. Interruption handling before a new command

Both services:

- interrupt in-flight TTS before listening again
- send a voice-session interruption event
- send the current wake phrase as a non-final transcript seed

### 5. Partial transcript forwarding

Both services:

- forward partial transcripts from recognition into `postVoiceSessionEvent(... isFinal = false, autoExecute = false)`

### 6. Final command dispatch

Both services:

- send the final spoken command into `postVoiceSessionEvent(... isFinal = true, autoExecute = true)`
- derive a spoken reply from `lastResponse` or `planResponse`

### 7. Reply persistence

Both services:

- persist the last spoken backend response into `PREF_LAST_REPLY`

## Responsibility overlap with BackendSupervisor

`BackendSupervisor` is not duplicating the same code as the two services, but it does force them to duplicate orchestration because it currently exposes a mixed surface:

- backend health, avatar, runtime status, chat, voice-session, and perception HTTP calls
- install, start, stop, update, AI-provider configuration, and advanced-mode toggles through `TermuxCommandClient`

That mixed API encourages services to depend on a large utility instead of a narrower abstraction.

## Target shape

The smallest useful target is four layers:

### 1. `ShellBackendClient`

Purpose:

- pure typed HTTP client for the localhost backend

Owns:

- `/health`
- `/api/status`
- `/api/avatar`
- `/api/chat`
- `/api/voice/sessions/*`
- `/api/android/perception`

Does not own:

- Termux lifecycle commands
- preference reads
- wake logic
- notification or overlay decisions

### 2. `RuntimeCommandGateway`

Purpose:

- typed wrapper around `TermuxCommandClient`

Owns:

- install
- start
- stop
- update
- AI-provider apply
- advanced-mode apply

This can remain a thin wrapper over the existing `TermuxCommandClient` at first.

### 3. `VoiceSessionController`

Purpose:

- shared voice-session state machine for both services

Owns:

- session creation and caching
- interruption events
- transcript forwarding
- final-command dispatch
- playback-finished events
- last-reply persistence

Does not own:

- wake phrase recognition startup
- notification rendering
- overlay rendering
- local restricted accessibility actions

### 4. `ShellCoordinator`

Purpose:

- central orchestration layer for shell runtime state

Owns:

- current shell state snapshot
- backend reachability state
- whether the runtime should be auto-started
- startup ordering
- shell-service and accessibility-service shared policies
- source-agnostic voice entrypoints that delegate to `VoiceSessionController`

Does not own:

- actual Android UI widgets
- direct speech-recognition implementation details
- direct Termux command formatting

## Proposed `ShellState`

The coordinator should publish one typed state model, exposed through `StateFlow`:

- `termuxInstalled: Boolean`
- `backendReachable: Boolean`
- `backendStatusText: String`
- `shellServiceEnabled: Boolean`
- `wakeEnabled: Boolean`
- `accessibilityEnabled: Boolean`
- `overlayEnabled: Boolean`
- `advancedModeAllowed: Boolean`
- `advancedModeEnabled: Boolean`
- `activeVoiceSurface: NONE | SHELL_SERVICE | ACCESSIBILITY_OVERLAY`
- `lastReply: String?`
- `startupPhase: NOT_STARTED | CHECKING_ENVIRONMENT | STARTING_RUNTIME | VERIFYING_BACKEND | READY | DEGRADED`

This state should become the source for:

- foreground notification text
- main/settings screen summaries
- future debug surfaces inside the shell app

## StartupOrchestrator plan

Introduce `StartupOrchestrator` as a narrow class used by `ShellCoordinator`.

It should perform startup in explicit phases:

1. Load operator preferences.
2. Check local prerequisites:
   - Termux installed
   - root availability
   - microphone permission
   - notification permission
   - accessibility enabled state
3. Probe backend `/health`.
4. If backend is offline and auto-start is enabled, invoke runtime start through `RuntimeCommandGateway`.
5. Re-probe backend health with bounded retries.
6. Publish final startup phase and degradation reason.

Non-goals for the first version:

- no hidden retries that last indefinitely
- no silent privilege escalation
- no automatic permission prompts from background startup

## Smallest safe extraction

The smallest safe extraction is not a full rewrite. It is a three-step move that preserves current behavior.

### Step 1. Extract `VoiceSessionController`

New file candidates:

- `android-shell/src/main/java/ai/mordecai/shell/voice/VoiceSessionController.kt`
- `android-shell/src/main/java/ai/mordecai/shell/backend/ShellBackendClient.kt`

Move into `VoiceSessionController`:

- `voiceSessionId`
- `ensureVoiceSessionId(...)`
- `playbackFinished` reporting
- transcript posting helpers
- interrupt helper
- final-command execution helper
- last-reply persistence

Keep in `MordecaiShellService`:

- wake phrase ownership
- foreground notification rendering
- backend health polling for now

Keep in `MordecaiAccessibilityService`:

- overlay rendering
- restricted local actions
- perception streaming

This step removes the highest-risk duplication without changing app structure.

### Step 2. Split `BackendSupervisor`

Refactor `BackendSupervisor` into:

- `ShellBackendClient`
- `RuntimeCommandGateway`

Compatibility path:

- keep `BackendSupervisor` temporarily as a facade delegating to both classes
- migrate call sites gradually

This avoids a large rename burst while shrinking future coupling.

### Step 3. Introduce `ShellCoordinator` plus `StartupOrchestrator`

After the shared voice and transport seams exist, move these responsibilities out of `MordecaiShellService`:

- health-check loop ownership
- auto-start decision logic
- shell state derivation
- startup sequencing

At that point:

- `MordecaiShellService` becomes a thin Android service host for wake phrase, notification surface, and coordinator callbacks
- `MordecaiAccessibilityService` becomes a thin overlay and accessibility event host with voice delegation to the coordinator

## Concrete future file plan

### New files

- `android-shell/src/main/java/ai/mordecai/shell/backend/ShellBackendClient.kt`
- `android-shell/src/main/java/ai/mordecai/shell/backend/RuntimeCommandGateway.kt`
- `android-shell/src/main/java/ai/mordecai/shell/voice/VoiceSessionController.kt`
- `android-shell/src/main/java/ai/mordecai/shell/coordinator/ShellCoordinator.kt`
- `android-shell/src/main/java/ai/mordecai/shell/coordinator/StartupOrchestrator.kt`
- `android-shell/src/main/java/ai/mordecai/shell/state/ShellState.kt`

### Existing files to simplify

- `android-shell/src/main/java/ai/mordecai/shell/BackendSupervisor.kt`
- `android-shell/src/main/java/ai/mordecai/shell/MordecaiShellService.kt`
- `android-shell/src/main/java/ai/mordecai/shell/accessibility/MordecaiAccessibilityService.kt`
- `android-shell/src/main/java/ai/mordecai/shell/MainActivity.kt`
- `android-shell/src/main/java/ai/mordecai/shell/SettingsActivity.kt`

## Stratos-inspired guardrails

The following patterns are worth adopting from Stratos at a design level, without copying implementation:

### Operator-driven updates

- updates should remain explicit and operator-initiated
- update actions should expose progress and failure state clearly
- dangerous actions should stay grouped in visible UI with confirmation

### Typed shell config

- shell configuration should be validated as typed data before it reaches `.env` mutation or runtime restarts
- defaults should be centralized instead of duplicated across activities and services
- only known fields should be persisted or applied

### Clear shell/backend contract boundaries

- keep the Android shell contract small, typed, and documented
- make shell-originated event types explicit, especially for voice sessions and perception ingestion
- prefer a thin transport client plus visible orchestration over helper classes that mix transport and policy

## Execution order recommendation

Recommended implementation order:

1. Extract `VoiceSessionController`. ✅
2. Add `ShellBackendClient` and make `BackendSupervisor` delegate to it. ✅
3. Add `RuntimeCommandGateway` and move runtime lifecycle methods behind it. ✅
4. Introduce `ShellState` and `ShellCoordinator`. ✅
5. Add `StartupOrchestrator` and move startup sequencing into it. ✅
6. Update `MainActivity` and `SettingsActivity` to read coordinator state instead of recomputing summaries locally. ✅

This order minimizes behavior risk while steadily removing duplication.

## Out of scope

This note does not propose:

- changing the localhost backend contract
- weakening policy enforcement
- bypassing Termux as the runtime host
- embedding Python directly into the shell APK
- expanding accessibility actions beyond the current restricted local set
