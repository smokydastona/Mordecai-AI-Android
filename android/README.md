# Android Layer

This directory is reserved for device-specific setup, recovery notes, radio guidance, and guarded control instructions for supported Android hosts. The Galaxy S10e remains the advanced reference profile, not the only target.

## Scope

- ROM selection and flashing notes
- Root and Magisk decisions
- Radio and connectivity guidance
- Android-side prerequisites for Termux, ADB, and automation

## Current Canonical References

- `docs/phase1-install.md`
- `docs/s10e-setup.md`
- `src/mordecai/android_control.py`

Keep Android changes explicit and recoverable. Device control must remain opt-in and allowlist-based.