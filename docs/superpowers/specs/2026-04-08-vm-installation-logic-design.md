# VM Tool Installation Logic — Design Spec

**Date:** 2026-04-08
**Status:** Approved

## Problem

The VM provisioning template (`provision.sh.j2`) has several issues:

1. **Runs `uv sync` on user's project** (lines 100-119) — wrong. The user's project might not be Python, might use another package manager, or might be C++. We should never touch their dependency tree.
2. **No version pinning for PyPI mode** — `uv tool install qt-ai-dev-tools` installs latest, not the version matching the host. Can cause API mismatches.
3. **No staleness detection for install-and-own mode** — after `vm sync` or `sync-auto`, the tool venv in the VM is stale. No automatic rebuild trigger.
4. **Env vars scattered** — `QT_AI_DEV_TOOLS_VM`, `QT_AI_DEV_TOOLS_BRIDGE`, `DISPLAY` etc. are read via raw `os.environ.get()` calls throughout the codebase with no central registry.

## Design Decisions

### 1. Provisioning template cleanup

- Remove the entire project venv block (lines 100-119 of `provision.sh.j2`) — no `uv sync`, no gi symlinks into project venv
- Pin version for PyPI mode: `uv tool install qt-ai-dev-tools=={{ version }}`
- Keep install-and-own detection and gi-into-tool-venv as-is (correct today)

### 2. Project-specific override provisioning

- This project keeps its own committed `provision.sh` that extends the template output
- Adds `uv sync` on `/vagrant` + gi symlinks into project venv — because this project's tests need AT-SPI access
- Template-generated `provision.sh` is for end users; committed one is for this project's development

### 3. Centralized env var registry (`_env.py`)

- All env vars the tool reads, defined as typed constants with descriptions
- Variables: `QT_AI_DEV_TOOLS_VM`, `QT_AI_DEV_TOOLS_BRIDGE`, `QT_AI_DEV_TOOLS_ALLOW_VERSION_MISMATCH` (new), `DISPLAY`
- Descriptions enable future doc generation
- All existing `os.environ.get(...)` calls migrate to use this module

### 4. Tool readiness check (`_vm_tool.py`)

- `ensure_tool_ready()` — called by `_proxy_to_vm()` before forwarding commands
- Detects install mode by checking if `/vagrant/.qt-ai-dev-tools/src/` exists in the VM
- **PyPI mode**: compares host version (`__version__`) with VM version (`qt-ai-dev-tools --version` via SSH). On mismatch → error. If `ALLOW_VERSION_MISMATCH=1` → warning only.
- **Install-and-own mode**: compares hash of `.qt-ai-dev-tools/src/` with a stored marker (`/home/vagrant/.local/state/qt-ai-dev-tools/source-hash`). If stale → `uv tool install --force /vagrant/.qt-ai-dev-tools/` → update marker → proceed.

### 5. Roadmap update

- Add standalone task for e2e tests covering the installation process (both modes, version mismatch, staleness rebuild)
- Deferred until Docker is ready since testing provisioning requires spinning up full environments

## What stays the same

- Binary path in VM: `~/.local/bin/qt-ai-dev-tools` (both modes, via `uv tool install`)
- CLI proxy mechanism (`_proxy_to_vm()`) — just gains an `ensure_tool_ready()` call
- gi symlink into tool venv — correct as-is
- Workspace discovery (`find_workspace()`) — unchanged

## File changes

| File | Action |
|------|--------|
| `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` | Remove project venv block, pin version |
| `provision.sh` (project root, committed) | New — this project's own provisioning with `uv sync` + gi links |
| `src/qt_ai_dev_tools/_env.py` | New — env var registry |
| `src/qt_ai_dev_tools/_vm_tool.py` | New — tool readiness/staleness check |
| `src/qt_ai_dev_tools/cli.py` | Migrate env var reads to `_env.py`, call `ensure_tool_ready()` |
| `src/qt_ai_dev_tools/vagrant/vm.py` | Migrate env var reads to `_env.py` |
| `docs/ROADMAP.md` | Add installation e2e test task |
