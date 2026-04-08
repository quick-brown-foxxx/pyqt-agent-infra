# VM Tool Installation Logic — Design Decisions

**Date:** 2026-04-08 | **Status:** Implemented in v0.6.3

## Key decisions

1. **Provisioning template never touches user's project.** No `uv sync`, no gi symlinks into project venv. Template pins tool version: `uv tool install qt-ai-dev-tools=={{ version }}`.

2. **Project-specific dev provisioning** via `make provision-dev` Makefile target (not a committed `provision.sh`). Runs `uv sync` + gi symlinks for this project's own test venv.

3. **Centralized env var registry** (`_env.py`). `EnvVar` frozen dataclass with `get_bool()`/`get_str()`. Vars: `VM`, `BRIDGE`, `ALLOW_VERSION_MISMATCH`, `DISPLAY`.

4. **Tool readiness check** (`_vm_tool.py`). `ensure_tool_ready()` called before CLI proxy. PyPI mode: version match (error on mismatch, `ALLOW_VERSION_MISMATCH=1` suppresses). Install-and-own mode: SHA-256 hash staleness → auto-rebuild + gi re-link.

5. **gi re-link after rebuild.** `uv tool install --force` destroys venv symlinks. `_RELINK_GI_CMD` re-creates them after every rebuild.

## Deferred

- E2e installation tests (roadmap S-6) — needs Docker backend (Phase 5).
