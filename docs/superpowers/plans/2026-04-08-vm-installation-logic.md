# VM Tool Installation Logic — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix VM tool installation logic — remove `uv sync` on user projects, pin versions, add staleness detection for install-and-own, centralize env vars.

**Architecture:** New `_env.py` module for centralized env var access. New `_vm_tool.py` module with `ensure_tool_ready()` called before CLI proxy. Provisioning template cleaned up (no project venv block, version pinned). Project-specific `provision.sh` committed for this repo's own development.

**Tech Stack:** Python 3.12+, basedpyright strict, pytest, dataclasses

**Spec:** `docs/superpowers/specs/2026-04-08-vm-installation-logic-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/qt_ai_dev_tools/_env.py` | Create | Centralized env var registry with typed access |
| `src/qt_ai_dev_tools/_vm_tool.py` | Create | Tool readiness check (version match, staleness) |
| `src/qt_ai_dev_tools/cli.py` | Modify | Use `_env.py`, call `ensure_tool_ready()` in proxy |
| `src/qt_ai_dev_tools/vagrant/vm.py` | Modify | Use `_env.py` for env var references |
| `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` | Modify | Remove project venv block, pin version |
| `src/qt_ai_dev_tools/vagrant/workspace.py` | Modify | Pass version to template context |
| `provision.sh` | Create | Project-specific provisioning (committed) |
| `tests/unit/test_env.py` | Create | Tests for `_env.py` |
| `tests/unit/test_vm_tool.py` | Create | Tests for `_vm_tool.py` |
| `tests/unit/test_workspace.py` | Modify | Update for version in template context |
| `tests/unit/test_vm.py` | Modify | Update for `_env.py` usage |
| `docs/ROADMAP.md` | Modify | Add installation e2e test task |

---

### Task 1: Create `_env.py` — Centralized Env Var Registry

**Files:**
- Create: `src/qt_ai_dev_tools/_env.py`
- Create: `tests/unit/test_env.py`

**Skills:** `writing-python-code`, `testing-python`

This module defines all env vars the tool reads as typed dataclass descriptors with a typed read function. No `Any`, no `cast`.

- [ ] **Step 1: Write tests for `_env.py`**

```python
"""Tests for centralized environment variable registry."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from qt_ai_dev_tools._env import (
    EnvVar,
    get_bool,
    get_str,
    ALLOW_VERSION_MISMATCH,
    BRIDGE,
    DISPLAY,
    VM,
)

pytestmark = pytest.mark.unit


class TestEnvVarDefinitions:
    def test_vm_var_has_correct_name(self) -> None:
        assert VM.name == "QT_AI_DEV_TOOLS_VM"

    def test_bridge_var_has_correct_name(self) -> None:
        assert BRIDGE.name == "QT_AI_DEV_TOOLS_BRIDGE"

    def test_allow_version_mismatch_var_has_correct_name(self) -> None:
        assert ALLOW_VERSION_MISMATCH.name == "QT_AI_DEV_TOOLS_ALLOW_VERSION_MISMATCH"

    def test_display_var_has_correct_name(self) -> None:
        assert DISPLAY.name == "DISPLAY"

    def test_all_vars_have_descriptions(self) -> None:
        for var in [VM, BRIDGE, ALLOW_VERSION_MISMATCH, DISPLAY]:
            assert var.description, f"{var.name} missing description"


class TestGetBool:
    def test_returns_true_when_env_set_to_1(self) -> None:
        with patch.dict(os.environ, {"QT_AI_DEV_TOOLS_VM": "1"}):
            assert get_bool(VM) is True

    def test_returns_false_when_env_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert get_bool(VM) is False

    def test_returns_false_when_env_set_to_0(self) -> None:
        with patch.dict(os.environ, {"QT_AI_DEV_TOOLS_VM": "0"}):
            assert get_bool(VM) is False

    def test_returns_false_when_env_set_to_empty(self) -> None:
        with patch.dict(os.environ, {"QT_AI_DEV_TOOLS_VM": ""}):
            assert get_bool(VM) is False

    def test_returns_true_when_env_set_to_true(self) -> None:
        with patch.dict(os.environ, {"QT_AI_DEV_TOOLS_VM": "true"}):
            assert get_bool(VM) is True

    def test_returns_true_when_env_set_to_yes(self) -> None:
        with patch.dict(os.environ, {"QT_AI_DEV_TOOLS_VM": "yes"}):
            assert get_bool(VM) is True


class TestGetStr:
    def test_returns_value_when_set(self) -> None:
        with patch.dict(os.environ, {"DISPLAY": ":42"}):
            assert get_str(DISPLAY) == ":42"

    def test_returns_default_when_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert get_str(DISPLAY) == ""

    def test_returns_custom_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert get_str(DISPLAY, default=":99") == ":99"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_env.py -v -p xdist -p timeout`
Expected: ImportError — module does not exist yet.

- [ ] **Step 3: Implement `_env.py`**

```python
"""Centralized environment variable registry.

All env vars read by qt-ai-dev-tools are defined here as typed descriptors.
This provides a single source of truth for env var names, descriptions, and
default values.  Descriptions support future documentation generation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = frozenset({"1", "true", "yes"})


@dataclass(frozen=True, slots=True)
class EnvVar:
    """An environment variable descriptor with name, description, and default."""

    name: str
    description: str
    default: str = ""


def get_bool(var: EnvVar) -> bool:
    """Read an env var as a boolean (truthy: '1', 'true', 'yes')."""
    return os.environ.get(var.name, var.default).lower() in _TRUTHY


def get_str(var: EnvVar, *, default: str | None = None) -> str:
    """Read an env var as a string."""
    fallback = default if default is not None else var.default
    return os.environ.get(var.name, fallback)


# ── Registered env vars ────────────────────────────────────────────────

VM = EnvVar(
    name="QT_AI_DEV_TOOLS_VM",
    description="Set to '1' inside the Vagrant VM.  Used by the CLI to detect "
    "whether to proxy commands via SSH or execute locally.",
)

BRIDGE = EnvVar(
    name="QT_AI_DEV_TOOLS_BRIDGE",
    description="Set to '1' to enable the bridge server in Qt apps.  "
    "The bridge provides runtime code execution via Unix socket.",
)

ALLOW_VERSION_MISMATCH = EnvVar(
    name="QT_AI_DEV_TOOLS_ALLOW_VERSION_MISMATCH",
    description="Set to '1' to downgrade version mismatch errors to warnings.  "
    "By default, a version mismatch between host and VM tool is a fatal error.",
)

DISPLAY = EnvVar(
    name="DISPLAY",
    description="X11 display identifier.  The VM uses ':99' (Xvfb).  "
    "All AT-SPI and xdotool commands require this to be set.",
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_env.py -v -p xdist -p timeout`
Expected: All pass.

- [ ] **Step 5: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/_env.py tests/unit/test_env.py
git commit -m "feat: add centralized env var registry (_env.py)"
```

---

### Task 2: Migrate existing code to use `_env.py`

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py`
- Modify: `tests/unit/test_vm.py`

**Skills:** `writing-python-code`

Replace all raw `os.environ.get(...)` calls for registered env vars with `_env` module access.

- [ ] **Step 1: Update `cli.py` — replace `_is_in_vm()`**

In `cli.py`, change `_is_in_vm()` (around line 132-134) from:

```python
def _is_in_vm() -> bool:
    """Check if we're running inside the Vagrant VM."""
    return os.environ.get("QT_AI_DEV_TOOLS_VM") == "1"
```

to:

```python
def _is_in_vm() -> bool:
    """Check if we're running inside the Vagrant VM."""
    from qt_ai_dev_tools._env import VM, get_bool

    return get_bool(VM)
```

- [ ] **Step 2: Update `vm.py` — use env var constants in env prefix**

In `vm.py`, the `vm_run()` function constructs an env prefix string (line 111-117). The string values are shell exports, not Python reads, so they stay as string literals. However, import `_env` and add a comment referencing the canonical definitions:

```python
def vm_run(
    command: str, workspace: Path | None = None, display: str = ":99", *, stream: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run a command inside the VM with proper Qt/AT-SPI environment.

    Env vars exported here are defined in ``qt_ai_dev_tools._env``.
    """
```

This is documentation-only — the shell env prefix must remain a string template since it's executed in bash, not Python.

- [ ] **Step 3: Verify existing tests still pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_vm.py tests/unit/test_env.py tests/unit/test_cli_helpers.py -v -p xdist -p timeout`
Expected: All pass.

- [ ] **Step 4: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py src/qt_ai_dev_tools/vagrant/vm.py
git commit -m "refactor: migrate env var reads to _env.py registry"
```

---

### Task 3: Create `_vm_tool.py` — Tool Readiness Check

**Files:**
- Create: `src/qt_ai_dev_tools/_vm_tool.py`
- Create: `tests/unit/test_vm_tool.py`

**Skills:** `writing-python-code`, `testing-python`

This is the most complex new module. It checks whether the tool in the VM is ready (correct version for PyPI mode, up-to-date source for install-and-own mode).

- [ ] **Step 1: Write tests for `_vm_tool.py`**

```python
"""Tests for VM tool readiness check."""

from __future__ import annotations

import subprocess as _subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from qt_ai_dev_tools._vm_tool import (
    InstallMode,
    ToolVersionMismatchError,
    _compute_source_hash,
    _detect_install_mode,
    _get_vm_tool_version,
    ensure_tool_ready,
)

pytestmark = pytest.mark.unit


class TestDetectInstallMode:
    def test_returns_local_when_source_dir_exists(self, tmp_path: Path) -> None:
        ws = tmp_path / ".qt-ai-dev-tools"
        ws.mkdir()
        (ws / "src").mkdir()
        (ws / "src" / "qt_ai_dev_tools").mkdir(parents=True)
        result = _detect_install_mode(tmp_path)
        assert result == InstallMode.LOCAL

    def test_returns_pypi_when_no_source_dir(self, tmp_path: Path) -> None:
        result = _detect_install_mode(tmp_path)
        assert result == InstallMode.PYPI


class TestGetVmToolVersion:
    def test_parses_version_from_output(self) -> None:
        mock_result = _subprocess.CompletedProcess(
            args=[], returncode=0, stdout="qt-ai-dev-tools 0.6.2\n", stderr=""
        )
        with patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=mock_result):
            version = _get_vm_tool_version(Path("/fake"))
        assert version == "0.6.2"

    def test_returns_none_on_failure(self) -> None:
        mock_result = _subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="command not found"
        )
        with patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=mock_result):
            version = _get_vm_tool_version(Path("/fake"))
        assert version is None

    def test_returns_none_on_unparseable_output(self) -> None:
        mock_result = _subprocess.CompletedProcess(
            args=[], returncode=0, stdout="garbage output\n", stderr=""
        )
        with patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=mock_result):
            version = _get_vm_tool_version(Path("/fake"))
        assert version is None


class TestComputeSourceHash:
    def test_returns_consistent_hash_for_same_content(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "qt_ai_dev_tools"
        src.mkdir(parents=True)
        (src / "cli.py").write_text("print('hello')")
        (src / "__init__.py").write_text("")
        hash1 = _compute_source_hash(tmp_path)
        hash2 = _compute_source_hash(tmp_path)
        assert hash1 == hash2

    def test_returns_different_hash_for_different_content(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "qt_ai_dev_tools"
        src.mkdir(parents=True)
        (src / "cli.py").write_text("print('hello')")
        hash1 = _compute_source_hash(tmp_path)
        (src / "cli.py").write_text("print('world')")
        hash2 = _compute_source_hash(tmp_path)
        assert hash1 != hash2

    def test_returns_empty_string_when_no_source_dir(self, tmp_path: Path) -> None:
        result = _compute_source_hash(tmp_path)
        assert result == ""


class TestEnsureToolReady:
    """Tests for the main ensure_tool_ready() orchestration function."""

    def test_skips_check_when_inside_vm(self) -> None:
        with patch("qt_ai_dev_tools._vm_tool.get_bool", return_value=True):
            # Should return without doing anything
            ensure_tool_ready(Path("/fake"))

    def test_pypi_mode_matching_versions_succeeds(self, tmp_path: Path) -> None:
        mock_result = _subprocess.CompletedProcess(
            args=[], returncode=0, stdout="qt-ai-dev-tools 0.6.2\n", stderr=""
        )
        with (
            patch("qt_ai_dev_tools._vm_tool.get_bool", return_value=False),
            patch("qt_ai_dev_tools._vm_tool._detect_install_mode", return_value=InstallMode.PYPI),
            patch("qt_ai_dev_tools._vm_tool.__version__", "0.6.2"),
            patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=mock_result),
        ):
            ensure_tool_ready(tmp_path)  # Should not raise

    def test_pypi_mode_mismatched_versions_raises(self, tmp_path: Path) -> None:
        mock_result = _subprocess.CompletedProcess(
            args=[], returncode=0, stdout="qt-ai-dev-tools 0.5.0\n", stderr=""
        )
        with (
            patch("qt_ai_dev_tools._vm_tool.get_bool", return_value=False),
            patch("qt_ai_dev_tools._vm_tool._detect_install_mode", return_value=InstallMode.PYPI),
            patch("qt_ai_dev_tools._vm_tool.__version__", "0.6.2"),
            patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=mock_result),
        ):
            with pytest.raises(ToolVersionMismatchError, match="0.6.2.*0.5.0"):
                ensure_tool_ready(tmp_path)

    def test_pypi_mode_mismatch_warns_when_allowed(self, tmp_path: Path) -> None:
        mock_result = _subprocess.CompletedProcess(
            args=[], returncode=0, stdout="qt-ai-dev-tools 0.5.0\n", stderr=""
        )
        # get_bool returns True for VM check=False, then True for ALLOW_VERSION_MISMATCH
        call_count = 0

        def mock_get_bool(var: object) -> bool:
            nonlocal call_count
            call_count += 1
            # First call: is_in_vm -> False, Second call: allow_mismatch -> True
            return call_count > 1

        with (
            patch("qt_ai_dev_tools._vm_tool.get_bool", side_effect=mock_get_bool),
            patch("qt_ai_dev_tools._vm_tool._detect_install_mode", return_value=InstallMode.PYPI),
            patch("qt_ai_dev_tools._vm_tool.__version__", "0.6.2"),
            patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=mock_result),
        ):
            ensure_tool_ready(tmp_path)  # Should warn, not raise

    def test_local_mode_rebuilds_when_stale(self, tmp_path: Path) -> None:
        ws = tmp_path / ".qt-ai-dev-tools"
        ws.mkdir()
        src = ws / "src" / "qt_ai_dev_tools"
        src.mkdir(parents=True)
        (src / "cli.py").write_text("print('hello')")

        # Create stale marker
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        marker = state_dir / "source-hash"
        marker.write_text("old-hash")

        rebuild_result = _subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        with (
            patch("qt_ai_dev_tools._vm_tool.get_bool", return_value=False),
            patch("qt_ai_dev_tools._vm_tool._detect_install_mode", return_value=InstallMode.LOCAL),
            patch("qt_ai_dev_tools._vm_tool._STATE_DIR_VM", state_dir),
            patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=rebuild_result) as mock_run,
        ):
            ensure_tool_ready(tmp_path)
            # Should have called vm_run to rebuild
            assert mock_run.called

    def test_vm_tool_not_installed_raises(self, tmp_path: Path) -> None:
        mock_result = _subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="not found"
        )
        with (
            patch("qt_ai_dev_tools._vm_tool.get_bool", return_value=False),
            patch("qt_ai_dev_tools._vm_tool._detect_install_mode", return_value=InstallMode.PYPI),
            patch("qt_ai_dev_tools._vm_tool.__version__", "0.6.2"),
            patch("qt_ai_dev_tools._vm_tool.vm_run", return_value=mock_result),
        ):
            with pytest.raises(ToolVersionMismatchError, match="not installed"):
                ensure_tool_ready(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_vm_tool.py -v -p xdist -p timeout`
Expected: ImportError — module does not exist yet.

- [ ] **Step 3: Implement `_vm_tool.py`**

```python
"""VM tool readiness check.

Ensures the qt-ai-dev-tools binary inside the VM is current before proxying
commands.  Two modes:

- **PyPI mode**: compares host ``__version__`` with VM tool version.
  Mismatch raises ``ToolVersionMismatchError`` (or warns if
  ``QT_AI_DEV_TOOLS_ALLOW_VERSION_MISMATCH=1``).

- **Install-and-own (local) mode**: compares a SHA-256 hash of the local
  ``.qt-ai-dev-tools/src/`` tree with a stored marker in the VM.  If stale,
  rebuilds via ``uv tool install --force``.
"""

from __future__ import annotations

import enum
import hashlib
import logging
from pathlib import Path

from qt_ai_dev_tools.__version__ import __version__
from qt_ai_dev_tools._env import ALLOW_VERSION_MISMATCH, VM, get_bool

logger = logging.getLogger(__name__)

_WORKSPACE_DIR = ".qt-ai-dev-tools"
_STATE_DIR_VM = Path("/home/vagrant/.local/state/qt-ai-dev-tools")


class InstallMode(enum.Enum):
    """How qt-ai-dev-tools was installed in the project."""

    PYPI = "pypi"
    LOCAL = "local"


class ToolVersionMismatchError(Exception):
    """Host and VM tool versions do not match."""


def _detect_install_mode(project_root: Path) -> InstallMode:
    """Detect whether the project uses PyPI or local install-and-own."""
    local_src = project_root / _WORKSPACE_DIR / "src" / "qt_ai_dev_tools"
    if local_src.is_dir():
        return InstallMode.LOCAL
    return InstallMode.PYPI


def _get_vm_tool_version(workspace: Path) -> str | None:
    """Query the tool version inside the VM.

    Returns the version string or None if the tool is not installed or
    the output cannot be parsed.
    """
    from qt_ai_dev_tools.vagrant.vm import vm_run

    result = vm_run("qt-ai-dev-tools --version", workspace)
    if result.returncode != 0:
        return None
    # Expected output: "qt-ai-dev-tools X.Y.Z"
    parts = result.stdout.strip().split()
    if len(parts) >= 2:
        return parts[-1]
    return None


def _compute_source_hash(toolkit_dir: Path) -> str:
    """Compute a SHA-256 hash of all Python files in the toolkit source.

    Returns empty string if the source directory does not exist.
    """
    src_dir = toolkit_dir / "src" / "qt_ai_dev_tools"
    if not src_dir.is_dir():
        return ""
    hasher = hashlib.sha256()
    for py_file in sorted(src_dir.rglob("*.py")):
        hasher.update(py_file.read_bytes())
    return hasher.hexdigest()


def _check_pypi_mode(workspace: Path) -> None:
    """Check version match for PyPI-installed tool."""
    vm_version = _get_vm_tool_version(workspace)
    if vm_version is None:
        msg = f"qt-ai-dev-tools is not installed in the VM (expected {__version__})"
        raise ToolVersionMismatchError(msg)
    if vm_version != __version__:
        if get_bool(ALLOW_VERSION_MISMATCH):
            logger.warning(
                "Version mismatch: host=%s, VM=%s (suppressed by %s)",
                __version__,
                vm_version,
                ALLOW_VERSION_MISMATCH.name,
            )
            return
        msg = (
            f"Version mismatch: host has {__version__}, VM has {vm_version}. "
            f"Re-provision the VM or set {ALLOW_VERSION_MISMATCH.name}=1 to suppress."
        )
        raise ToolVersionMismatchError(msg)
    logger.debug("Version match: host=%s, VM=%s", __version__, vm_version)


def _check_local_mode(project_root: Path, workspace: Path) -> None:
    """Check staleness for install-and-own mode and rebuild if needed."""
    from qt_ai_dev_tools.vagrant.vm import vm_run

    toolkit_dir = project_root / _WORKSPACE_DIR
    current_hash = _compute_source_hash(toolkit_dir)
    if not current_hash:
        logger.warning("Local toolkit at %s has no source files", toolkit_dir)
        return

    # Read stored hash from VM
    marker_path = _STATE_DIR_VM / "source-hash"
    read_result = vm_run(f"cat {marker_path} 2>/dev/null || echo ''", workspace)
    stored_hash = read_result.stdout.strip()

    if stored_hash == current_hash:
        logger.debug("Local toolkit is up-to-date (hash=%s…)", current_hash[:12])
        return

    # Rebuild
    logger.info("Local toolkit changed, rebuilding in VM…")
    rebuild_result = vm_run(
        f"uv tool install --force /vagrant/{_WORKSPACE_DIR}/", workspace
    )
    if rebuild_result.returncode != 0:
        logger.error("Rebuild failed: %s", rebuild_result.stderr)
        return

    # Store new hash
    vm_run(f"mkdir -p {_STATE_DIR_VM} && echo '{current_hash}' > {marker_path}", workspace)
    logger.info("Rebuild complete, hash updated.")


def ensure_tool_ready(project_root: Path, workspace: Path | None = None) -> None:
    """Ensure the VM tool is ready before proxying commands.

    Call this before ``_proxy_to_vm()``.  Does nothing when already inside
    the VM.

    Args:
        project_root: The project root directory (parent of .qt-ai-dev-tools/).
        workspace: Explicit workspace path.  Auto-discovered if None.
    """
    if get_bool(VM):
        return  # Already inside VM

    from qt_ai_dev_tools.vagrant.vm import find_workspace

    ws = find_workspace(workspace)
    mode = _detect_install_mode(project_root)

    if mode == InstallMode.PYPI:
        _check_pypi_mode(ws)
    else:
        _check_local_mode(project_root, ws)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_vm_tool.py -v -p xdist -p timeout`
Expected: All pass.

- [ ] **Step 5: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/_vm_tool.py tests/unit/test_vm_tool.py
git commit -m "feat: add VM tool readiness check (_vm_tool.py)"
```

---

### Task 4: Integrate `ensure_tool_ready()` into CLI Proxy

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`

**Skills:** `writing-python-code`

Wire `ensure_tool_ready()` into `_proxy_to_vm()` so every proxied command checks tool readiness first.

- [ ] **Step 1: Update `_proxy_to_vm()` in `cli.py`**

Find the `_proxy_to_vm()` function (around line 137) and add the readiness check before forwarding. The function currently:

```python
def _proxy_to_vm(workspace: Path | None = None) -> None:
    if _is_in_vm():
        return
    from qt_ai_dev_tools.vagrant.vm import vm_run
    cmd = "qt-ai-dev-tools " + " ".join(shlex.quote(a) for a in sys.argv[1:])
    result = vm_run(cmd, workspace)
    ...
```

Change to:

```python
def _proxy_to_vm(workspace: Path | None = None) -> None:
    if _is_in_vm():
        return

    from qt_ai_dev_tools._vm_tool import ToolVersionMismatchError, ensure_tool_ready

    try:
        ensure_tool_ready(Path.cwd(), workspace)
    except ToolVersionMismatchError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    from qt_ai_dev_tools.vagrant.vm import vm_run
    cmd = "qt-ai-dev-tools " + " ".join(shlex.quote(a) for a in sys.argv[1:])
    result = vm_run(cmd, workspace)
    ...
```

- [ ] **Step 2: Also update `_proxy_screenshot()` similarly**

Add the same readiness check at the top of `_proxy_screenshot()` (around line 157), before any VM interaction.

- [ ] **Step 3: Run existing tests**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/ -v -p xdist -p timeout`
Expected: All pass.

- [ ] **Step 4: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "feat: integrate ensure_tool_ready() into CLI proxy"
```

---

### Task 5: Clean Up Provisioning Template

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2`
- Modify: `src/qt_ai_dev_tools/vagrant/workspace.py`
- Modify: `tests/unit/test_workspace.py`

**Skills:** `writing-python-code`, `testing-python`

Remove the project venv block and pin the tool version in the template.

- [ ] **Step 1: Update `workspace.py` to pass version to template context**

In `render_workspace()`, the template context dict is passed to Jinja2. Add `version` to the context so the template can use `{{ version }}` for version pinning.

Find the `render_workspace()` function and add `"version": __version__` to the template context dict. Import `__version__` at top of function:

```python
def render_workspace(workspace: Path, config: WorkspaceConfig | None = None) -> list[Path]:
    from qt_ai_dev_tools.__version__ import __version__
    # ... existing code ...
    context = {
        # ... existing context keys ...
        "version": __version__,
    }
```

- [ ] **Step 2: Update `provision.sh.j2` — remove project venv block**

Remove the entire block from `provision.sh.j2` that starts with `# Optionally prepare project venv` (approximately lines 100-119):

```
# Optionally prepare project venv if pyproject.toml exists.
# Tests and apps that use AT-SPI (gi.repository.Atspi) need the gi symlinks
# in the project venv too, not just the tool venv.
if [ -f /vagrant/pyproject.toml ]; then
    echo "==> Syncing project venv"
    su - vagrant -c "cd /vagrant && uv sync"
    ...
fi
```

Remove ALL of this. The template should NOT touch the user's project.

- [ ] **Step 3: Update `provision.sh.j2` — pin version for PyPI mode**

Change the PyPI install line from:

```bash
    su - vagrant -c "uv tool install qt-ai-dev-tools"
```

to:

```bash
    su - vagrant -c "uv tool install qt-ai-dev-tools=={{ version }}"
```

The `{{ version }}` will be filled by the template context from Step 1.

- [ ] **Step 4: Update workspace test**

Add a test in `tests/unit/test_workspace.py` to verify the version appears in the rendered provision.sh:

```python
def test_provision_contains_pinned_version(self, tmp_path: Path) -> None:
    from qt_ai_dev_tools.__version__ import __version__

    render_workspace(tmp_path)
    content = (tmp_path / "provision.sh").read_text()
    assert f"qt-ai-dev-tools=={__version__}" in content

def test_provision_does_not_contain_uv_sync(self, tmp_path: Path) -> None:
    render_workspace(tmp_path)
    content = (tmp_path / "provision.sh").read_text()
    assert "uv sync" not in content
```

- [ ] **Step 5: Run tests**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_workspace.py -v -p xdist -p timeout`
Expected: All pass.

- [ ] **Step 6: Run linter**

Run: `uv run poe lint_full`
Expected: 0 errors.

- [ ] **Step 7: Commit**

```bash
git add src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2 src/qt_ai_dev_tools/vagrant/workspace.py tests/unit/test_workspace.py
git commit -m "fix: remove uv sync from template, pin tool version"
```

---

### Task 6: Create Project-Specific `provision.sh`

**Files:**
- Create: `provision.sh` (project root, committed to git)
- Modify: `.gitignore` (if needed)

This project's own development needs `uv sync` + gi symlinks in the project venv. Instead of polluting the template, we commit a project-specific provisioning script.

- [ ] **Step 1: Generate the base provisioning script**

Run `workspace init` to get the current template output, then examine it:

```bash
uv run qt-ai-dev-tools workspace init --memory 4096 --cpus 4
```

- [ ] **Step 2: Create project-specific `provision.sh`**

Copy the generated `.qt-ai-dev-tools/provision.sh` to project root as `provision.sh`. Then append the project-specific block at the end (before the final `echo` line):

```bash
# ── Project-specific: sync project venv + gi symlinks ─────────────────
# This block is specific to qt-ai-dev-tools development.
# The template-generated provision.sh does NOT include this.
if [ -f /vagrant/pyproject.toml ]; then
    echo "==> Syncing project venv (dev-only)"
    su - vagrant -c "cd /vagrant && uv sync"
    PROJECT_VENV="/vagrant/.venv"
    if [ -d "$PROJECT_VENV" ]; then
        echo "==> Linking gi into project venv (dev-only)"
        PROJECT_SITE=$("$PROJECT_VENV/bin/python" -c "import sysconfig; print(sysconfig.get_path('purelib'))")
        SYS_GI_DIR=$(python3 -c "import gi, os; print(os.path.dirname(gi.__file__))")
        SYS_SITE=$(dirname "$SYS_GI_DIR")
        for name in gi pygtkcompat; do
            if [ -e "$SYS_SITE/$name" ]; then
                ln -sf "$SYS_SITE/$name" "$PROJECT_SITE/$name"
            fi
        done
        for so in "$SYS_SITE"/_gi*.so; do
            [ -e "$so" ] && ln -sf "$so" "$PROJECT_SITE/"
        done
    fi
fi
```

- [ ] **Step 3: Update the Vagrantfile to use the project root provision.sh**

The `.qt-ai-dev-tools/Vagrantfile` template references `provision.sh` relative to the workspace dir. For this project's development, we need to point it at the project root `provision.sh` instead. Update the Vagrantfile (or create a note in CLAUDE.md about the workflow).

Actually, the simpler approach: keep `.qt-ai-dev-tools/provision.sh` as the generated one (from template), and use `make provision` which runs `cd .qt-ai-dev-tools && vagrant provision`. The project-specific provision.sh at the root is run via a separate mechanism or by modifying the Vagrantfile to point to `../provision.sh`.

**Decision:** Instead of a separate file, modify the `.qt-ai-dev-tools/Vagrantfile.j2` template to support an optional custom provisioning script path. But that's over-engineering. Simpler: just add a `make` target that runs the extra steps after provisioning:

```makefile
provision-dev: provision  ## re-provision + sync project venv with gi links
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv sync"
	uv run qt-ai-dev-tools vm run 'PROJECT_SITE=$$(/vagrant/.venv/bin/python -c "import sysconfig; print(sysconfig.get_path('"'"'purelib'"'"'))") && SYS_GI_DIR=$$(python3 -c "import gi, os; print(os.path.dirname(gi.__file__))") && SYS_SITE=$$(dirname "$$SYS_GI_DIR") && for name in gi pygtkcompat; do [ -e "$$SYS_SITE/$$name" ] && ln -sf "$$SYS_SITE/$$name" "$$PROJECT_SITE/$$name"; done && for so in "$$SYS_SITE"/_gi*.so; do [ -e "$$so" ] && ln -sf "$$so" "$$PROJECT_SITE/"; done'
```

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "feat: add provision-dev target for project venv gi links"
```

---

### Task 7: Update Roadmap

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Add installation e2e test task to standalone tasks**

Add a new standalone task entry:

```markdown
| S-6 | large | E2E tests for VM tool installation process (both PyPI and install-and-own modes, version mismatch, staleness rebuild). Requires spinning up environments — deferred until Docker is ready (Phase 5). | Deferred |
```

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs: add installation e2e test task to roadmap"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run full linter**

Run: `uv run poe lint_full`
Expected: 0 errors.

- [ ] **Step 2: Run full unit test suite**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/ -v -p xdist -p timeout`
Expected: All pass, 0 failures.

- [ ] **Step 3: Verify no regressions in existing test files**

Pay special attention to:
- `tests/unit/test_vm.py` — env var assertions may need updating
- `tests/unit/test_workspace.py` — template rendering tests
- `tests/unit/test_installer.py` — install-and-own tests
- `tests/unit/test_cli_helpers.py` — CLI helper tests

- [ ] **Step 4: Final commit if any fixes needed**
