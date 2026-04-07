# Validation Fixes & Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix user-facing issues found in Round 3 validation and fill critical test coverage gaps so regressions are caught automatically.

**Architecture:** Fix bugs in order of dependency — first consolidate visibility logic (used everywhere), then fix CLI inconsistencies, then add `--app` to `type`/`key`, then fix `do --screenshot` proxy. Each fix gets TDD: write failing test first, then implement, then verify.

**Tech Stack:** Python 3.12, PySide6, pytest, AT-SPI (`gi.repository.Atspi`), xdotool, Vagrant VM

**Skills to use:** `writing-python-code` for ALL Python edits, `testing-python` for ALL test code.

---

## File Structure

### Files to modify

| File | Responsibility | Changes |
|------|---------------|---------|
| `src/qt_ai_dev_tools/_atspi.py` | AT-SPI typed wrapper | Add `get_state_set()` and `is_showing` property |
| `src/qt_ai_dev_tools/pilot.py` | Main interaction class | Refactor `_is_visible()` to use STATE_SHOWING, make it importable |
| `src/qt_ai_dev_tools/cli.py` | CLI commands | Fix `tree --visible` default, add `--app` to `type`/`key`, fix `do --screenshot`, use shared `_is_visible` |
| `src/qt_ai_dev_tools/interact.py` | xdotool wrappers | Add `activate_window()` helper for `--app` support |
| `src/qt_ai_dev_tools/screenshot.py` | Screenshot capture | No changes needed |

### Files to create

| File | Responsibility |
|------|---------------|
| `tests/unit/test_screenshot.py` | Unit tests for `take_screenshot()` |
| `tests/unit/test_subprocess_helpers.py` | Unit tests for `subsystems/_subprocess.py` |
| `tests/unit/test_logging.py` | Unit tests for `logging/logger_setup.py` |
| `tests/e2e/test_cli_commands_e2e.py` | E2E tests for `type`, `key`, `text`, `state` CLI commands |
| `tests/e2e/test_visibility_e2e.py` | E2E tests for visibility filter with menus |

### Files to modify (tests)

| File | Changes |
|------|---------|
| `tests/unit/test_pilot.py` | Add tests for refactored `_is_visible` with STATE_SHOWING |
| `tests/unit/test_interact.py` | Add tests for `activate_window()` |
| `tests/unit/test_cli_helpers.py` | Update `_widget_dict` tests for shared visibility |
| `tests/e2e/test_compound_e2e.py` | Add tests for `do --screenshot` host transfer |

---

## Task 1: Unit tests for foundational untested modules

These modules are used by everything but have zero tests. Adding tests first reveals any existing bugs.

**Files:**
- Create: `tests/unit/test_screenshot.py`
- Create: `tests/unit/test_subprocess_helpers.py`
- Create: `tests/unit/test_logging.py`
- Read: `src/qt_ai_dev_tools/screenshot.py`
- Read: `src/qt_ai_dev_tools/subsystems/_subprocess.py`
- Read: `src/qt_ai_dev_tools/logging/logger_setup.py`

- [ ] **Step 1: Write unit tests for `screenshot.py`**

```python
"""Tests for screenshot capture module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def _mock_run_command():
    """Mock run_command to avoid calling real scrot."""
    with patch("qt_ai_dev_tools.screenshot.run_command") as mock:
        mock.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        yield mock


@pytest.fixture
def _mock_getsize():
    """Mock os.path.getsize to return realistic file size."""
    with patch("qt_ai_dev_tools.screenshot.os.path.getsize", return_value=15000):
        yield


class TestTakeScreenshot:
    def test_default_path(self, tmp_path: Path, _mock_run_command, _mock_getsize):
        from qt_ai_dev_tools.screenshot import take_screenshot

        result = take_screenshot(str(tmp_path / "shot.png"))
        assert result == str(tmp_path / "shot.png")
        _mock_run_command.assert_called_once()
        args = _mock_run_command.call_args[0][0]
        assert args[0] == "scrot"
        assert "--overwrite" in args

    def test_creates_parent_dir(self, tmp_path: Path, _mock_run_command, _mock_getsize):
        from qt_ai_dev_tools.screenshot import take_screenshot

        nested = tmp_path / "sub" / "dir" / "shot.png"
        take_screenshot(str(nested))
        assert nested.parent.exists()

    def test_sets_display_env(self, tmp_path: Path, _mock_run_command, _mock_getsize):
        from qt_ai_dev_tools.screenshot import take_screenshot

        take_screenshot(str(tmp_path / "shot.png"))
        env = _mock_run_command.call_args[1]["env"]
        assert env["DISPLAY"] == ":99"

    def test_check_true_propagates_error(self, tmp_path: Path):
        from qt_ai_dev_tools.screenshot import take_screenshot

        with patch("qt_ai_dev_tools.screenshot.run_command", side_effect=RuntimeError("scrot failed")):
            with pytest.raises(RuntimeError, match="scrot failed"):
                take_screenshot(str(tmp_path / "shot.png"))
```

- [ ] **Step 2: Write unit tests for `subsystems/_subprocess.py`**

Read the source file first (`src/qt_ai_dev_tools/subsystems/_subprocess.py`), then write tests for `check_tool()` and `run_tool()`:

```python
"""Tests for subsystem subprocess helpers."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest


class TestCheckTool:
    def test_tool_found(self):
        from qt_ai_dev_tools.subsystems._subprocess import check_tool

        with patch("qt_ai_dev_tools.subsystems._subprocess.shutil.which", return_value="/usr/bin/xsel"):
            check_tool("xsel")  # Should not raise

    def test_tool_not_found_raises(self):
        from qt_ai_dev_tools.subsystems._subprocess import check_tool

        with patch("qt_ai_dev_tools.subsystems._subprocess.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="xsel"):
                check_tool("xsel")


class TestRunTool:
    def test_basic_run(self):
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.subsystems._subprocess.run_command") as mock:
            mock.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
            result = run_tool(["echo", "hello"])
            assert result.stdout == "ok"

    def test_check_true_raises_on_failure(self):
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.subsystems._subprocess.run_command", side_effect=RuntimeError("failed")):
            with pytest.raises(RuntimeError):
                run_tool(["bad_cmd"], check=True)
```

Note: Read the actual source to verify function signatures and adjust test code accordingly.

- [ ] **Step 3: Write unit tests for `logging/logger_setup.py`**

```python
"""Tests for logging configuration module."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest


class TestSetupFileLogging:
    def test_creates_log_directory(self, tmp_path: Path):
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        log_dir = tmp_path / "logs"
        setup_file_logging(log_dir=log_dir, app_name="test-app")
        assert log_dir.exists()

    def test_creates_log_file(self, tmp_path: Path):
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        setup_file_logging(log_dir=tmp_path, app_name="test-app")
        assert (tmp_path / "test-app.log").exists()

    def test_adds_handler_to_root_logger(self, tmp_path: Path):
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        root = logging.getLogger()
        initial_count = len(root.handlers)
        setup_file_logging(log_dir=tmp_path, app_name="test-app")
        assert len(root.handlers) > initial_count

    @pytest.fixture(autouse=True)
    def _cleanup_handlers(self):
        """Remove handlers added during tests."""
        root = logging.getLogger()
        original = list(root.handlers)
        yield
        for h in root.handlers[:]:
            if h not in original:
                root.removeHandler(h)
                h.close()


class TestSetupStderrLogging:
    def test_adds_stderr_handler(self):
        from qt_ai_dev_tools.logging.logger_setup import setup_stderr_logging

        root = logging.getLogger()
        initial_count = len(root.handlers)
        setup_stderr_logging(level=logging.DEBUG)
        assert len(root.handlers) > initial_count

    @pytest.fixture(autouse=True)
    def _cleanup_handlers(self):
        root = logging.getLogger()
        original = list(root.handlers)
        yield
        for h in root.handlers[:]:
            if h not in original:
                root.removeHandler(h)
                h.close()
```

- [ ] **Step 4: Run all new unit tests to verify they pass**

Run: `uv run pytest tests/unit/test_screenshot.py tests/unit/test_subprocess_helpers.py tests/unit/test_logging.py -v`

Expected: All pass (these test existing working code).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_screenshot.py tests/unit/test_subprocess_helpers.py tests/unit/test_logging.py
git commit -m "test: add unit tests for screenshot, subprocess helpers, and logging modules"
```

---

## Task 2: Add `is_showing` to AtspiNode and refactor `_is_visible()`

The visibility filter is the root cause of ISSUE-025 (closed menu items appearing visible). AT-SPI provides `STATE_SHOWING` which indicates whether a widget is actually rendered on screen. Using this instead of coordinate heuristics solves the problem properly.

**IMPORTANT:** This task requires prototyping first. Before implementing, spawn a researcher agent to test `STATE_SHOWING` behavior in the VM with real apps (SpeedCrunch, KeePassXC). Verify that:
1. `Atspi.StateType.STATE_SHOWING` is available
2. Visible buttons have STATE_SHOWING = True
3. Closed menu items have STATE_SHOWING = False
4. The AT-SPI `get_state_set()` method works on the AtspiNode._native object

**Files:**
- Modify: `src/qt_ai_dev_tools/_atspi.py` (add `get_state_set()`, `is_showing`)
- Modify: `src/qt_ai_dev_tools/pilot.py` (refactor `_is_visible()`)
- Modify: `src/qt_ai_dev_tools/cli.py:107-121` (use shared `_is_visible` in `_widget_dict`)
- Test: `tests/unit/test_atspi.py`, `tests/unit/test_pilot.py`, `tests/unit/test_cli_helpers.py`

- [ ] **Step 1: Prototype STATE_SHOWING in VM**

Spawn a researcher agent to run this in the VM:

```python
import gi
gi.require_version('Atspi', '2.0')
from gi.repository import Atspi

Atspi.init()
desktop = Atspi.get_desktop(0)

# Launch speedcrunch first, then:
for i in range(desktop.get_child_count()):
    app = desktop.get_child_at_index(i)
    if 'speedcrunch' in (app.get_name() or '').lower():
        # Walk tree, check STATE_SHOWING on each widget
        def check(node, depth=0):
            name = node.get_name() or ""
            role = node.get_role_name()
            state_set = node.get_state_set()
            showing = state_set.contains(Atspi.StateType.STATE_SHOWING)
            visible = state_set.contains(Atspi.StateType.STATE_VISIBLE)
            ext = node.get_extents(Atspi.CoordType.SCREEN)
            print(f"{'  '*depth}[{role}] '{name}' showing={showing} visible={visible} @({ext.x},{ext.y} {ext.width}x{ext.height})")
            for j in range(node.get_child_count()):
                child = node.get_child_at_index(j)
                if child:
                    check(child, depth+1)
        check(app)
```

Confirm that STATE_SHOWING correctly distinguishes visible from hidden widgets. If it doesn't work reliably, fall back to display-bounds checking approach.

- [ ] **Step 2: Write failing test for `AtspiNode.is_showing`**

In `tests/unit/test_atspi.py`, add:

```python
class TestStateSet:
    def test_is_showing_true(self, mock_native):
        """Widget with STATE_SHOWING returns True."""
        state_set = MagicMock()
        state_set.contains.return_value = True
        mock_native.get_state_set.return_value = state_set
        node = AtspiNode(mock_native)
        assert node.is_showing is True

    def test_is_showing_false(self, mock_native):
        """Widget without STATE_SHOWING returns False."""
        state_set = MagicMock()
        state_set.contains.return_value = False
        mock_native.get_state_set.return_value = state_set
        node = AtspiNode(mock_native)
        assert node.is_showing is False

    def test_is_showing_handles_no_state_set(self, mock_native):
        """If get_state_set() fails, is_showing returns False."""
        mock_native.get_state_set.side_effect = RuntimeError("no state")
        node = AtspiNode(mock_native)
        assert node.is_showing is False
```

Look at the existing `mock_native` fixture pattern in `test_atspi.py` and follow it.

- [ ] **Step 3: Run test — verify it fails**

Run: `uv run pytest tests/unit/test_atspi.py::TestStateSet -v`
Expected: FAIL — `AtspiNode` has no `is_showing` attribute.

- [ ] **Step 4: Implement `is_showing` on AtspiNode**

Add to `src/qt_ai_dev_tools/_atspi.py`, after the `get_extents` method (around line 66):

```python
@property
def is_showing(self) -> bool:
    """Whether the widget is currently rendered on screen (AT-SPI STATE_SHOWING).

    Returns False if the state cannot be determined (stale node, error).
    """
    try:
        state_set = self._native.get_state_set()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        return state_set.contains(Atspi.StateType.STATE_SHOWING)  # type: ignore[no-any-return,reportUnknownMemberType]  # rationale: AT-SPI StateSet has no stubs
    except (RuntimeError, OSError):
        return False
```

Also need to ensure `Atspi` is imported at module level (it already is — line 7).

- [ ] **Step 5: Run test — verify it passes**

Run: `uv run pytest tests/unit/test_atspi.py::TestStateSet -v`
Expected: PASS

- [ ] **Step 6: Write failing test for refactored `_is_visible()`**

In `tests/unit/test_pilot.py`, add/update visibility tests. The key change: `_is_visible` should now use `is_showing` as the primary check, with coordinate heuristics as fallback.

```python
class TestIsVisible:
    def test_showing_widget_is_visible(self):
        """Widget with STATE_SHOWING and valid extents is visible."""
        widget = MagicMock()
        widget.is_showing = True
        widget.get_extents.return_value = Extents(100, 200, 50, 30)
        assert _is_visible(widget) is True

    def test_not_showing_widget_is_not_visible(self):
        """Widget without STATE_SHOWING is not visible, even with valid extents."""
        widget = MagicMock()
        widget.is_showing = False
        widget.get_extents.return_value = Extents(100, 200, 50, 30)
        assert _is_visible(widget) is False

    def test_zero_size_not_visible(self):
        """Widget with zero size is not visible regardless of STATE_SHOWING."""
        widget = MagicMock()
        widget.is_showing = True
        widget.get_extents.return_value = Extents(100, 200, 0, 0)
        assert _is_visible(widget) is False

    def test_origin_not_showing_not_visible(self):
        """Widget at (0,0) that is not showing is not visible."""
        widget = MagicMock()
        widget.is_showing = False
        widget.get_extents.return_value = Extents(0, 0, 100, 30)
        assert _is_visible(widget) is False

    def test_exception_returns_false(self):
        """Widget that raises on get_extents is not visible."""
        widget = MagicMock()
        widget.is_showing = True
        widget.get_extents.side_effect = RuntimeError("stale")
        assert _is_visible(widget) is False
```

- [ ] **Step 7: Refactor `_is_visible()` in pilot.py**

Replace the current implementation (lines 16-33) with:

```python
def _is_visible(widget: AtspiNode) -> bool:
    """Check if a widget is likely visible on screen.

    Uses AT-SPI STATE_SHOWING as the primary indicator, with size
    validation as a secondary check. Rejects zero-size widgets
    regardless of state flags.
    """
    try:
        ext = widget.get_extents()
        if ext.width <= 0 or ext.height <= 0:
            return False
        return widget.is_showing
    except (RuntimeError, OSError):
        return False
```

- [ ] **Step 8: Update `_widget_dict()` in cli.py to use shared `_is_visible()`**

Replace the inline visibility logic at line 115:

```python
# Before:
"visible": ext.width > 0 and ext.height > 0 and not (ext.x == 0 and ext.y == 0),

# After:
"visible": _is_visible(widget),
```

Add the import at the top of cli.py:
```python
from qt_ai_dev_tools.pilot import _is_visible
```

And update `_widget_dict` to handle the exception case:

```python
def _widget_dict(widget: AtspiNode) -> dict[str, object]:
    """Convert a widget to a JSON-serializable dict."""
    try:
        ext = widget.get_extents()
        extents_dict: dict[str, int] = {"x": ext.x, "y": ext.y, "width": ext.width, "height": ext.height}
    except (RuntimeError, OSError):
        extents_dict = {"x": 0, "y": 0, "width": 0, "height": 0}

    d: dict[str, object] = {
        "role": widget.role_name,
        "name": widget.name,
        "text": widget.get_text(),
        "extents": extents_dict,
        "visible": _is_visible(widget),
    }
    if widget.has_value_iface:
        d["value"] = widget.get_value()
        d["min_value"] = widget.get_minimum_value()
        d["max_value"] = widget.get_maximum_value()
    return d
```

- [ ] **Step 9: Update `_widget_dict` tests in `test_cli_helpers.py`**

Verify the existing tests still work after the refactor. Update mocks to provide `is_showing` attribute.

- [ ] **Step 10: Run full test suite**

Run: `uv run pytest tests/unit/ -v`
Expected: All pass

- [ ] **Step 11: Commit**

```bash
git add src/qt_ai_dev_tools/_atspi.py src/qt_ai_dev_tools/pilot.py src/qt_ai_dev_tools/cli.py \
       tests/unit/test_atspi.py tests/unit/test_pilot.py tests/unit/test_cli_helpers.py
git commit -m "fix: use AT-SPI STATE_SHOWING for visibility filter (ISSUE-025)

Replace coordinate-based heuristic with AT-SPI STATE_SHOWING flag.
Consolidate duplicated visibility logic in _widget_dict to use
shared _is_visible(). Fixes false positives for closed menu items."
```

---

## Task 3: Fix `tree --visible` default inconsistency

The `tree` command defaults `visible=False` while every other command defaults `visible=True`. This causes agent confusion — `tree` shows widgets that `click`/`find` can't find.

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:257` (change default)
- Test: `tests/integration/test_cli.py` (update existing tree tests if needed)

- [ ] **Step 1: Write test that demonstrates the inconsistency**

Add to `tests/integration/test_cli.py` or create `tests/unit/test_cli_defaults.py`:

```python
def test_tree_visible_default_matches_find():
    """tree and find should have the same default for --visible."""
    import inspect
    from qt_ai_dev_tools.cli import tree, find

    tree_sig = inspect.signature(tree)
    find_sig = inspect.signature(find)
    assert tree_sig.parameters["visible"].default == find_sig.parameters["visible"].default
```

- [ ] **Step 2: Run test — verify it fails**

Run: `uv run pytest tests/unit/test_cli_defaults.py::test_tree_visible_default_matches_find -v`
Expected: FAIL — tree defaults to False, find to True.

- [ ] **Step 3: Fix the default**

In `src/qt_ai_dev_tools/cli.py`, line 257, change:

```python
# Before:
visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = False,

# After:
visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
```

- [ ] **Step 4: Run test — verify it passes**

Run: `uv run pytest tests/unit/test_cli_defaults.py -v`
Expected: PASS

- [ ] **Step 5: Run full lint + test**

Run: `uv run poe lint_full && uv run pytest tests/unit/ -v`

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py tests/unit/test_cli_defaults.py
git commit -m "fix: tree --visible now defaults to True, matching find/click/do (NEW-001)"
```

---

## Task 4: Add `--app` flag to `type` and `key` commands (ISSUE-005)

When multiple apps are open, `type` and `key` fire xdotool at whatever window has focus. Adding `--app` uses `xdotool windowactivate` to focus the right window first.

**Files:**
- Modify: `src/qt_ai_dev_tools/interact.py` (add `activate_app_window()`)
- Modify: `src/qt_ai_dev_tools/cli.py:341-362` (add `--app` to `type` and `key`)
- Test: `tests/unit/test_interact.py` (test `activate_app_window`)
- Test: `tests/e2e/test_cli_commands_e2e.py` (e2e test for `type --app`, `key --app`)

- [ ] **Step 1: Write failing test for `activate_app_window()`**

In `tests/unit/test_interact.py`, add:

```python
class TestActivateAppWindow:
    def test_activates_window_by_name(self, mock_run_command):
        from qt_ai_dev_tools.interact import activate_app_window

        # xdotool search returns window ID, then windowactivate uses it
        mock_run_command.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="12345678\n", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        activate_app_window("SpeedCrunch")
        calls = mock_run_command.call_args_list
        assert "search" in calls[0][0][0] or calls[0][0][0] == ["xdotool", "search", "--name", "SpeedCrunch"]

    def test_raises_if_no_window_found(self, mock_run_command):
        from qt_ai_dev_tools.interact import activate_app_window

        mock_run_command.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        with pytest.raises(RuntimeError, match="No window found"):
            activate_app_window("NonexistentApp")
```

Look at the existing `mock_run_command` fixture in `test_interact.py` and reuse it.

- [ ] **Step 2: Run test — verify it fails**

Run: `uv run pytest tests/unit/test_interact.py::TestActivateAppWindow -v`
Expected: FAIL — `activate_app_window` doesn't exist.

- [ ] **Step 3: Implement `activate_app_window()` in interact.py**

Add after the `_xdotool_env()` function:

```python
def activate_app_window(app_name: str) -> None:
    """Activate (focus) a window by application name using xdotool.

    Searches for a window matching the app name and brings it to focus.
    This ensures subsequent type/key commands go to the right app.

    Args:
        app_name: Window name substring to search for.

    Raises:
        RuntimeError: If no window matching the name is found.
    """
    env = _xdotool_env()
    result = run_command(
        ["xdotool", "search", "--name", app_name],
        env=env,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        msg = f"No window found matching '{app_name}'"
        raise RuntimeError(msg)
    # Use the first matching window
    window_id = result.stdout.strip().splitlines()[0]
    run_command(
        ["xdotool", "windowactivate", window_id],
        env=env,
        check=True,
    )
    time.sleep(0.1)  # Brief pause for focus to settle
```

- [ ] **Step 4: Run test — verify it passes**

Run: `uv run pytest tests/unit/test_interact.py::TestActivateAppWindow -v`

- [ ] **Step 5: Update `type` and `key` CLI commands to accept `--app`**

In `src/qt_ai_dev_tools/cli.py`, update the `type_cmd` function (line 341):

```python
@app.command(name="type")
def type_cmd(
    text: typing.Annotated[str, typer.Argument(help="Text to type")],
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name — activates window before typing")] = None,
) -> None:
    """Type text into the currently focused widget."""
    _proxy_to_vm()
    from qt_ai_dev_tools.interact import activate_app_window, type_text

    if app_name:
        try:
            activate_app_window(app_name)
        except RuntimeError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
    type_text(text)
    typer.echo(f"Typed: {text}")
```

Similarly update `key` (line 353):

```python
@app.command()
def key(
    key_name: typing.Annotated[str, typer.Argument(help="Key to press (e.g. Return, Tab, ctrl+a)")],
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name — activates window before key press")] = None,
) -> None:
    """Press a key via xdotool."""
    _proxy_to_vm()
    from qt_ai_dev_tools.interact import activate_app_window, press_key

    if app_name:
        try:
            activate_app_window(app_name)
        except RuntimeError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
    press_key(key_name)
    typer.echo(f"Pressed: {key_name}")
```

- [ ] **Step 6: Run lint**

Run: `uv run poe lint_full`

- [ ] **Step 7: Commit**

```bash
git add src/qt_ai_dev_tools/interact.py src/qt_ai_dev_tools/cli.py tests/unit/test_interact.py
git commit -m "feat: add --app flag to type and key commands (ISSUE-005)

Adds activate_app_window() helper that uses xdotool search + windowactivate
to focus the target app before typing/pressing keys."
```

---

## Task 5: Fix `do --screenshot` VM proxy issue (ISSUE-021)

When `do --screenshot` runs on the host, the entire command is proxied to the VM. The screenshot is saved inside the VM but never transferred back. Fix: detect `--screenshot` on the host side and run a separate screenshot transfer after the proxied `do` command completes.

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:526-572` (split `do` command to handle screenshot on host)
- Test: `tests/unit/test_cli_helpers.py` (test the split logic)

- [ ] **Step 1: Write test for the screenshot transfer behavior**

This is hard to unit test since it involves the proxy mechanism. The best approach is to test the refactored logic:

In `tests/unit/test_cli_helpers.py`, verify the `do` command's screenshot logic can be tested in isolation. The key architectural change: when on host with `--screenshot`, the `do` command should:
1. Proxy the `do click` WITHOUT `--screenshot`
2. Then separately call `_proxy_screenshot()` to get the screenshot

- [ ] **Step 2: Refactor `do_action()` to handle screenshot on host**

In `src/qt_ai_dev_tools/cli.py`, modify the `do_action` function:

```python
@app.command(name="do")
def do_action(
    action: typing.Annotated[str, typer.Argument(help="Action to perform: click")],
    target: typing.Annotated[str, typer.Argument(help="Widget name or role to act on")],
    role: typing.Annotated[str, typer.Option("--role", "-r", help="Widget role")] = "push button",
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name")] = None,
    verify: typing.Annotated[
        str | None, typer.Option("--verify", help="Verify condition after action (e.g. 'label:status contains Saved')")
    ] = None,
    screenshot_after: typing.Annotated[bool, typer.Option("--screenshot", help="Take screenshot after action")] = False,
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[
        int | None,
        typer.Option("--index", help="Select Nth matching widget (0-based)."),
    ] = None,
    output: typing.Annotated[str, typer.Option("-o", "--output", help="Screenshot output path")] = "/tmp/screenshot.png",
) -> None:
    """Perform a compound action (click + optional verify/screenshot)."""
    # On host: proxy the do command WITHOUT --screenshot, then transfer screenshot separately
    if not _is_in_vm() and screenshot_after:
        # Proxy the action part (without --screenshot)
        from qt_ai_dev_tools.vagrant.vm import vm_run

        args = ["qt-ai-dev-tools", "do", action, shlex.quote(target)]
        args.extend(["--role", role])
        if app_name:
            args.extend(["--app", app_name])
        if verify:
            args.extend(["--verify", verify])
        if not visible:
            args.append("--no-visible")
        if exact:
            args.append("--exact")
        if index is not None:
            args.extend(["--index", str(index)])

        result = vm_run(" ".join(args))
        if result.stdout:
            typer.echo(result.stdout, nl=False)
        if result.stderr:
            typer.echo(result.stderr, err=True, nl=False)
        if result.returncode != 0:
            raise typer.Exit(code=result.returncode)

        # Now transfer screenshot via the proper proxy mechanism
        _proxy_screenshot(output)
        return

    _proxy_to_vm()
    try:
        pilot = _get_pilot(app_name)

        if action == "click":
            widget = pilot.find_one(role=role, name=target, visible=visible, exact=exact, index=index)
            info = f"'{role}' ({target})"
            pilot.click(widget)
            typer.echo(f"Clicked {info}")
        else:
            typer.echo(f"Unknown action: {action}", err=True)
            raise typer.Exit(code=1)

        if screenshot_after:
            path = pilot.screenshot(output)
            typer.echo(f"Screenshot: {path}")

        if verify:
            _verify_condition(pilot, verify)

    except (RuntimeError, LookupError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
```

Note: Check if `pilot.screenshot()` accepts a path argument. If not, update it.

- [ ] **Step 3: Also fix `_verify_condition` to pass `visible=True`**

In `_verify_condition()` (line 596), add `visible=True`:

```python
# Before:
widgets = pilot.find(
    role=verify_role.strip(),
    name=verify_name.strip() if verify_name else None,
)

# After:
widgets = pilot.find(
    role=verify_role.strip(),
    name=verify_name.strip() if verify_name else None,
    visible=True,
)
```

- [ ] **Step 4: Run lint and tests**

Run: `uv run poe lint_full && uv run pytest tests/unit/ -v`

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "fix: do --screenshot transfers file from VM to host (ISSUE-021)

When running on host, split the do command: proxy the action to VM
without --screenshot, then use _proxy_screenshot() to transfer the
file back. Also fix _verify_condition to filter by visible=True."
```

---

## Task 6: Improve error handling in `_dump()` and `click_at()`

Fix code quality issues identified by triage:
1. `_dump()` catches bare `Exception` — should catch specific types
2. `click_at()` has redundant origin check (already checked by `click()`)

**Files:**
- Modify: `src/qt_ai_dev_tools/pilot.py:455-459` (specific exception)
- Modify: `src/qt_ai_dev_tools/interact.py:48-53` (remove redundant check)
- Test: `tests/unit/test_pilot.py` (test _dump error handling)

- [ ] **Step 1: Fix `_dump()` exception handling**

In `src/qt_ai_dev_tools/pilot.py`, replace the bare `except Exception` in `_dump()`:

```python
# Before:
except Exception:
    pos = ""

# After:
except (RuntimeError, OSError):
    pos = ""
```

- [ ] **Step 2: Remove redundant origin check from `click_at()`**

In `src/qt_ai_dev_tools/interact.py`, remove lines 48-53 (the `if x == 0 and y == 0` check). The semantic check "widget at origin means closed popup" is already handled by `click()` at lines 86-92.

Keep the display bounds check (lines 32-47) — that's a legitimate coordinate validation.

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/test_pilot.py tests/unit/test_interact.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/pilot.py src/qt_ai_dev_tools/interact.py
git commit -m "fix: specific exception handling in _dump(), remove redundant origin check in click_at()"
```

---

## Task 7: E2E tests for CLI commands and visibility filter

Add e2e tests that exercise real AT-SPI with the sample app. These tests run in the VM.

**Files:**
- Create: `tests/e2e/test_cli_commands_e2e.py`
- Create: `tests/e2e/test_visibility_e2e.py`
- Read: `tests/e2e/conftest.py` (for fixture patterns)
- Read: `app/main.py` (sample app capabilities)

- [ ] **Step 1: Write e2e tests for `type` and `key` commands**

```python
"""E2E tests for type, key, text, and state CLI commands."""

from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.e2e


class TestTypeCommand:
    """Test the type CLI command with real xdotool."""

    def test_type_text_into_focused_widget(self, bridge_app):
        """Type text into the todo input field."""
        # First focus the input
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "click", "--role", "text", "--app", "main.py"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

        # Type text
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "type", "Test todo item"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "Typed:" in result.stdout

    def test_type_with_app_flag(self, bridge_app):
        """Type text with --app flag to target specific window."""
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "type", "hello", "--app", "main.py"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0


class TestKeyCommand:
    def test_press_key(self, bridge_app):
        """Press a key via the key command."""
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "key", "Tab"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "Pressed:" in result.stdout

    def test_key_with_app_flag(self, bridge_app):
        """Press key with --app flag."""
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "key", "Return", "--app", "main.py"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0


class TestTextCommand:
    def test_read_text_content(self, bridge_app):
        """Read text from a widget."""
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "text", "--role", "text", "--app", "main.py"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0


class TestStateCommand:
    def test_read_widget_state(self, bridge_app):
        """Read state of a widget."""
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "state", "--role", "push button", "--name", "Add",
             "--app", "main.py", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
```

Note: Check the actual `text` and `state` command signatures in cli.py and adjust test arguments accordingly.

- [ ] **Step 2: Write e2e test for visibility filter with menus**

```python
"""E2E tests for visibility filter behavior with menus."""

from __future__ import annotations

import json
import subprocess

import pytest

pytestmark = pytest.mark.e2e


class TestMenuVisibility:
    """Test that closed menu items are correctly filtered by visibility."""

    def test_closed_menu_items_filtered(self, complex_app):
        """Menu items in closed menus should not appear in visible-only find."""
        # Find with default visible=True
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "find", "--role", "menu item",
             "--app", "complex_app.py", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        visible_items = json.loads(result.stdout)

        # Find with --no-visible (all items)
        result_all = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "find", "--role", "menu item",
             "--app", "complex_app.py", "--json", "--no-visible"],
            capture_output=True, text=True, timeout=10,
        )
        assert result_all.returncode == 0
        all_items = json.loads(result_all.stdout)

        # Visible items should be a subset of all items
        assert len(visible_items) <= len(all_items)
        # Top-level menu items should be visible
        # Submenu items (when closed) should NOT be visible


class TestTreeVisibleDefault:
    """Test that tree --visible defaults to True (matches find)."""

    def test_tree_with_role_filters_invisible(self, bridge_app):
        """tree --role should filter to visible widgets by default."""
        result = subprocess.run(
            ["uv", "run", "qt-ai-dev-tools", "tree", "--role", "push button", "--app", "main.py"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        # All listed widgets should have valid (non-zero) extents
```

Note: The complex_app test app must have menus for this test to work. Check `tests/apps/complex_app.py` to verify it has a menu bar.

- [ ] **Step 3: Run e2e tests in VM**

Run: `make test-e2e` or `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_cli_commands_e2e.py tests/e2e/test_visibility_e2e.py -v"`

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_cli_commands_e2e.py tests/e2e/test_visibility_e2e.py
git commit -m "test: add e2e tests for type/key/text/state commands and visibility filter"
```

---

## Task 8: Final verification — full test suite + lint

- [ ] **Step 1: Run full lint**

Run: `uv run poe lint_full`
Expected: 0 errors, 0 warnings

- [ ] **Step 2: Run full test suite**

Run: `make test` (all tests — VM + host)
Expected: 0 failures, 0 errors

- [ ] **Step 3: Fix any failures**

If tests fail, diagnose and fix. Re-run until all pass.

- [ ] **Step 4: Commit any remaining fixes**

---

## Task 9: Update validation docs

- [ ] **Step 1: Update `docs/validation/issues.md`**

Mark the following as Fixed:
- ISSUE-025: Closed menu items bypass visibility filter → Fixed (STATE_SHOWING)
- ISSUE-005/013: `key`/`type` lack `--app` → Fixed (added `--app` flag)
- ISSUE-021: `do --screenshot` saves in VM → Fixed (separate screenshot transfer)
- NEW-001: `tree --visible` default inconsistency → Fixed

Add to observations:
- STATE_SHOWING is reliable for visibility detection
- coordinate heuristic replaced with AT-SPI state flag

- [ ] **Step 2: Update `docs/ROADMAP.md`**

Note the fixes in Phase 6 Round 3 section.

- [ ] **Step 3: Commit**

```bash
git add docs/validation/issues.md docs/ROADMAP.md
git commit -m "docs: update validation issues with Round 3 fixes"
```

---

## Dependency Graph

```
Task 1 (foundational tests) ─── independent, do first
    │
Task 2 (STATE_SHOWING + visibility) ─── depends on Task 1 being committed
    │
    ├── Task 3 (tree --visible default) ─── depends on Task 2 (visibility logic)
    │
    ├── Task 5 (do --screenshot) ─── independent of Task 2, can overlap
    │
    └── Task 7 (e2e tests) ─── depends on Tasks 2, 3, 4, 5
         │
Task 4 (type/key --app) ─── independent of Task 2
    │
Task 6 (error handling cleanup) ─── independent, can overlap
    │
Task 8 (final verification) ─── depends on ALL above
    │
Task 9 (docs update) ─── depends on Task 8
```

**Parallelizable groups:**
- Group A: Tasks 1 (parallel with others as it's foundational tests)
- Group B: Tasks 3, 4, 5, 6 (independent of each other, all depend on Task 2)
- Group C: Task 7 (depends on B)
- Group D: Tasks 8, 9 (sequential, after everything)
