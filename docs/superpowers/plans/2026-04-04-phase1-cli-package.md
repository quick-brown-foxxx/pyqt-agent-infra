# Phase 1: CLI & Library Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace verbose Python heredocs with one-liner CLI commands. Refactor `scripts/qt_pilot.py` into a proper `qt_ai_dev_tools` package with CLI entry points. Clean up PoC leftovers.

**Architecture:** The package lives in `src/qt_ai_dev_tools/` following src-layout. The existing `QtPilot` class is split into logical modules (pilot core, tree formatting, CLI). The CLI uses `typer` for subcommands. Each CLI command is self-contained — no persistent state between invocations.

**Tech Stack:** Python 3.12+, typer (CLI), gi.repository.Atspi (AT-SPI), xdotool (X11 interaction), scrot (screenshots), basedpyright (strict types), ruff (lint/format), pytest + pytest-qt (tests)

**Skills required for implementation:**
- `writing-python-code` — ALWAYS for any Python file
- `testing-python` — ALWAYS for test files
- `setting-up-python-projects` — for pyproject.toml and project structure

---

## File Structure

### New files to create

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Build config, deps, CLI entry point, tool config |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff, basedpyright) |
| `.gitignore` | Standard Python gitignore |
| `src/qt_ai_dev_tools/__init__.py` | Package init, exports `QtPilot`, `__version__` |
| `src/qt_ai_dev_tools/pilot.py` | `QtPilot` class — AT-SPI connection, tree walking, widget search |
| `src/qt_ai_dev_tools/interact.py` | Interaction functions — click, type, key press, focus, action |
| `src/qt_ai_dev_tools/state.py` | State reading — name, role, extents, text |
| `src/qt_ai_dev_tools/screenshot.py` | Screenshot via scrot |
| `src/qt_ai_dev_tools/models.py` | Data types — `Extents`, `WidgetInfo` |
| `src/qt_ai_dev_tools/cli.py` | Typer CLI app with all subcommands |
| `src/qt_ai_dev_tools/__main__.py` | `python -m qt_ai_dev_tools` entry point |
| `tests/conftest.py` | Shared fixtures |
| `tests/unit/test_models.py` | Unit tests for data types |
| `tests/unit/test_tree_format.py` | Unit tests for tree formatting |
| `tests/integration/test_cli.py` | CLI integration tests (subprocess) |

### Files to modify

| File | Change |
|------|--------|
| `tests/test_main.py` | Update imports from package instead of sys.path hack |
| `Makefile` | Add `lint`, `lint-fix` targets; update test targets for new package |

### Files to delete (PoC leftovers)

| File | Reason |
|------|--------|
| `scripts/qt_pilot.py` | Replaced by `src/qt_ai_dev_tools/` package |
| `pytest.ini` | Config moved to `pyproject.toml` |

### Files to keep unchanged

| File | Reason |
|------|--------|
| `scripts/vm-run.sh` | Still needed for VM command execution |
| `scripts/screenshot.sh` | Still needed for host-side screenshots |
| `app/main.py` | Sample app — unchanged |
| `Vagrantfile` | VM config — unchanged |
| `provision.sh` | VM provisioning — unchanged |

---

## Task 1: Project scaffolding — pyproject.toml, .gitignore, pre-commit

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.pre-commit-config.yaml`
- Create: `src/qt_ai_dev_tools/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

Adapt from template at `~/Projects/coding_rules_python/templates/pyproject.toml`. Key changes from template:
- `name = "qt-ai-dev-tools"`
- `requires-python = ">=3.12"` (VM runs Ubuntu 24.04 with Python 3.12)
- `pythonVersion = "3.12"` in basedpyright
- `target-version = "py312"` in ruff
- Enable typer, colorlog dependencies
- Enable pytest-qt in dev deps
- Add `gi-stubs` note as comment (system package, not pip-installable)
- CLI entry point: `qt-ai-dev-tools = "qt_ai_dev_tools.cli:app"`
- Add `[tool.hatch.build.targets.wheel] packages = ["src/qt_ai_dev_tools"]`
- Preserve existing pytest config from pytest.ini (qt_api, timeout, etc.)

```toml
[project]
name = "qt-ai-dev-tools"
description = "AI agent infrastructure for Qt/PySide apps — inspect, interact, screenshot via AT-SPI"
version = "0.1.0"
license = { text = "GPL-3.0" }
requires-python = ">=3.12"
dependencies = [
    "colorlog>=6.10.1",
    "typer>=0.12.0",
]

# System deps (not pip-installable, installed via apt):
#   gir1.2-atspi-2.0, python3-gi  → gi.repository.Atspi
#   xdotool                        → X11 interaction
#   scrot                          → screenshots

[dependency-groups]
dev = [
    "pytest>=9.0.1",
    "pytest-cov>=7.0.0",
    "pytest-qt>=4.5.0",
    "ruff>=0.14.6",
    "basedpyright>=1.34.0",
    "pre-commit",
    "poethepoet",
]

[build-system]
build-backend = "hatchling.build"
requires = ["hatchling"]

[tool.hatch.build.targets.wheel]
packages = ["src/qt_ai_dev_tools"]

[project.scripts]
qt-ai-dev-tools = "qt_ai_dev_tools.cli:app"

[tool.basedpyright]
pythonPlatform = "Linux"
pythonVersion = "3.12"
venvPath = "."
venv = ".venv"
typeCheckingMode = "strict"
reportAny = "error"
reportImplicitStringConcatenation = "none"
reportUnusedCallResult = "none"
reportUnnecessaryIsInstance = "none"
exclude = [
    "**/__pycache__", ".venv", "venv", "build", "dist", "wrktrs",
]

[tool.ruff]
line-length = 120
target-version = "py312"
extend-exclude = [
    "venv", ".venv", "*.egg", "*.egg-info", "**/dist", "**/build",
    "**/__pycache__", "wrktrs", ".git", ".pytest_cache",
]

[tool.ruff.lint]
extend-select = [
    "E", "F", "W", "I", "N", "UP", "ASYNC", "S", "B", "A", "C4",
    "SIM", "PT", "PERF", "RUF",
]
ignore = ["S101", "RUF001", "S603", "S607"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "PT018"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
qt_api = "pyside6"
timeout = 30
log_cli = true
log_cli_level = "INFO"

[tool.poe.tasks]
test = "pytest"
app = "python -m qt_ai_dev_tools"

[tool.poe.tasks.lint_full]
shell = "basedpyright src/ && ruff check --fix . && ruff format ."
```

- [ ] **Step 2: Create .gitignore**

Copy from `~/Projects/coding_rules_python/templates/gitignore`. Add project-specific entries:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.pyd

# Virtual environments
.venv/
venv/

# Distribution
dist/
build/
*.egg-info/
*.egg

# uv
uv.lock

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Claude Code worktrees
wrktrs/

# Vagrant
.vagrant/
.vagrant-ssh-config
```

- [ ] **Step 3: Create .pre-commit-config.yaml**

Copy from template.

- [ ] **Step 4: Create src/qt_ai_dev_tools/__init__.py**

```python
"""AI agent infrastructure for Qt/PySide apps — inspect, interact, screenshot via AT-SPI."""

__version__ = "0.1.0"

from qt_ai_dev_tools.pilot import QtPilot

__all__ = ["QtPilot"]
```

- [ ] **Step 5: Create directory structure**

```bash
mkdir -p src/qt_ai_dev_tools tests/unit tests/integration tests/fixtures
```

- [ ] **Step 6: Initialize environment and verify**

```bash
uv sync --all-extras --group dev
uv run pre-commit install
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore .pre-commit-config.yaml src/qt_ai_dev_tools/__init__.py
git commit -m "feat: scaffold qt-ai-dev-tools package with pyproject.toml and tooling"
```

---

## Task 2: Models — data types for widget info

**Files:**
- Create: `src/qt_ai_dev_tools/models.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write failing test for Extents**

```python
# tests/unit/test_models.py
from qt_ai_dev_tools.models import Extents

class TestExtents:
    def test_center_calculation(self) -> None:
        ext = Extents(x=100, y=200, width=80, height=40)
        assert ext.center == (140, 220)

    def test_center_odd_dimensions(self) -> None:
        ext = Extents(x=0, y=0, width=101, height=51)
        assert ext.center == (50, 25)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement Extents**

```python
# src/qt_ai_dev_tools/models.py
"""Data types for qt-ai-dev-tools."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Extents:
    """Screen coordinates and dimensions of a widget."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        """Center point of the widget bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/unit/test_models.py -v
```

- [ ] **Step 5: Add WidgetInfo test and implementation**

Add to test file:

```python
from qt_ai_dev_tools.models import WidgetInfo

class TestWidgetInfo:
    def test_display_format(self) -> None:
        info = WidgetInfo(role="push button", name="Save", extents=Extents(100, 200, 80, 30))
        assert '[push button] "Save" @(100,200 80x30)' == str(info)

    def test_display_no_extents(self) -> None:
        info = WidgetInfo(role="label", name="Status")
        assert '[label] "Status"' == str(info)
```

Add to models.py:

```python
@dataclass(slots=True)
class WidgetInfo:
    """Serializable widget information (decoupled from AT-SPI objects)."""

    role: str
    name: str
    extents: Extents | None = None
    text: str | None = None
    children_count: int = 0

    def __str__(self) -> str:
        s = f'[{self.role}] "{self.name}"'
        if self.extents:
            e = self.extents
            s += f" @({e.x},{e.y} {e.width}x{e.height})"
        return s

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict."""
        d: dict[str, object] = {"role": self.role, "name": self.name}
        if self.extents:
            d["extents"] = {"x": self.extents.x, "y": self.extents.y,
                            "width": self.extents.width, "height": self.extents.height}
        if self.text is not None:
            d["text"] = self.text
        d["children_count"] = self.children_count
        return d
```

- [ ] **Step 6: Run tests, lint**

```bash
uv run pytest tests/unit/test_models.py -v
uv run poe lint_full
```

- [ ] **Step 7: Commit**

```bash
git add src/qt_ai_dev_tools/models.py tests/unit/test_models.py
git commit -m "feat: add Extents and WidgetInfo data models"
```

---

## Task 3: Core pilot module — QtPilot class

**Files:**
- Create: `src/qt_ai_dev_tools/pilot.py`
- Create: `src/qt_ai_dev_tools/interact.py`
- Create: `src/qt_ai_dev_tools/state.py`
- Create: `src/qt_ai_dev_tools/screenshot.py`

This is a refactor of `scripts/qt_pilot.py` into the new package. The logic is identical — just split across modules with type hints added.

- [ ] **Step 1: Create state.py — widget state reading**

Functions that read state from AT-SPI widget objects. These are stateless functions, not methods.

```python
# src/qt_ai_dev_tools/state.py
"""Read widget state from AT-SPI objects."""

from __future__ import annotations

from qt_ai_dev_tools.models import Extents

# gi.repository.Atspi is a system package — no type stubs available
import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # type: ignore[import-untyped]  # rationale: system AT-SPI bindings


def get_name(widget: Atspi.Accessible) -> str:
    """Get the accessible name of a widget."""
    return widget.get_name() or ""


def get_role(widget: Atspi.Accessible) -> str:
    """Get the role name of a widget (e.g. 'push button', 'text', 'label')."""
    return widget.get_role_name()


def get_extents(widget: Atspi.Accessible) -> Extents:
    """Get screen position and size of a widget."""
    ext = widget.get_extents(Atspi.CoordType.SCREEN)
    return Extents(ext.x, ext.y, ext.width, ext.height)


def get_text(widget: Atspi.Accessible) -> str:
    """Get text content from a widget. Falls back to accessible name."""
    iface = widget.get_text_iface()
    if iface:
        return iface.get_text(0, iface.get_character_count())
    return widget.get_name() or ""


def get_children(widget: Atspi.Accessible) -> list[Atspi.Accessible]:
    """Get direct children of a widget."""
    children: list[Atspi.Accessible] = []
    for i in range(widget.get_child_count()):
        c = widget.get_child_at_index(i)
        if c:
            children.append(c)
    return children
```

- [ ] **Step 2: Create interact.py — xdotool and AT-SPI actions**

```python
# src/qt_ai_dev_tools/interact.py
"""Widget interaction via xdotool and AT-SPI actions."""

from __future__ import annotations

import os
import subprocess
import time

from qt_ai_dev_tools.state import get_extents

import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # type: ignore[import-untyped]  # rationale: system AT-SPI bindings


def _xdotool_env() -> dict[str, str]:
    """Environment with DISPLAY set for xdotool."""
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    return env


def click(widget: Atspi.Accessible, pause: float = 0.2) -> None:
    """Click the center of a widget using xdotool."""
    ext = get_extents(widget)
    cx, cy = ext.center
    env = _xdotool_env()
    subprocess.run(["xdotool", "mousemove", str(cx), str(cy)], check=True, env=env)
    subprocess.run(["xdotool", "click", "1"], check=True, env=env)
    time.sleep(pause)


def type_text(text: str, delay_ms: int = 20, pause: float = 0.2) -> None:
    """Type text via xdotool into the currently focused widget."""
    subprocess.run(
        ["xdotool", "type", "--delay", str(delay_ms), text],
        check=True, env=_xdotool_env(),
    )
    time.sleep(pause)


def press_key(key: str, pause: float = 0.1) -> None:
    """Press a key via xdotool (e.g. 'Return', 'Tab', 'ctrl+a')."""
    subprocess.run(["xdotool", "key", key], check=True, env=_xdotool_env())
    time.sleep(pause)


def action(widget: Atspi.Accessible, action_name: str = "Press", pause: float = 0.3) -> None:
    """Invoke an AT-SPI action by name (e.g. 'Press', 'SetFocus')."""
    iface = widget.get_action_iface()
    if not iface:
        msg = f'Widget [{widget.get_role_name()}] "{widget.get_name()}" has no action interface'
        raise RuntimeError(msg)
    for i in range(iface.get_n_actions()):
        if iface.get_action_name(i) == action_name:
            iface.do_action(i)
            time.sleep(pause)
            return
    available = [iface.get_action_name(i) for i in range(iface.get_n_actions())]
    msg = f"Action '{action_name}' not found. Available: {available}"
    raise LookupError(msg)


def focus(widget: Atspi.Accessible, pause: float = 0.2) -> None:
    """Focus a widget via AT-SPI SetFocus, falling back to click."""
    try:
        action(widget, "SetFocus", pause=pause)
    except (RuntimeError, LookupError):
        click(widget, pause=pause)
```

- [ ] **Step 3: Create screenshot.py**

```python
# src/qt_ai_dev_tools/screenshot.py
"""Screenshot capture via scrot."""

from __future__ import annotations

import os
import subprocess


def take_screenshot(path: str = "/tmp/screenshot.png") -> str:
    """Take a screenshot of the Xvfb display using scrot.

    Returns the path to the saved screenshot.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    subprocess.run(["scrot", path], check=True, env=env)
    size = os.path.getsize(path)
    print(f"Screenshot: {path} ({size} bytes)")
    return path
```

- [ ] **Step 4: Create pilot.py — main QtPilot class**

This is the refactored core. It delegates to the module functions but provides the same familiar API.

```python
# src/qt_ai_dev_tools/pilot.py
"""QtPilot — main class for AT-SPI based Qt app interaction."""

from __future__ import annotations

import time

from qt_ai_dev_tools import interact, state
from qt_ai_dev_tools.models import Extents, WidgetInfo
from qt_ai_dev_tools.screenshot import take_screenshot

import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # type: ignore[import-untyped]  # rationale: system AT-SPI bindings


class QtPilot:
    """Connect to a running Qt app via AT-SPI and interact with it.

    Usage:
        pilot = QtPilot()                     # finds the first Qt app
        pilot = QtPilot(app_name="main.py")   # by name substring

        pilot.dump_tree()
        btn = pilot.find_one(role="push button", name="Save")
        pilot.click(btn)
        pilot.type_text("hello")
    """

    def __init__(self, app_name: str | None = None, retries: int = 5, delay: float = 1.0) -> None:
        """Connect to a running Qt app via AT-SPI.

        Args:
            app_name: Substring match against app name (default: first app found).
            retries: How many times to poll for the app to appear.
            delay: Seconds between retries.
        """
        self.app: Atspi.Accessible | None = None
        for _ in range(retries):
            desktop = Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                candidate = desktop.get_child_at_index(i)
                if candidate is None:
                    continue
                if app_name is None or app_name in (candidate.get_name() or ""):
                    self.app = candidate
                    break
            if self.app:
                break
            time.sleep(delay)

        if not self.app:
            apps: list[str] = []
            desktop = Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                c = desktop.get_child_at_index(i)
                if c:
                    apps.append(c.get_name())
            msg = f"App '{app_name}' not found on AT-SPI bus. Visible apps: {apps}"
            raise RuntimeError(msg)

    # ── Tree inspection ──────────────────────────────────────────

    def find(
        self, role: str | None = None, name: str | None = None, root: Atspi.Accessible | None = None
    ) -> list[Atspi.Accessible]:
        """Find all widgets matching role and/or name (substring match)."""
        root = root or self.app
        assert root is not None
        results: list[Atspi.Accessible] = []
        self._walk(root, role, name, results)
        return results

    def find_one(
        self, role: str | None = None, name: str | None = None, root: Atspi.Accessible | None = None
    ) -> Atspi.Accessible:
        """Find exactly one widget. Raises if 0 or >1 found."""
        found = self.find(role, name, root)
        if len(found) == 0:
            msg = f"No widget found: role={role}, name={name}"
            raise LookupError(msg)
        if len(found) > 1:
            descs = [f'[{w.get_role_name()}] "{w.get_name()}"' for w in found]
            msg = f"Multiple widgets found for role={role}, name={name}: {descs}"
            raise LookupError(msg)
        return found[0]

    def dump_tree(
        self, root: Atspi.Accessible | None = None, indent: int = 0, max_depth: int = 8
    ) -> str:
        """Return and print a text dump of the widget tree."""
        root = root or self.app
        assert root is not None
        lines: list[str] = []
        self._dump(root, indent, max_depth, lines)
        text = "\n".join(lines)
        print(text)
        return text

    def get_children(self, widget: Atspi.Accessible) -> list[Atspi.Accessible]:
        """Get direct children of a widget."""
        return state.get_children(widget)

    # ── Interaction ──────────────────────────────────────────────

    def click(self, widget: Atspi.Accessible, pause: float = 0.2) -> None:
        """Click the center of a widget using xdotool."""
        interact.click(widget, pause)

    def type_text(self, text: str, delay_ms: int = 20, pause: float = 0.2) -> None:
        """Type text via xdotool into the currently focused widget."""
        interact.type_text(text, delay_ms, pause)

    def press_key(self, key: str, pause: float = 0.1) -> None:
        """Press a key via xdotool."""
        interact.press_key(key, pause)

    def action(self, widget: Atspi.Accessible, action_name: str = "Press", pause: float = 0.3) -> None:
        """Invoke an AT-SPI action by name."""
        interact.action(widget, action_name, pause)

    def focus(self, widget: Atspi.Accessible, pause: float = 0.2) -> None:
        """Focus a widget via AT-SPI SetFocus, falling back to click."""
        interact.focus(widget, pause)

    # ── State ────────────────────────────────────────────────────

    def get_name(self, widget: Atspi.Accessible) -> str:
        """Get the accessible name."""
        return state.get_name(widget)

    def get_role(self, widget: Atspi.Accessible) -> str:
        """Get the role name."""
        return state.get_role(widget)

    def get_extents(self, widget: Atspi.Accessible) -> Extents:
        """Get screen position and size."""
        return state.get_extents(widget)

    def get_text(self, widget: Atspi.Accessible) -> str:
        """Get text content."""
        return state.get_text(widget)

    # ── Screenshots ──────────────────────────────────────────────

    def screenshot(self, path: str = "/tmp/screenshot.png") -> str:
        """Take a screenshot of the Xvfb display."""
        return take_screenshot(path)

    # ── Private ──────────────────────────────────────────────────

    def _walk(
        self,
        node: Atspi.Accessible,
        role: str | None,
        name: str | None,
        results: list[Atspi.Accessible],
    ) -> None:
        for i in range(node.get_child_count()):
            c = node.get_child_at_index(i)
            if c is None:
                continue
            match = True
            if role and c.get_role_name() != role:
                match = False
            if name and name not in (c.get_name() or ""):
                match = False
            if match:
                results.append(c)
            self._walk(c, role, name, results)

    def _dump(
        self,
        node: Atspi.Accessible,
        indent: int,
        max_depth: int,
        lines: list[str],
    ) -> None:
        if indent > max_depth:
            return
        name = node.get_name() or ""
        role = node.get_role_name()
        try:
            ext = node.get_extents(Atspi.CoordType.SCREEN)
            pos = f" @({ext.x},{ext.y} {ext.width}x{ext.height})"
        except Exception:
            pos = ""
        lines.append(f"{'  ' * indent}[{role}] \"{name}\"{pos}")
        for i in range(node.get_child_count()):
            c = node.get_child_at_index(i)
            if c:
                self._dump(c, indent + 1, max_depth, lines)
```

- [ ] **Step 5: Update __init__.py to export key items**

```python
# src/qt_ai_dev_tools/__init__.py
"""AI agent infrastructure for Qt/PySide apps — inspect, interact, screenshot via AT-SPI."""

__version__ = "0.1.0"

from qt_ai_dev_tools.models import Extents, WidgetInfo
from qt_ai_dev_tools.pilot import QtPilot

__all__ = ["Extents", "QtPilot", "WidgetInfo"]
```

- [ ] **Step 6: Lint check**

```bash
uv run ruff check --fix src/qt_ai_dev_tools/ && uv run ruff format src/qt_ai_dev_tools/
```

Note: basedpyright will show errors for `Atspi.Accessible` type annotations since `gi.repository` has no stubs. These are expected and suppressed with `# type: ignore[import-untyped]` on imports. The Atspi types in annotations will need `# type: ignore` pragmas — the implementing agent should use the minimum necessary.

- [ ] **Step 7: Commit**

```bash
git add src/qt_ai_dev_tools/
git commit -m "feat: refactor qt_pilot into qt_ai_dev_tools package with typed modules"
```

---

## Task 4: CLI — typer subcommands

**Files:**
- Create: `src/qt_ai_dev_tools/cli.py`
- Create: `src/qt_ai_dev_tools/__main__.py`

- [ ] **Step 1: Create cli.py with all subcommands**

The CLI provides one-liner access to all QtPilot features. Each command connects to AT-SPI, does one thing, prints output, exits.

```python
# src/qt_ai_dev_tools/cli.py
"""CLI interface for qt-ai-dev-tools."""

from __future__ import annotations

import json
import sys

import typer

app = typer.Typer(
    name="qt-ai-dev-tools",
    help="AI agent tools for Qt/PySide app interaction via AT-SPI.",
    no_args_is_help=True,
)


def _get_pilot(app_name: str | None = None, retries: int = 5) -> "QtPilot":
    """Create a QtPilot instance, handling connection errors."""
    from qt_ai_dev_tools.pilot import QtPilot

    try:
        return QtPilot(app_name=app_name, retries=retries)
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def tree(
    app_name: str | None = typer.Option(None, "--app", help="App name substring to connect to"),
    role: str | None = typer.Option(None, "--role", help="Filter by widget role"),
    max_depth: int = typer.Option(8, "--depth", help="Maximum tree depth"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Print the widget tree of a running Qt app."""
    pilot = _get_pilot(app_name)
    if role:
        widgets = pilot.find(role=role)
        if output_json:
            from qt_ai_dev_tools.state import get_extents, get_name, get_role, get_text
            items = []
            for w in widgets:
                ext = get_extents(w)
                items.append({
                    "role": get_role(w), "name": get_name(w), "text": get_text(w),
                    "extents": {"x": ext.x, "y": ext.y, "width": ext.width, "height": ext.height},
                })
            typer.echo(json.dumps(items, indent=2, ensure_ascii=False))
        else:
            from qt_ai_dev_tools.state import get_extents, get_name, get_role
            for w in widgets:
                ext = get_extents(w)
                typer.echo(f'[{get_role(w)}] "{get_name(w)}" @({ext.x},{ext.y} {ext.width}x{ext.height})')
    else:
        if output_json:
            typer.echo("JSON output for full tree not yet supported. Use --role filter.", err=True)
            raise typer.Exit(code=1)
        pilot.dump_tree(max_depth=max_depth)


@app.command()
def find(
    role: str | None = typer.Option(None, "--role", help="Widget role (e.g. 'push button')"),
    name: str | None = typer.Option(None, "--name", help="Widget name substring"),
    app_name: str | None = typer.Option(None, "--app", help="App name substring"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Find widgets by role and/or name."""
    if not role and not name:
        typer.echo("Error: specify at least --role or --name", err=True)
        raise typer.Exit(code=1)
    pilot = _get_pilot(app_name)
    widgets = pilot.find(role=role, name=name)
    if not widgets:
        typer.echo("No widgets found.", err=True)
        raise typer.Exit(code=1)
    if output_json:
        from qt_ai_dev_tools.state import get_extents, get_name, get_role, get_text
        items = []
        for w in widgets:
            ext = get_extents(w)
            items.append({
                "role": get_role(w), "name": get_name(w), "text": get_text(w),
                "extents": {"x": ext.x, "y": ext.y, "width": ext.width, "height": ext.height},
            })
        typer.echo(json.dumps(items, indent=2, ensure_ascii=False))
    else:
        from qt_ai_dev_tools.state import get_extents, get_name, get_role
        for w in widgets:
            ext = get_extents(w)
            typer.echo(f'[{get_role(w)}] "{get_name(w)}" @({ext.x},{ext.y} {ext.width}x{ext.height})')


@app.command(name="click")
def click_cmd(
    role: str = typer.Option(..., "--role", help="Widget role"),
    name: str | None = typer.Option(None, "--name", help="Widget name substring"),
    app_name: str | None = typer.Option(None, "--app", help="App name substring"),
) -> None:
    """Click a widget by role and optional name."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    pilot.click(widget)
    from qt_ai_dev_tools.state import get_name, get_role
    typer.echo(f'Clicked [{get_role(widget)}] "{get_name(widget)}"')


@app.command(name="type")
def type_cmd(
    text: str = typer.Argument(help="Text to type"),
    app_name: str | None = typer.Option(None, "--app", help="App name substring"),
) -> None:
    """Type text into the currently focused widget."""
    from qt_ai_dev_tools.interact import type_text
    type_text(text)
    typer.echo(f"Typed: {text}")


@app.command()
def key(
    key_name: str = typer.Argument(help="Key to press (e.g. Return, Tab, ctrl+a)"),
) -> None:
    """Press a key via xdotool."""
    from qt_ai_dev_tools.interact import press_key
    press_key(key_name)
    typer.echo(f"Pressed: {key_name}")


@app.command()
def focus(
    role: str = typer.Option(..., "--role", help="Widget role"),
    name: str | None = typer.Option(None, "--name", help="Widget name substring"),
    app_name: str | None = typer.Option(None, "--app", help="App name substring"),
) -> None:
    """Focus a widget by role and optional name."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    pilot.focus(widget)
    from qt_ai_dev_tools.state import get_name, get_role
    typer.echo(f'Focused [{get_role(widget)}] "{get_name(widget)}"')


@app.command()
def state(
    role: str = typer.Option(..., "--role", help="Widget role"),
    name: str | None = typer.Option(None, "--name", help="Widget name substring"),
    app_name: str | None = typer.Option(None, "--app", help="App name substring"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Read state of a widget (name, text, extents)."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    from qt_ai_dev_tools.state import get_extents, get_name, get_role, get_text
    ext = get_extents(widget)
    if output_json:
        typer.echo(json.dumps({
            "role": get_role(widget), "name": get_name(widget),
            "text": get_text(widget),
            "extents": {"x": ext.x, "y": ext.y, "width": ext.width, "height": ext.height},
        }, indent=2, ensure_ascii=False))
    else:
        typer.echo(f'[{get_role(widget)}] "{get_name(widget)}"')
        typer.echo(f"  text: {get_text(widget)}")
        typer.echo(f"  extents: ({ext.x},{ext.y} {ext.width}x{ext.height})")


@app.command()
def text(
    role: str = typer.Option(..., "--role", help="Widget role"),
    name: str | None = typer.Option(None, "--name", help="Widget name substring"),
    app_name: str | None = typer.Option(None, "--app", help="App name substring"),
) -> None:
    """Get text content of a widget."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    from qt_ai_dev_tools.state import get_text
    typer.echo(get_text(widget))


@app.command()
def screenshot(
    output: str = typer.Option("/tmp/screenshot.png", "--output", "-o", help="Output path"),
) -> None:
    """Take a screenshot of the Xvfb display."""
    from qt_ai_dev_tools.screenshot import take_screenshot
    path = take_screenshot(output)
    typer.echo(path)


@app.command()
def apps(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all AT-SPI accessible applications on the bus."""
    import gi  # type: ignore[import-untyped]
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi  # type: ignore[import-untyped]

    desktop = Atspi.get_desktop(0)
    app_list: list[str] = []
    for i in range(desktop.get_child_count()):
        c = desktop.get_child_at_index(i)
        if c:
            app_list.append(c.get_name() or "(unnamed)")
    if output_json:
        typer.echo(json.dumps(app_list, ensure_ascii=False))
    else:
        if not app_list:
            typer.echo("No apps found on AT-SPI bus.")
        else:
            for a in app_list:
                typer.echo(a)


@app.command()
def wait(
    app_name: str = typer.Option(..., "--app", help="App name substring to wait for"),
    timeout: int = typer.Option(10, "--timeout", help="Timeout in seconds"),
) -> None:
    """Wait for an app to appear on the AT-SPI bus."""
    import time

    import gi  # type: ignore[import-untyped]
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi  # type: ignore[import-untyped]

    start = time.time()
    while time.time() - start < timeout:
        desktop = Atspi.get_desktop(0)
        for i in range(desktop.get_child_count()):
            c = desktop.get_child_at_index(i)
            if c and app_name in (c.get_name() or ""):
                typer.echo(f"Found: {c.get_name()}")
                return
        time.sleep(0.5)
    typer.echo(f"Timeout: '{app_name}' not found after {timeout}s", err=True)
    raise typer.Exit(code=1)
```

- [ ] **Step 2: Create __main__.py**

```python
# src/qt_ai_dev_tools/__main__.py
"""Entry point for `python -m qt_ai_dev_tools`."""

from qt_ai_dev_tools.cli import app

app()
```

- [ ] **Step 3: Verify CLI help renders**

```bash
uv run qt-ai-dev-tools --help
uv run qt-ai-dev-tools tree --help
uv run qt-ai-dev-tools click --help
```

- [ ] **Step 4: Lint**

```bash
uv run ruff check --fix src/qt_ai_dev_tools/ && uv run ruff format src/qt_ai_dev_tools/
```

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py src/qt_ai_dev_tools/__main__.py
git commit -m "feat: add typer CLI with tree, find, click, type, key, focus, state, screenshot, apps, wait commands"
```

---

## Task 5: Update existing tests, add conftest

**Files:**
- Modify: `tests/test_main.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create conftest.py**

```python
# tests/conftest.py
"""Shared pytest fixtures."""
```

Empty for now — the existing tests use qtbot from pytest-qt which is auto-discovered.

- [ ] **Step 2: Update test_main.py imports**

Remove the `sys.path.insert` hack. The app module is still imported directly (it's not part of the package — it's the test subject).

Change:
```python
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import MainWindow
```

To:
```python
# app/ is not a package — add project root to path for test discovery
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.main import MainWindow
```

Also clean up the `__import__` hack for Qt.LeftButton — import it normally at the top:

```python
from PySide6.QtCore import Qt
```

Then replace `__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LeftButton` with `Qt.MouseButton.LeftButton` in both uses.

- [ ] **Step 3: Run existing tests to confirm nothing is broken**

```bash
uv run pytest tests/test_main.py -v -k "not atspi and not scrot" --override-ini="qt_qpa_platform=offscreen"
```

Expected: 5 tests pass (the offscreen ones).

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "refactor: clean up test imports, remove sys.path hack"
```

---

## Task 6: CLI integration tests

**Files:**
- Create: `tests/integration/test_cli.py`

These tests run the CLI as a subprocess and verify output/exit codes. They require the VM with a running Qt app (AT-SPI available). Mark them so they can be skipped in offscreen mode.

- [ ] **Step 1: Write CLI tests**

```python
# tests/integration/test_cli.py
"""Integration tests for the qt-ai-dev-tools CLI.

These tests require a running Qt app with AT-SPI available (DISPLAY set).
Run inside the Vagrant VM with `make test-full`.
"""

import os
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="DISPLAY not set — CLI tests require AT-SPI",
)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run qt-ai-dev-tools CLI and capture output."""
    return subprocess.run(
        ["uv", "run", "qt-ai-dev-tools", *args],
        capture_output=True,
        text=True,
        timeout=15,
    )


class TestCLIHelp:
    """CLI help renders without errors (no AT-SPI needed)."""

    @pytest.mark.skipif(False, reason="Always runs")
    def test_help(self) -> None:
        result = run_cli("--help")
        assert result.returncode == 0
        assert "qt-ai-dev-tools" in result.stdout.lower() or "usage" in result.stdout.lower()

    @pytest.mark.skipif(False, reason="Always runs")
    def test_tree_help(self) -> None:
        result = run_cli("tree", "--help")
        assert result.returncode == 0


class TestCLIApps:
    def test_apps_lists_something(self) -> None:
        result = run_cli("apps")
        assert result.returncode == 0


class TestCLITree:
    def test_tree_default(self) -> None:
        result = run_cli("tree")
        assert result.returncode == 0
        assert "[" in result.stdout  # should have role markers like [frame]

    def test_tree_with_role_filter(self) -> None:
        result = run_cli("tree", "--role", "push button")
        assert result.returncode == 0

    def test_tree_with_role_json(self) -> None:
        result = run_cli("tree", "--role", "push button", "--json")
        assert result.returncode == 0
        import json
        data = json.loads(result.stdout)
        assert isinstance(data, list)


class TestCLIFind:
    def test_find_by_role(self) -> None:
        result = run_cli("find", "--role", "push button")
        assert result.returncode == 0
        assert "push button" in result.stdout

    def test_find_no_args_fails(self) -> None:
        result = run_cli("find")
        assert result.returncode != 0


class TestCLIScreenshot:
    def test_screenshot_default(self) -> None:
        result = run_cli("screenshot")
        assert result.returncode == 0
        assert ".png" in result.stdout
```

- [ ] **Step 2: Run help tests locally (no VM needed)**

```bash
uv run pytest tests/integration/test_cli.py::TestCLIHelp -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_cli.py
git commit -m "test: add CLI integration tests"
```

---

## Task 7: Clean up PoC leftovers and update Makefile

**Files:**
- Delete: `scripts/qt_pilot.py`
- Delete: `pytest.ini`
- Modify: `Makefile`

- [ ] **Step 1: Delete replaced files**

```bash
git rm scripts/qt_pilot.py
git rm pytest.ini
```

- [ ] **Step 2: Update Makefile**

Add lint targets and update test commands to use the package:

```makefile
.PHONY: up provision ssh sync run test test-full screenshot destroy help status lint lint-fix

SHELL := /bin/bash
VM_RUN := ./scripts/vm-run.sh
SCREENSHOT := ./scripts/screenshot.sh

help: ## show this message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## start VM (first time: ~10 min)
	vagrant up --provider=libvirt
	chmod +x scripts/vm-run.sh scripts/screenshot.sh

sync: ## sync files to VM (rsync)
	vagrant rsync

provision: ## re-run provisioning
	vagrant provision

ssh: ## SSH into VM
	vagrant ssh

run: ## launch app in VM (headless)
	$(VM_RUN) "python3 /vagrant/app/main.py &"
	sleep 1
	$(SCREENSHOT) /tmp/app-running.png
	@echo "Screenshot: /tmp/app-running.png"

# ── Tests ────────────────────────────────────────────────────────────────────

test: ## fast pytest-qt tests (offscreen, no Xvfb)
	$(VM_RUN) "cd /vagrant && QT_QPA_PLATFORM=offscreen uv run pytest tests/test_main.py -v -k 'not atspi and not scrot'"

test-full: ## full tests including AT-SPI, screenshot, and CLI (requires Xvfb)
	$(VM_RUN) "cd /vagrant && uv run pytest tests/ -v"

test-atspi: ## AT-SPI smoke test only
	$(VM_RUN) "cd /vagrant && uv run pytest tests/ -v -k atspi"

test-cli: ## CLI integration tests only
	$(VM_RUN) "cd /vagrant && uv run pytest tests/integration/ -v"

# ── Lint ─────────────────────────────────────────────────────────────────────

lint: ## run linters (ruff check + basedpyright)
	uv run basedpyright src/
	uv run ruff check src/ tests/

lint-fix: ## run linters with auto-fix
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# ── Debug ─────────────────────────────────────────────────────────────────────

screenshot: ## screenshot current VM display
	$(SCREENSHOT) /tmp/vm-current.png

status: ## check Xvfb, openbox, AT-SPI status
	$(VM_RUN) "echo '=== Xvfb ===' && systemctl is-active xvfb && echo '=== Desktop session ===' && systemctl --user is-active desktop-session && echo '=== AT-SPI ===' && python3 -c 'import gi; gi.require_version(\"Atspi\",\"2.0\"); from gi.repository import Atspi; d=Atspi.get_desktop(0); print(f\"Apps on bus: {d.get_child_count()}\")'"

destroy: ## destroy VM and clean up
	vagrant destroy -f
	rm -f .vagrant-ssh-config
```

- [ ] **Step 3: Verify local lint and test targets work**

```bash
make lint-fix
uv run pytest tests/unit/ -v
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove PoC leftovers (qt_pilot.py, pytest.ini), update Makefile"
```

---

## Task 8: Update CLAUDE.md

**Files:**
- Modify: `AGENTS.md` (CLAUDE.md is a symlink to it)

- [ ] **Step 1: Update CLAUDE.md to reflect new package structure**

Update the "Quick orientation" and "Running things" sections to document:
- New package location `src/qt_ai_dev_tools/`
- CLI usage examples
- Updated make targets (lint, test-cli)
- Remove references to `scripts/qt_pilot.py`

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update CLAUDE.md for new package structure and CLI"
```

---

## Summary of PoC leftovers to clean up

| Leftover | Action | Task |
|----------|--------|------|
| `scripts/qt_pilot.py` | Delete — replaced by `src/qt_ai_dev_tools/` | Task 7 |
| `pytest.ini` | Delete — config moved to `pyproject.toml` | Task 7 |
| `sys.path.insert` hack in tests | Replace with clean import | Task 5 |
| `__import__("PySide6.QtCore")` hack | Replace with normal import | Task 5 |
| Makefile using raw pytest | Update to use `uv run pytest` | Task 7 |
| No .gitignore | Add standard Python .gitignore | Task 1 |
| No linting config | Add ruff + basedpyright via pyproject.toml | Task 1 |
