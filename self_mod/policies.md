# Self Modification Policies

Mordecai may only improve itself through reversible, test-gated, observable changes.

## Allowed

- Propose candidate file changes outside protected paths
- Run tests in a sandboxed workspace
- Generate diffs for operator review
- Apply approved candidates with backups
- Roll back an applied candidate using recorded backups

## Forbidden

- Editing protected policy and safety surfaces
- Editing avatar assets, avatar style, or avatar behavior
- Introducing hidden persistence through shell rc files, boot receivers, scheduled tasks, or autostart registration patterns
- Applying failed candidates
- Writing hidden persistence or hidden startup behavior
- Bypassing the git, proxy, Android, or safety policy layers

## Protected Runtime Surfaces

The current runtime protects at least these files from self-modification:

- `src/mordecai/policy.py`
- `src/mordecai/proxy.py`
- `src/mordecai/self_improvement.py`
- `src/mordecai/config.py`
- `src/mordecai/avatar.py`
- `prompts/system_prompt.txt`
- `assets/avatar/`