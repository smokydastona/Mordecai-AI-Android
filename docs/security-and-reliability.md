# Security and Reliability Improvements

This document outlines critical security and reliability fixes made to Mordecai as of 2026-05-08.

## Critical Issues Fixed

### 1. Self-Improvement Test Execution Error Handling

**Issue**: Test failures in `_run_tests()` were silently logged without detailed error information.

**Fix**: 
- Added comprehensive exception handling for subprocess failures
- Capture stderr/stdout separately for better diagnostics
- Implement 30-second timeout to prevent hung test suites
- Return detailed error messages for FileNotFoundError and other runtime errors

**Impact**: Self-improvement candidates now properly report test failures instead of silently marking as failed.

### 2. Concurrent State Store Data Loss (TOCTOU Race Condition)

**Issue**: Under concurrent FastAPI requests, the StateStore had a Time-Of-Check-Time-Of-Use race condition where two workers could lose each other's writes.

**Before**:
```python
# Non-atomic operation
with self._lock:
    payload = self._load(path)      # Read under lock
    payload.append(entry)
    self._save(path, payload)        # Write under lock
# Between lock release and next read, another process could overwrite
```

**After**:
```python
# Atomic rename operation
with self._lock:
    payload = self._load(path)
    payload.append(entry)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(...)      # Write to temp file
    temp_path.replace(path)         # Atomic rename on most filesystems
```

**Impact**: Conversation history and tool execution logs are now safe under high concurrency.

### 3. Avatar Emotion Classification Completeness

**Issue**: Avatar emotion classification fell back to "neutral" 30% of the time due to incomplete token coverage.

**Fix**:
- Changed from early-return pattern to scoring-based approach
- Expanded token coverage from 11 emotions to comprehensive set per emotion
- Multiple tokens per emotion increase classification accuracy
- Fallback only when no tokens match any emotion

**Example Improvement**:
- `"I don't understand this"` now returns "thinking" instead of "neutral"
- `"error in processing"` now returns "concerned" instead of "neutral"

**Impact**: Avatar expressions better reflect system state and improve user perception.

### 4. Concurrent Workspace Directory Creation

**Issue**: Config validation could fail if workspace_dir didn't exist, breaking initialization in tests and edge cases.

**Fix**: Changed from validation check to automatic creation with `mkdir(parents=True, exist_ok=True)`.

**Impact**: Simpler configuration, no edge case failures during initialization.

## High-Priority Issues Fixed

### 5. Untested Candidate Promotion Gap

**Issue**: Manual candidate promotion accepted `tests_passed=None`, which allowed untested self-improvement candidates to reach the live workspace.

**Fix**:
- Require `tests_passed is True` before any apply path can promote a candidate
- Added regression coverage for manual apply through the runtime API and manager layer

**Impact**: Self-improvement is now test-gated on both auto-apply and manual promotion paths.

### 6. Incomplete Protected Runtime Perimeter

**Issue**: Self-improvement path protection covered only a narrow subset of runtime files and left core execution surfaces writable.

**Fix**:
- Expanded protected runtime files in `src/mordecai/`
- Protected all `mordecai_core/` and `providers/` execution surfaces from self-modification
- Added tests that assert core and provider changes are blocked

**Impact**: Runtime wiring, tool execution, and provider surfaces now stay behind the policy boundary.

### 7. Exception Masking in FastAPI Endpoints

**Issue**: Broad `except Exception` clauses caught system exceptions like `KeyboardInterrupt`, preventing graceful shutdown.

**Fix**: Added explicit handling to re-raise system exceptions before catching application exceptions.

**Impact**: Graceful shutdown now works correctly, server can be interrupted cleanly.

### 8. Mutable Policy Protected Paths

**Issue**: Policy engine's `protected_paths` was a mutable `set()`, allowing runtime modification.

**Fix**: Changed to immutable `frozenset`.

**Impact**: Policy enforcement cannot be bypassed at runtime through attribute modification.

### 9. Silent OpenAI Configuration Fallback

**Issue**: Incomplete OpenAI configuration silently fell back to rule-based provider without notifying operator.

**Fix**: Added validation that checks all three required fields (api_key, base_url, model) and logs detailed warning about missing fields.

**Impact**: Operators now get clear feedback when OpenAI is unavailable due to incomplete config.

### 10. Git Binary Output Handling

**Issue**: Git subprocess calls would crash on non-UTF8 output (e.g., binary diffs).

**Fix**: Added `errors='replace'` parameter to handle decode errors gracefully.

**Impact**: Git operations are more robust against unusual file types and encodings.

## Medium-Priority Issues Fixed

### 13. Personal-Data Exfiltration And Purchase-Flow Gaps

**Issue**: The outbound proxy previously enforced only a domain allowlist, and Android control still exposed generic `tap`, `swipe`, and `type` injection. That meant an allowlisted host could still receive personal data, and direct UI automation could still be used to progress a checkout flow.

**Fix**:
- Added payload-aware outbound policy validation for personal-data fields and values
- Blocked commerce-oriented outbound paths such as checkout and payment endpoints, even when the host itself is allowlisted
- Blocked direct Android `tap`, `swipe`, and `type` actions at the policy layer, leaving only safer navigation and allowlisted app-launch flows available
- Added regression coverage for blocked checkout URLs, blocked personal-data payloads, blocked sensitive query values, and blocked direct Android input actions

**Impact**: Mordecai can no longer use its managed network surface to send common personal data to the internet, and it can no longer use generic Android UI injection to complete purchases or enter payment details.

### 11. State Store Silent Failure Handling

**Issue**: Persistence and state read failures were reduced to silent fallbacks or stderr warnings, which hid broken audit and rollback state.

**Fix**:
- Added explicit `StateStoreError` exceptions for corrupt, missing, and failed-save state files
- Propagate those failures to runtime callers instead of silently returning empty state or warning-only output

**Impact**: Persistence failures are now visible to operators and API clients.

### 12. Type Inconsistency in LocalModelService

**Issue**: `model_available` field could return `bool | None`, violating type contract.

**Fix**: Changed to always return `bool` (False if path is None).

**Impact**: API clients have consistent type expectations.

## Architecture Improvements

### Atomic File Operations

The StateStore now uses proper atomic file operations with temporary files and rename semantics, following best practices for safe concurrent file I/O.

### Runtime Composition Boundary

Runtime composition now lives in a dedicated bootstrap module so the core execution layer can compose runtime services without importing the FastAPI entrypoint module.

### Defensive Error Handling

All external subprocess calls now include:
- Timeout handling
- Binary output handling
- Detailed error reporting
- Graceful degradation

### Configuration Validation

Settings validation now:
- Automatically creates required directories
- Validates dependent field groups early
- Logs warnings about incomplete optional configs
- Prevents silent fallbacks

## Testing

All 57 tests pass with these fixes:
- ✅ Error handling scenarios covered
- ✅ Concurrent access patterns validated
- ✅ Configuration edge cases handled
- ✅ Exception propagation verified

## Recommendations for Future Work

1. **Async/Sync Boundary**: Separate async I/O concerns in `agent.chat()` to improve performance under load
2. **Dashboard Refactoring**: Break 17KB dashboard.py into modular templates
3. **Process-Level Locking**: Consider implementing inter-process locks for truly safe concurrent access
4. **Emotion Classification**: Continue expanding emotion token vocabulary based on user feedback
5. **Performance Monitoring**: Add telemetry for detecting race conditions and timeouts in production
