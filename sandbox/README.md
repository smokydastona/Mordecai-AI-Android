# Sandbox Layer

This directory defines the Linux execution layer that sits on top of Android and below the Mordecai runtime.

## Scope

- Termux and proot bootstrap
- Package installation for Python services and future local model support
- Environment reproducibility

## Current Runtime Mapping

- `scripts/termux_boot.sh` starts the active runtime inside the sandbox.
- `sandbox/proot-setup.sh` is the canonical bootstrap script for preparing the sandbox from scratch.

The sandbox is the preferred place for experimentation, dependency management, and future local model hosting.