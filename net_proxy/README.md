# Network Proxy Layer

This directory is the canonical home for Mordecai's safe internet boundary.

## Current Implementation

The active proxy runtime is implemented in `src/mordecai/proxy.py` with policy decisions sourced from `src/mordecai/policy.py` and configuration from `src/mordecai/config.py`.

## Responsibilities

- Domain allowlists
- Request logging
- Rate limiting
- Centralized outbound request control

The active runtime should continue to use a single guarded outbound surface rather than ad hoc direct HTTP calls.