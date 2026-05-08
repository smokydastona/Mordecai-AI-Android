# Sandbox Layer

This directory defines the Linux execution layer that sits on top of Android and below the Mordecai runtime.

## Scope

- Termux and proot bootstrap
- Package installation for Python services and future local model support
- Environment reproducibility

## Current Runtime Mapping

- `scripts/proot-setup.sh` is the canonical public installer for preparing the sandboxed backend from scratch.
- `scripts/start.sh` is the canonical Phase 1 launcher for the backend service.
- `sandbox/proot-setup.sh` is a compatibility wrapper for older bootstrap references.

The sandbox is the preferred place for experimentation, dependency management, and future local model hosting.