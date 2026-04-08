# Provision: Replace `uv sync` with `uv tool install` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `uv sync --project /vagrant` in VM provisioning with `uv tool install qt-ai-dev-tools`, decoupling the tool installation from the user's project and fixing the empty-directory bug.

**Architecture:** The provisioning template detects whether a local install-and-own copy exists at `/vagrant/.qt-ai-dev-tools/` and installs from there, otherwise installs from PyPI. `vm_run()` PATH is updated to use `~/.local/bin` (where `uv tool install` places binaries). The `install_and_own()` function generates a minimal `pyproject.toml` so the local copy is pip/uv-installable. gi/pygobject linking targets the tool's venv at `~/.local/share/uv/tools/qt-ai-dev-tools/`.

**Tech Stack:** Python 3.12+, Jinja2 templates, uv, pytest, bash

**Spec:** `docs/superpowers/specs/2026-04-08-provision-uv-tool-install-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/qt_ai_dev_tools/installer.py` | Add `pyproject.toml` generation to install-and-own |
| Modify | `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` | Replace `uv sync` with `uv tool install`, update gi linking, update .bashrc |
| Modify | `src/qt_ai_dev_tools/vagrant/vm.py` | Update `vm_run()` env_prefix PATH |
| Modify | `tests/unit/test_installer.py` | Test pyproject.toml generation |
| Modify | `tests/unit/test_workspace.py` | Test provision template renders correctly |
| Modify | `tests/unit/test_vm.py` | Test updated vm_run() PATH construction |
| Modify | `tests/e2e/test_bridge_proxy.py` | Update hardcoded venv paths |
| Modify | `tests/CLAUDE.md` | Update provisioning docs |

---

### Task 1: Add `pyproject.toml` generation to `install_and_own()`

**Files:**
- Modify: `src/qt_ai_dev_tools/installer.py`
- Test: `tests/unit/test_installer.py`

**Context:** `uv tool install` requires a `pyproject.toml` at the install path. The current install-and-own output has no build metadata — just raw source + a PEP 722 shebang script. We need to generate a minimal pyproject.toml alongside the source. Use the `writing-python-code` skill.

- [ ] **Step 1: Write failing tests for pyproject.toml generation**

Add to `tests/unit/test_installer.py`:

```python
class TestInstallAndOwnPyprojectToml:
    """Tests for pyproject.toml generation in install_and_own()."""

    def test_creates_pyproject_toml(self, tmp_path: Path) -> None:
        """install_and_own should create a pyproject.toml for uv tool install."""
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        pyproject = tmp_path / "pyproject.toml"
        assert pyproject.exists()

    def test_pyproject_contains_entry_point(self, tmp_path: Path) -> None:
        """pyproject.toml must define the qt-ai-dev-tools CLI entry point."""
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        content = (tmp_path / "pyproject.toml").read_text()
        assert 'qt-ai-dev-tools = "qt_ai_dev_tools.cli:app"' in content

    def test_pyproject_contains_dependencies(self, tmp_path: Path) -> None:
        """pyproject.toml must declare runtime dependencies."""
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        content = (tmp_path / "pyproject.toml").read_text()
        assert "typer" in content
        assert "jinja2" in content
        assert "colorlog" in content

    def test_pyproject_contains_build_system(self, tmp_path: Path) -> None:
        """pyproject.toml must have a hatchling build-system for uv tool install."""
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        content = (tmp_path / "pyproject.toml").read_text()
        assert "hatchling" in content
        assert 'packages = ["src/qt_ai_dev_tools"]' in content

    def test_pyproject_contains_correct_version(self, tmp_path: Path) -> None:
        """pyproject.toml version should match __version__."""
        from qt_ai_dev_tools.__version__ import __version__
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        content = (tmp_path / "pyproject.toml").read_text()
        assert f'version = "{__version__}"' in content

    def test_pyproject_listed_in_created_paths(self, tmp_path: Path) -> None:
        """install_and_own should include pyproject.toml in returned paths."""
        from qt_ai_dev_tools.installer import install_and_own

        created = install_and_own(tmp_path)

        assert "pyproject.toml" in created
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_installer.py::TestInstallAndOwnPyprojectToml -v -p timeout`
Expected: FAIL — pyproject.toml not created.

- [ ] **Step 3: Implement pyproject.toml generation**

In `src/qt_ai_dev_tools/installer.py`, add a template and write function:

```python
_PYPROJECT_TOML_TEMPLATE: str = """\
[project]
name = "qt-ai-dev-tools"
version = "{version}"
requires-python = ">=3.12"
dependencies = ["typer>=0.12.0", "jinja2>=3.1.0", "colorlog>=6.10.1"]

[project.scripts]
qt-ai-dev-tools = "qt_ai_dev_tools.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/qt_ai_dev_tools"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""


def _write_pyproject_toml(target: Path) -> Path:
    """Generate pyproject.toml for uv tool install compatibility."""
    pyproject_path = target / "pyproject.toml"
    pyproject_path.write_text(_PYPROJECT_TOML_TEMPLATE.format(version=__version__))
    return pyproject_path
```

Add to `install_and_own()` after the config.toml generation:

```python
    # Generate pyproject.toml (enables `uv tool install` from this directory)
    _write_pyproject_toml(target)
    created.append("pyproject.toml")
```

Also update `self_update()` — pyproject.toml should be regenerated (not preserved, since it tracks version):

No change needed — `self_update()` calls `install_and_own()` which already regenerates it, and the preserve list only covers `config.toml` and `notes/`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_installer.py -v -p timeout`
Expected: ALL PASS

- [ ] **Step 5: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/installer.py tests/unit/test_installer.py
git commit -m "feat: generate pyproject.toml in install-and-own for uv tool install"
```

---

### Task 2: Update provision template — replace `uv sync` with `uv tool install`

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2`
- Test: `tests/unit/test_workspace.py`

**Context:** The provision template must detect local vs PyPI install and use `uv tool install` accordingly. gi/pygobject linking must target the tool's venv. `.bashrc` must drop `UV_PROJECT_ENVIRONMENT` and ensure `~/.local/bin` is in PATH. Use the `writing-python-code` skill for test code.

- [ ] **Step 1: Write failing tests for provision template**

Add to `tests/unit/test_workspace.py`:

```python
class TestProvisionUvToolInstall:
    """Tests for uv tool install provisioning (replaces uv sync)."""

    def test_provision_does_not_contain_uv_sync(self, tmp_path: Path) -> None:
        """provision.sh must not contain 'uv sync --project /vagrant'."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "uv sync --project /vagrant" not in content

    def test_provision_contains_uv_tool_install_pypi(self, tmp_path: Path) -> None:
        """provision.sh must contain 'uv tool install qt-ai-dev-tools' for PyPI path."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "uv tool install qt-ai-dev-tools" in content

    def test_provision_contains_install_and_own_detection(self, tmp_path: Path) -> None:
        """provision.sh must detect local install-and-own copy."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "/vagrant/.qt-ai-dev-tools/src/qt_ai_dev_tools" in content

    def test_provision_contains_uv_tool_install_local(self, tmp_path: Path) -> None:
        """provision.sh must use 'uv tool install --force' for local copy."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "uv tool install --force" in content

    def test_provision_gi_linking_uses_tool_venv(self, tmp_path: Path) -> None:
        """gi/pygobject linking must target the uv tool venv, not project venv."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert ".local/share/uv/tools/qt-ai-dev-tools" in content
        assert ".venv-qt-ai-dev-tools" not in content

    def test_provision_bashrc_no_uv_project_environment(self, tmp_path: Path) -> None:
        """provision.sh .bashrc block must not export UV_PROJECT_ENVIRONMENT."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "UV_PROJECT_ENVIRONMENT" not in content

    def test_provision_bashrc_has_local_bin_in_path(self, tmp_path: Path) -> None:
        """provision.sh .bashrc block must add ~/.local/bin to PATH."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert ".local/bin" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_workspace.py::TestProvisionUvToolInstall -v -p timeout`
Expected: FAIL — provision.sh still contains `uv sync`.

- [ ] **Step 3: Update provision.sh.j2**

In `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2`, replace lines 63-91 (the `uv + project venv` section and gi linking) with:

```bash
# ── uv + qt-ai-dev-tools ──────────────────────────────────────────────────
# Install uv for general use, then install qt-ai-dev-tools as a standalone
# tool. If a local install-and-own copy exists, install from that; otherwise
# install from PyPI.
echo "==> Installing uv"
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/opt/uv" sh
ln -sf /opt/uv/uv /usr/local/bin/uv
ln -sf /opt/uv/uvx /usr/local/bin/uvx

echo "==> Installing qt-ai-dev-tools"
if [ -d /vagrant/.qt-ai-dev-tools/src/qt_ai_dev_tools ]; then
    su - vagrant -c "uv tool install --force /vagrant/.qt-ai-dev-tools/"
else
    su - vagrant -c "uv tool install qt-ai-dev-tools"
fi

# Link system-only gi/pygobject into the tool's venv (not pip-installable).
# gi.repository.Atspi requires: gi package, _gi C extension, pygtkcompat.
# NOTE: apt installs gi into /usr/lib/python3/dist-packages/, NOT the path
# returned by sysconfig.get_path('purelib') (/usr/local/lib/...).  We locate
# gi by actually importing it, which always gives the real path.
TOOL_VENV="$HOME/.local/share/uv/tools/qt-ai-dev-tools"
TOOL_PYTHON=$(su - vagrant -c "readlink -f \$HOME/.local/share/uv/tools/qt-ai-dev-tools/bin/python")
VENV_SITE=$("$TOOL_PYTHON" -c "import sysconfig; print(sysconfig.get_path('purelib'))")
SYS_GI_DIR=$(python3 -c "import gi, os; print(os.path.dirname(gi.__file__))")
SYS_SITE=$(dirname "$SYS_GI_DIR")
for name in gi pygtkcompat; do
    if [ -e "$SYS_SITE/$name" ]; then
        ln -sf "$SYS_SITE/$name" "$VENV_SITE/$name"
    fi
done
# Link compiled _gi*.so extensions (may live next to gi/ in the same site dir)
for so in "$SYS_SITE"/_gi*.so; do
    [ -e "$so" ] && ln -sf "$so" "$VENV_SITE/"
done
```

Also update the `.bashrc` block (lines 265-284). Replace:
```bash
export UV_PROJECT_ENVIRONMENT=\$HOME/.venv-qt-ai-dev-tools
```
With:
```bash
export PATH=\$HOME/.local/bin:\$PATH
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_workspace.py -v -p timeout`
Expected: ALL PASS

- [ ] **Step 5: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2 tests/unit/test_workspace.py
git commit -m "feat: replace uv sync with uv tool install in provisioning"
```

---

### Task 3: Update `vm_run()` env prefix

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py:103-119`
- Test: `tests/unit/test_vm.py:69-121`

**Context:** `vm_run()` constructs an env prefix for SSH commands. It currently adds `$HOME/.venv-qt-ai-dev-tools/bin` to PATH and exports `UV_PROJECT_ENVIRONMENT`. Both need updating. Use the `writing-python-code` skill.

- [ ] **Step 1: Update existing test assertions**

In `tests/unit/test_vm.py`, modify `test_env_contains_required_variables` (line 92). Change:

```python
        assert "UV_PROJECT_ENVIRONMENT=$HOME/.venv-qt-ai-dev-tools" in ssh_cmd
```

To:

```python
        assert "PATH=$HOME/.local/bin:$PATH" in ssh_cmd
        assert "UV_PROJECT_ENVIRONMENT" not in ssh_cmd
        assert ".venv-qt-ai-dev-tools" not in ssh_cmd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_vm.py::TestVmRunEnvConstruction::test_env_contains_required_variables -v -p timeout`
Expected: FAIL — still has old PATH.

- [ ] **Step 3: Update vm_run() env_prefix**

In `src/qt_ai_dev_tools/vagrant/vm.py`, replace lines 111-118:

```python
    env_prefix = (
        f"export DISPLAY={display} QT_QPA_PLATFORM=xcb QT_ACCESSIBILITY=1"
        " QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1"
        " QT_AI_DEV_TOOLS_VM=1"
        " PATH=$HOME/.local/bin:$PATH"
        ' DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus";'
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_vm.py -v -p timeout`
Expected: ALL PASS

- [ ] **Step 5: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/vagrant/vm.py tests/unit/test_vm.py
git commit -m "feat: update vm_run() PATH to use ~/.local/bin for uv tool install"
```

---

### Task 4: Update `test_bridge_proxy.py` hardcoded venv paths

**Files:**
- Modify: `tests/e2e/test_bridge_proxy.py:100-116`

**Context:** The `vm_bridge_app` fixture hardcodes `/home/vagrant/.venv-qt-ai-dev-tools/bin/python3` for the app Python interpreter and `UV_PROJECT_ENVIRONMENT` in the systemd service environment. Both must use the new tool venv path. Use the `writing-python-code` skill.

- [ ] **Step 1: Update the fixture**

In `tests/e2e/test_bridge_proxy.py`, update the `vm_bridge_app` fixture. Replace lines 104-116:

```python
    start = _vm_run(
        "systemd-run --user --unit=test-bridge-app"
        " --property=Environment=DISPLAY=:99"
        " --property=Environment=QT_AI_DEV_TOOLS_BRIDGE=1"
        " --property=Environment=QT_QPA_PLATFORM=xcb"
        " --property=Environment=QT_ACCESSIBILITY=1"
        " --property=Environment=QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1"
        " --property=Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
        " --property=WorkingDirectory=/vagrant"
        " python3 app/main.py",
        timeout=10,
    )
```

Key changes:
- Remove `UV_PROJECT_ENVIRONMENT` property (no longer needed)
- Use system `python3` instead of venv python (PySide6 is a system package installed via apt)

- [ ] **Step 2: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_bridge_proxy.py
git commit -m "fix: update bridge proxy test fixture for uv tool install paths"
```

---

### Task 5: Update `tests/CLAUDE.md` documentation

**Files:**
- Modify: `tests/CLAUDE.md`

**Context:** The test infrastructure docs reference `uv sync --project /vagrant`, `~/.venv-qt-ai-dev-tools`, and `UV_PROJECT_ENVIRONMENT`. All must be updated.

- [ ] **Step 1: Update provisioning section**

In `tests/CLAUDE.md`, update the "Provisioning" section to reflect:
- `uv tool install` instead of `uv sync`
- Tool venv at `~/.local/share/uv/tools/qt-ai-dev-tools/` instead of `~/.venv-qt-ai-dev-tools`
- Binary at `~/.local/bin/qt-ai-dev-tools`

Update the "Environment variables" section:
- Remove `UV_PROJECT_ENVIRONMENT`
- Add `PATH=$HOME/.local/bin:$PATH`

Update the "Known issues" section:
- Remove mention of `uv sync` being needed for `pytest-timeout`

- [ ] **Step 2: Commit**

```bash
git add tests/CLAUDE.md
git commit -m "docs: update test CLAUDE.md for uv tool install provisioning"
```

---

### Task 6: Version bump + publish + manual verification

**Files:**
- Modify: `pyproject.toml:4` (version)
- Modify: `src/qt_ai_dev_tools/__version__.py:5` (version)

**Context:** We need a published PyPI version to test the PyPI install path. Bump version, publish, then verify both paths work with a real VM. This task requires a running VM.

- [ ] **Step 1: Bump version**

In `pyproject.toml` line 4, change `version = "0.5.1"` to `version = "0.6.0"`.
In `src/qt_ai_dev_tools/__version__.py` line 5, change `__version__: str = "0.5.1"` to `__version__: str = "0.6.0"`.

- [ ] **Step 2: Run full linter + unit tests**

Run: `uv run poe lint_full`
Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/ -v -p timeout -p xdist -n auto`
Expected: ALL PASS, 0 errors.

- [ ] **Step 3: Commit and publish**

```bash
git add pyproject.toml src/qt_ai_dev_tools/__version__.py
git commit -m "release: bump version to 0.6.0"
uv publish
```

- [ ] **Step 4: Regenerate workspace and reprovision**

```bash
uv run qt-ai-dev-tools workspace init
uv run qt-ai-dev-tools vm destroy
uv run qt-ai-dev-tools vm up
```

Wait for provisioning to complete (~10 min).

- [ ] **Step 5: Verify qt-ai-dev-tools available in VM**

```bash
uv run qt-ai-dev-tools vm run "which qt-ai-dev-tools"
# Expected: /home/vagrant/.local/bin/qt-ai-dev-tools
uv run qt-ai-dev-tools vm run "qt-ai-dev-tools --help"
# Expected: CLI help output
```

- [ ] **Step 6: Verify gi/pygobject linking works**

```bash
uv run qt-ai-dev-tools vm run "qt-ai-dev-tools tree"
# Expected: widget tree output (AT-SPI works, gi imported successfully)
```

- [ ] **Step 7: Verify host-to-VM proxy works**

```bash
uv run qt-ai-dev-tools tree
# Expected: same output as above, proxied transparently
```

---

### Task 7: Test install-and-own path

**Context:** Verify the install-and-own path works: `install-and-own` creates a local copy with pyproject.toml, then provisioning installs from it.

- [ ] **Step 1: Create a test project in a temporary directory**

```bash
mkdir -p /tmp/test-empty-project
cd /tmp/test-empty-project
```

- [ ] **Step 2: Run install-and-own**

```bash
uvx qt-ai-dev-tools install-and-own .qt-ai-dev-tools --yes-I-will-maintain-it
```

Verify pyproject.toml exists:
```bash
cat .qt-ai-dev-tools/pyproject.toml
# Expected: valid pyproject.toml with entry point, deps, build-system
```

- [ ] **Step 3: Initialize workspace and boot VM**

```bash
cd /tmp/test-empty-project
# Use the local cli to init workspace (it's in .qt-ai-dev-tools/cli)
.qt-ai-dev-tools/cli workspace init
```

Verify provision.sh detects local copy:
```bash
grep "uv tool install" .qt-ai-dev-tools/provision.sh
# Expected: shows the if/else with local detection
```

- [ ] **Step 4: Boot VM (this tests the local install path)**

```bash
cd /tmp/test-empty-project
.qt-ai-dev-tools/cli vm up
```

Wait for provisioning. Should see "Installing qt-ai-dev-tools" with the local install path.

- [ ] **Step 5: Verify tool available in VM**

```bash
.qt-ai-dev-tools/cli vm run "which qt-ai-dev-tools"
# Expected: /home/vagrant/.local/bin/qt-ai-dev-tools
.qt-ai-dev-tools/cli vm run "qt-ai-dev-tools --help"
# Expected: CLI help
```

- [ ] **Step 6: Update .gitignore**

In the main project, add `.qt-ai-dev-tools/` to `.gitignore` if testing locally:
```bash
echo ".qt-ai-dev-tools/" >> /tmp/test-empty-project/.gitignore
```

- [ ] **Step 7: Clean up test project**

```bash
cd /tmp/test-empty-project
.qt-ai-dev-tools/cli vm destroy
cd /
rm -rf /tmp/test-empty-project
```

---

### Task 8: Final verification — full test suite

**Context:** Run the full lint + test suite to verify nothing is broken.

- [ ] **Step 1: Run linter**

Run: `make lint-full`
Expected: 0 errors

- [ ] **Step 2: Run full test suite**

Run: `make test-full`
Expected: ALL PASS, 0 failures, 0 errors

- [ ] **Step 3: Update CLAUDE.md**

Update the main `CLAUDE.md` to reflect provisioning changes:
- In "Key technical facts": update VM provisioning description
- In "Current state": mention the provisioning fix
- Update any references to `~/.venv-qt-ai-dev-tools` or `UV_PROJECT_ENVIRONMENT`

- [ ] **Step 4: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for uv tool install provisioning"
```
