# Mordecai Core Tools

Operational tools are currently implemented inside `src/mordecai/`:

- `proxy.py` for guarded web access
- `git_tools.py` for repository state and backups
- `android_control.py` for explicit Android actions

Future standalone tool adapters can be introduced here once the runtime surface is stable enough to split cleanly.