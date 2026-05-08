# Mordecai Core Safety

Safety enforcement is currently centered in:

- `src/mordecai/policy.py`
- protected path rules in the self-improvement flow
- allowlisted outbound networking in `src/mordecai/proxy.py`

This directory is the canonical future home for expanded validators, approval rules, and safety policy documents that should remain distinct from the general runtime logic.