# Provision: Replace `uv sync` with `uv tool install`

## Problem

`provision.sh.j2` line 73 runs `uv sync --project /vagrant` unconditionally. This:

1. **Fails in empty directories** — no `pyproject.toml` means `uv sync` errors out
2. **Couples provisioning to user's build system** — what if they use pip, poetry, or nothing?
3. **Conflates two concerns** — installing qt-ai-dev-tools (always needed) vs installing user's project deps (not our business)

The VM needs `qt-ai-dev-tools` on PATH because host commands proxy into the VM via `vagrant ssh -c "qt-ai-dev-tools ..."`. Without the binary, every proxied command fails.

## Solution

Replace project-specific `uv sync` with `uv tool install qt-ai-dev-tools`. Never sync user's project deps.

### Two install paths

| Scenario | Detection | Install command |
|---|---|---|
| **PyPI** (user ran `uvx qt-ai-dev-tools workspace init`) | No local toolkit dir | `uv tool install qt-ai-dev-tools` |
| **install-and-own** (user has local copy) | `.qt-ai-dev-tools/src/qt_ai_dev_tools/` exists at `/vagrant/.qt-ai-dev-tools/` | `uv tool install --force /vagrant/.qt-ai-dev-tools/` |

### Where `uv tool install` puts things

- Binary: `~/.local/bin/qt-ai-dev-tools` (symlink)
- Venv: `~/.local/share/uv/tools/qt-ai-dev-tools/`
- site-packages: `~/.local/share/uv/tools/qt-ai-dev-tools/lib/python3.X/site-packages/`

### install-and-own needs a pyproject.toml

`uv tool install` requires build metadata. The current install-and-own output has no `pyproject.toml` — just raw source + a PEP 722 shebang script. We must generate a minimal `pyproject.toml` during `install_and_own()`:

```toml
[project]
name = "qt-ai-dev-tools"
version = "<from __version__.py>"
requires-python = ">=3.12"
dependencies = ["typer>=0.12.0", "jinja2>=3.1.0", "colorlog>=6.10.1"]

[project.scripts]
qt-ai-dev-tools = "qt_ai_dev_tools.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/qt_ai_dev_tools"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

The deps are already declared in `_CLI_SCRIPT_TEMPLATE` PEP 722 metadata. The version comes from `__version__.py`. Single source of truth preserved.

## Changes

### 1. `src/qt_ai_dev_tools/installer.py`

- Add `_PYPROJECT_TOML_TEMPLATE` string
- In `install_and_own()`, write `pyproject.toml` to target dir alongside `src/`
- Include in `self_update()` logic (regenerate, don't preserve)

### 2. `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2`

Remove:
```bash
echo "==> Creating project venv with uv sync"
VM_VENV="/home/vagrant/.venv-qt-ai-dev-tools"
su - vagrant -c "UV_PROJECT_ENVIRONMENT=$VM_VENV uv sync --project /vagrant"
```

Replace with:
```bash
echo "==> Installing qt-ai-dev-tools"
TOOL_VENV_BASE="/home/vagrant/.local/share/uv/tools/qt-ai-dev-tools"
if [ -d /vagrant/.qt-ai-dev-tools/src/qt_ai_dev_tools ]; then
    su - vagrant -c "uv tool install --force /vagrant/.qt-ai-dev-tools/"
else
    su - vagrant -c "uv tool install qt-ai-dev-tools"
fi
```

Update gi/pygobject linking to target `$TOOL_VENV_BASE` instead of `$VM_VENV`:
```bash
VENV_SITE=$("$TOOL_VENV_BASE/bin/python" -c "import sysconfig; print(sysconfig.get_path('purelib'))")
```

Update `.bashrc` section:
- Remove `UV_PROJECT_ENVIRONMENT` export
- Ensure `$HOME/.local/bin` is in PATH (may already be via uv install)

### 3. `src/qt_ai_dev_tools/vagrant/vm.py`

In `vm_run()` env_prefix:
- Replace `PATH=$HOME/.venv-qt-ai-dev-tools/bin:$PATH` with `PATH=$HOME/.local/bin:$PATH`
- Remove `UV_PROJECT_ENVIRONMENT=$HOME/.venv-qt-ai-dev-tools`

### 4. `src/qt_ai_dev_tools/vagrant/workspace.py`

- Remove `UV_PROJECT_ENVIRONMENT` from any config if present
- No new config fields needed — the provision template auto-detects local vs PyPI

### 5. Test updates

**Unit tests to update:**
- `tests/unit/test_workspace.py` — template renders `uv tool install` not `uv sync`, gi linking targets tool venv
- `tests/unit/test_vm.py` — `vm_run()` PATH uses `~/.local/bin`, no `UV_PROJECT_ENVIRONMENT`
- `tests/unit/test_installer.py` — install-and-own generates `pyproject.toml`

**Unit tests to add:**
- Provision template: PyPI path renders `uv tool install qt-ai-dev-tools`
- Provision template: install-and-own path renders `uv tool install --force /vagrant/.qt-ai-dev-tools/`
- Provision template: no `uv sync --project` anywhere in output
- Installer: pyproject.toml content is valid (has correct deps, entry point, build system)

**E2E tests to update:**
- `tests/e2e/test_bridge_proxy.py` — hardcoded `/home/vagrant/.venv-qt-ai-dev-tools/bin/python3` path needs updating to use the tool venv path or a more portable lookup

**Manual verification (post-implementation):**
- Empty dir + `workspace init` + `vm up` works
- install-and-own + `workspace init` + `vm up` works
- Published PyPI package works after version bump

## Non-changes

- `uv` binary still installed in VM (useful for users)
- PySide6 still installed via apt (system package)
- Host-to-VM proxy mechanism unchanged (just PATH differs)
- CLI commands, bridge, subsystems — all unchanged
- No new config fields or CLI flags

## Risks

- **gi linking path** — `~/.local/share/uv/tools/qt-ai-dev-tools/lib/python3.X/site-packages/` has a version-dependent path. Must discover dynamically, not hardcode.
- **Reprovisioning** — `uv tool install --force` handles this (idempotent).
- **Network dependency** — PyPI path needs internet. Same as current `uv sync`. Not new.
- **install-and-own detection** — checking `/vagrant/.qt-ai-dev-tools/src/qt_ai_dev_tools/` is reliable since workspace is always at `.qt-ai-dev-tools/`.
