# Mordecai Core

This directory defines the logical home of the AI runtime itself.

## Current Implementation

The working runtime currently lives in `src/mordecai/` so packaging, tests, and CI remain stable.

## Logical Subsystems

- `agent.py` maps to `src/mordecai/agent.py`
- `tools/` maps to runtime services such as `proxy.py`, `git_tools.py`, and `android_control.py`
- `models/` maps to `src/mordecai/models.py` and provider configuration in `src/mordecai/config.py`
- `safety/` maps to `src/mordecai/policy.py` and protected runtime boundaries

This directory exists to establish the canonical project vocabulary without forcing a disruptive package move today.