# Galaxy S10e Setup

This document defines the target baseline for the S10e device that hosts Mordecai.

## Device Goals

- Stable daily-driver Android base
- Recoverable root path
- Reliable Termux and proot environment
- Minimal background noise from unwanted OEM or carrier software

## Recommended Baseline

1. Start from a clean, supportable ROM path.
2. Enable developer options and USB debugging.
3. Validate ADB connectivity from a trusted host machine.
4. Install Termux and confirm package updates complete cleanly.
5. Prepare the Linux sandbox used by Mordecai.

## ROM And Root Notes

- Prefer a debloated, maintainable Android build over a feature-heavy one.
- Only enable root if Android control or deeper automation requires it.
- Keep a known-good recovery path before enabling experimental automation.

## Base Environment

- Termux installed and updated
- Python available inside the sandbox
- Git available inside the sandbox
- Enough persistent storage for model caches, logs, and candidate workspaces

## Repo Entry Points

- `android/` contains phone-specific setup notes and future helper scripts.
- `sandbox/proot-setup.sh` is the canonical bootstrap entry point for the Linux layer.
- `scripts/termux_boot.sh` remains the direct app bootstrap for the current Python runtime.