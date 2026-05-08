# Self Modification Layer

This directory represents the controlled self-improvement system for Mordecai.

## Current Implementation

The live implementation is in `src/mordecai/self_improvement.py` and already supports:

- candidate creation
- sandbox workspace preparation
- test-gated evaluation
- apply with backups
- rollback

## Canonical Future Split

- `propose_change.py`
- `run_tests.py`
- `apply_change.py`
- `policies.md`

The split is documented here first so future refactors preserve the existing policy boundaries instead of weakening them.