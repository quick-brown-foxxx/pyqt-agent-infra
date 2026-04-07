# Round 2 Validation Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Use `writing-python-code` and `testing-python` skills for all code.

**Goal:** Fix 7 issues (ISSUE-015 through ISSUE-023, excluding ISSUE-018/021/024) discovered during Round 2 real-world validation, with e2e tests written first (TDD).

**Architecture:** Tests first to prove bugs exist, then minimal fixes. Group related CLI changes together. Extract desktop-session startup to a script to fix systemd quoting.

**Tech Stack:** Python 3.12, basedpyright strict, pytest, AT-SPI (gi.repository.Atspi), typer CLI, systemd, D-Bus

**Skills:** `writing-python-code`, `testing-python` for all code changes.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/qt_ai_dev_tools/screenshot.py` | Modify | Add `--overwrite` to scrot (ISSUE-015) |
| `src/qt_ai_dev_tools/cli.py` | Modify | Wire value interface (ISSUE-017), align find visibility (ISSUE-019), add `--index` to `do` (ISSUE-020) |
| `src/qt_ai_dev_tools/interact.py` | Modify | Add zero-coordinate guard (ISSUE-022) |
| `src/qt_ai_dev_tools/subsystems/tray.py` | Modify | Query app identity from D-Bus (ISSUE-023) |
| `src/qt_ai_dev_tools/subsystems/models.py` | Modify | Add `title` and `icon_name` to TrayItem (ISSUE-023) |
| `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` | Modify | Extract desktop-session to script (ISSUE-016) |
| `tests/e2e/test_complex_app_e2e.py` | Modify | Add tests for ISSUE-015, 017, 019, 022 |
| `tests/e2e/test_compound_e2e.py` | Modify | Add test for ISSUE-020 |
| `tests/e2e/test_tray_e2e.py` | Modify | Add test for ISSUE-023 |
| `tests/unit/test_screenshot.py` | Modify | Add overwrite test for ISSUE-015 |
| `tests/unit/test_cli.py` | Modify | Add value interface unit test for ISSUE-017 |

---

## Task 1: E2E Test — Screenshot Overwrite (ISSUE-015)

**Files:**
- Modify: `tests/e2e/test_complex_app_e2e.py`

- [ ] **Step 1: Write failing e2e test**

Add to `tests/e2e/test_complex_app_e2e.py` after existing test classes:

```python
class TestScreenshot:
    """Screenshot capture tests."""

    def test_consecutive_screenshots_differ_after_state_change(
        self, complex_app: subprocess.Popen[str]
    ) -> None:
        """Two screenshots with a display change between them must differ."""
        shot_path = "/tmp/test_screenshot_overwrite.png"

        # First screenshot
        r1 = _run_cli("screenshot", "-o", shot_path, app=None)
        assert r1.returncode == 0
        with open(shot_path, "rb") as f:
            hash1 = hashlib.md5(f.read()).hexdigest()

        # Change display state — switch tab
        _run_cli("click", "--role", "page tab", "--name", "Data")
        time.sleep(0.5)

        # Second screenshot to same path
        r2 = _run_cli("screenshot", "-o", shot_path, app=None)
        assert r2.returncode == 0
        with open(shot_path, "rb") as f:
            hash2 = hashlib.md5(f.read()).hexdigest()

        assert hash1 != hash2, "Screenshots should differ after tab switch"
```

Add `import hashlib` to the imports if not present.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestScreenshot::test_consecutive_screenshots_differ_after_state_change -v"`

Expected: FAIL — hashes are identical because scrot doesn't overwrite.

- [ ] **Step 3: Commit failing test**

```bash
git add tests/e2e/test_complex_app_e2e.py
git commit -m "test(e2e): add screenshot overwrite test (proves ISSUE-015)"
```

---

## Task 2: Fix Screenshot Overwrite (ISSUE-015)

**Files:**
- Modify: `src/qt_ai_dev_tools/screenshot.py:21`

- [ ] **Step 1: Fix scrot command**

In `src/qt_ai_dev_tools/screenshot.py`, line 21, change:

```python
run_command(["scrot", path], env=env, check=True)
```

to:

```python
run_command(["scrot", "--overwrite", path], env=env, check=True)
```

- [ ] **Step 2: Run e2e test to verify it passes**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestScreenshot -v"`

Expected: PASS

- [ ] **Step 3: Run full lint**

Run: `uv run poe lint_full`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/screenshot.py
git commit -m "fix: add --overwrite to scrot to prevent stale screenshots (ISSUE-015)"
```

---

## Task 3: E2E Test — Slider Value Interface (ISSUE-017)

**Files:**
- Modify: `tests/e2e/test_complex_app_e2e.py`

- [ ] **Step 1: Write failing e2e test**

Add to `tests/e2e/test_complex_app_e2e.py` inside an existing or new test class:

```python
class TestSliderValue:
    """Slider value interface tests."""

    def test_state_json_includes_slider_value(
        self, complex_app: subprocess.Popen[str]
    ) -> None:
        """state --json on a slider should include value/min/max fields."""
        # Switch to Inputs tab where the slider lives
        _run_cli("click", "--role", "page tab", "--name", "Inputs")
        time.sleep(0.3)

        # Set slider to known value via bridge
        _bridge_eval_strict(complex_app.pid, "widgets['volume_slider'].setValue(75)")
        time.sleep(0.3)

        result = _run_cli("state", "--role", "slider", "--json")
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert "value" in data, "state --json should include 'value' for sliders"
        assert data["value"] == 75.0
        assert "min_value" in data
        assert "max_value" in data
        assert data["min_value"] == 0.0
        assert data["max_value"] == 100.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestSliderValue -v"`

Expected: FAIL — "value" key not in JSON output.

- [ ] **Step 3: Commit failing test**

```bash
git add tests/e2e/test_complex_app_e2e.py
git commit -m "test(e2e): add slider value interface test (proves ISSUE-017)"
```

---

## Task 4: Fix Slider Value in CLI (ISSUE-017)

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:100-109` (`_widget_dict`)
- Modify: `src/qt_ai_dev_tools/cli.py:359-383` (`state` command text output)

- [ ] **Step 1: Update `_widget_dict` to include value fields**

In `src/qt_ai_dev_tools/cli.py`, modify the `_widget_dict` function (lines 100-109). After the `visible` field, add value interface fields:

```python
def _widget_dict(widget: AtspiNode) -> dict[str, object]:
    ext = widget.get_extents()
    d: dict[str, object] = {
        "role": widget.role_name,
        "name": widget.name,
        "text": widget.get_text(),
        "extents": {"x": ext.x, "y": ext.y, "width": ext.width, "height": ext.height},
        "visible": ext.width > 0 and ext.height > 0,
    }
    if widget.has_value_iface:
        d["value"] = widget.get_value()
        d["min_value"] = widget.get_minimum_value()
        d["max_value"] = widget.get_maximum_value()
    return d
```

- [ ] **Step 2: Update `state` text output**

In the `state` command function, after the extents print line, add value output. Find the section that prints extents in text mode and add after it:

```python
if widget.has_value_iface:
    val = widget.get_value()
    min_val = widget.get_minimum_value()
    max_val = widget.get_maximum_value()
    typer.echo(f"  Value: {val} (range: {min_val} - {max_val})")
```

- [ ] **Step 3: Run e2e test**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestSliderValue -v"`

Expected: PASS

- [ ] **Step 4: Run lint**

Run: `uv run poe lint_full`

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "feat: expose AT-SPI Value interface in state/find JSON output (ISSUE-017)"
```

---

## Task 5: E2E Test — `do click --index` (ISSUE-020)

**Files:**
- Modify: `tests/e2e/test_compound_e2e.py`

- [ ] **Step 1: Write failing e2e test**

Add to the existing test class in `tests/e2e/test_compound_e2e.py`:

```python
def test_do_click_with_index(self, bridge_app: subprocess.Popen[str]) -> None:
    """do click should accept --index to disambiguate widgets."""
    result = _run_cli(
        "do", "click", "push button", "--role", "push button", "--index", "0"
    )
    # The key assertion: --index should not cause "No such option" error
    assert "No such option" not in result.stderr
    assert result.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_compound_e2e.py::test_do_click_with_index -v"`

Expected: FAIL — "No such option: --index"

- [ ] **Step 3: Commit failing test**

```bash
git add tests/e2e/test_compound_e2e.py
git commit -m "test(e2e): add do click --index test (proves ISSUE-020)"
```

---

## Task 6: Fix `do` Command — Add `--index` (ISSUE-020)

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:493-535` (`do_action` function)

- [ ] **Step 1: Add `--index` parameter to `do_action`**

In the `do_action` function signature (around line 493), add the index parameter. Find the existing parameters and add after `exact`:

```python
index: Annotated[
    int | None,
    typer.Option("--index", help="Select Nth matching widget (0-based) when multiple match."),
] = None,
```

Then in the function body where `pilot.find_one()` is called (around line 517), pass the index:

```python
widget = pilot.find_one(role=role, name=target, visible=visible, exact=exact, index=index)
```

- [ ] **Step 2: Run e2e test**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_compound_e2e.py::test_do_click_with_index -v"`

Expected: PASS

- [ ] **Step 3: Run lint**

Run: `uv run poe lint_full`

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "feat: add --index to do command for widget disambiguation (ISSUE-020)"
```

---

## Task 7: E2E Test — Click on Invisible Popup (ISSUE-022)

**Files:**
- Modify: `tests/e2e/test_complex_app_e2e.py`

- [ ] **Step 1: Write failing e2e test**

Add to `tests/e2e/test_complex_app_e2e.py`:

```python
class TestClickInvisibleWidget:
    """Tests for clicking widgets in closed popup menus."""

    def test_click_closed_menu_item_rejects_zero_coords(
        self, complex_app: subprocess.Popen[str]
    ) -> None:
        """Clicking a menu item without opening its parent menu should fail.

        Menu items in closed popups have (0,0) coordinates in AT-SPI.
        Clicking at (0,0) is always wrong — the tool should reject this.
        """
        # Do NOT open the File menu first
        # Try to click a submenu item directly
        result = _run_cli("click", "--role", "menu item", "--name", "New", "--exact")
        # Should fail — the menu item has (0,0) coordinates
        assert result.returncode != 0, (
            "Clicking a closed popup menu item should fail, not silently click at (0,0)"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestClickInvisibleWidget -v"`

Expected: FAIL — click currently succeeds and reports clicking at (0,0).

- [ ] **Step 3: Commit failing test**

```bash
git add tests/e2e/test_complex_app_e2e.py
git commit -m "test(e2e): add click-on-closed-popup test (proves ISSUE-022)"
```

---

## Task 8: Fix Click on Invisible Popup Items (ISSUE-022)

**Files:**
- Modify: `src/qt_ai_dev_tools/interact.py:19-74` (`click_at` function)

- [ ] **Step 1: Add zero-coordinate guard to `click_at`**

In `src/qt_ai_dev_tools/interact.py`, in the `click_at` function, after the existing display bounds validation (around line 47), add a zero-coordinate guard:

```python
if x == 0 and y == 0:
    msg = (
        "Widget is at coordinates (0, 0), which typically means it is inside a "
        "closed popup menu or not yet rendered. Open the parent menu first."
    )
    raise ValueError(msg)
```

- [ ] **Step 2: Run e2e test**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestClickInvisibleWidget -v"`

Expected: PASS

- [ ] **Step 3: Run ALL e2e tests to check for regressions**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/ -v --timeout=60"`

Check that no existing tests break (no test should intentionally click at 0,0).

- [ ] **Step 4: Run lint**

Run: `uv run poe lint_full`

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/interact.py
git commit -m "fix: reject click at (0,0) coordinates from closed popups (ISSUE-022)"
```

---

## Task 9: E2E Test — find/state Visibility Consistency (ISSUE-019)

**Files:**
- Modify: `tests/e2e/test_complex_app_e2e.py`

- [ ] **Step 1: Write failing e2e test**

Add to `tests/e2e/test_complex_app_e2e.py`:

```python
class TestVisibilityConsistency:
    """Tests for consistent visibility defaults across commands."""

    def test_find_defaults_to_visible_only(
        self, complex_app: subprocess.Popen[str]
    ) -> None:
        """find should default to --visible (same as state and click).

        Currently find defaults to visible=False, showing invisible widgets.
        This is inconsistent with state (visible=True) and click (visible=True).
        """
        # Switch to Inputs tab — Data tab widgets become invisible
        _run_cli("click", "--role", "page tab", "--name", "Inputs")
        time.sleep(0.3)

        # find with default visibility should NOT show the data table
        # (it's on the hidden Data tab)
        result = _run_cli("find", "--role", "table", "--json")
        assert result.returncode == 0

        if result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, list):
                # All returned widgets should be visible
                for w in data:
                    assert w.get("visible", True), (
                        f"find should default to visible-only, but returned invisible widget: {w}"
                    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestVisibilityConsistency -v"`

Expected: FAIL — find defaults to `visible=False`, returns invisible widgets.

- [ ] **Step 3: Commit failing test**

```bash
git add tests/e2e/test_complex_app_e2e.py
git commit -m "test(e2e): add find/state visibility consistency test (proves ISSUE-019)"
```

---

## Task 10: Fix find Visibility Default (ISSUE-019)

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:264-288` (`find` command)

- [ ] **Step 1: Change `find` visibility default to True**

In the `find` function signature (around line 264), change the `visible` parameter default from `False` to `True`:

```python
visible: Annotated[
    bool,
    typer.Option("--visible/--no-visible", help="Filter to visible widgets only."),
] = True,
```

- [ ] **Step 2: Run e2e test**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_complex_app_e2e.py::TestVisibilityConsistency -v"`

Expected: PASS

- [ ] **Step 3: Run ALL tests to check regressions**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -v --timeout=60"`

Some existing tests may need updating if they relied on `find` showing invisible widgets. Fix any that break by adding `--no-visible` explicitly.

- [ ] **Step 4: Run lint**

Run: `uv run poe lint_full`

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py tests/
git commit -m "fix: align find visibility default to True, matching state and click (ISSUE-019)"
```

---

## Task 11: E2E Test — Tray App Name (ISSUE-023)

**Files:**
- Modify: `tests/e2e/test_tray_e2e.py`

- [ ] **Step 1: Write failing e2e test**

Add to the existing test class in `tests/e2e/test_tray_e2e.py`:

```python
def test_tray_item_has_app_identity(
    self, tray_app: subprocess.Popen[str], clean_sni_watcher: None
) -> None:
    """Tray items should expose app name, not just StatusNotifierItem-PID."""
    items = tray.list_items()
    assert len(items) > 0
    item = items[0]

    # The item should have a title or icon_name identifying the app
    has_identity = bool(item.title) or bool(item.icon_name)
    assert has_identity, (
        f"Tray item '{item.name}' has no app identity (title={item.title!r}, "
        f"icon_name={item.icon_name!r}). Should query D-Bus properties."
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_tray_e2e.py::test_tray_item_has_app_identity -v"`

Expected: FAIL — TrayItem has no `title` or `icon_name` attributes.

- [ ] **Step 3: Commit failing test**

```bash
git add tests/e2e/test_tray_e2e.py
git commit -m "test(e2e): add tray app identity test (proves ISSUE-023)"
```

---

## Task 12: Fix Tray App Name Resolution (ISSUE-023)

**Files:**
- Modify: `src/qt_ai_dev_tools/subsystems/models.py:33-39` (TrayItem)
- Modify: `src/qt_ai_dev_tools/subsystems/tray.py:233-279` (_parse_registered_items)
- Modify: `src/qt_ai_dev_tools/subsystems/tray.py:512-531` (_find_item)

- [ ] **Step 1: Add `title` and `icon_name` fields to TrayItem**

In `src/qt_ai_dev_tools/subsystems/models.py`, update the `TrayItem` dataclass:

```python
@dataclass(slots=True)
class TrayItem:
    """A registered StatusNotifierItem."""

    name: str
    bus_name: str
    object_path: str
    protocol: str
    title: str = ""
    icon_name: str = ""
```

- [ ] **Step 2: Query D-Bus properties in `_parse_registered_items`**

In `src/qt_ai_dev_tools/subsystems/tray.py`, in `_parse_registered_items`, after creating each `TrayItem`, query the `Title` and `IconName` D-Bus properties. Find where items are created and add property queries:

```python
# After creating the TrayItem, query identity properties
for item in items:
    try:
        title_out = run_tool(
            "busctl",
            ["--user", "get-property", item.bus_name, item.object_path,
             "org.kde.StatusNotifierItem", "Title"],
            capture=True,
        )
        if title_out.success and title_out.stdout:
            # busctl output: s "AppTitle"
            match = re.search(r'"([^"]*)"', title_out.stdout)
            if match:
                item.title = match.group(1)
    except Exception:
        pass

    try:
        icon_out = run_tool(
            "busctl",
            ["--user", "get-property", item.bus_name, item.object_path,
             "org.kde.StatusNotifierItem", "IconName"],
            capture=True,
        )
        if icon_out.success and icon_out.stdout:
            match = re.search(r'"([^"]*)"', icon_out.stdout)
            if match:
                item.icon_name = match.group(1)
    except Exception:
        pass
```

Note: The exact integration point depends on the existing code structure. The researcher agent should find the right place to insert this logic — it may be in `_parse_registered_items` or a new helper called after parsing.

- [ ] **Step 3: Update `_find_item` to match by title/icon_name**

In `src/qt_ai_dev_tools/subsystems/tray.py`, update `_find_item` (around line 512-531) to also match against `title` and `icon_name`:

```python
def _find_item(app_name: str) -> TrayItem:
    items = list_items()
    query = app_name.lower()
    for item in items:
        if (
            query in item.name.lower()
            or query in item.bus_name.lower()
            or query in item.title.lower()
            or query in item.icon_name.lower()
        ):
            return item
    msg = f"No tray item matching '{app_name}'. Available: {[i.name for i in items]}"
    raise LookupError(msg)
```

- [ ] **Step 4: Run e2e test**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_tray_e2e.py::test_tray_item_has_app_identity -v"`

Expected: PASS

- [ ] **Step 5: Run all tray tests**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_tray_e2e.py -v"`

Expected: All pass, no regressions.

- [ ] **Step 6: Run lint**

Run: `uv run poe lint_full`

- [ ] **Step 7: Commit**

```bash
git add src/qt_ai_dev_tools/subsystems/models.py src/qt_ai_dev_tools/subsystems/tray.py
git commit -m "feat: resolve tray item app name via D-Bus Title/IconName (ISSUE-023)"
```

---

## Task 13: Fix Desktop Session Service (ISSUE-016)

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2`

This task requires a researcher/prototyper agent because it involves systemd escaping and needs VM testing.

- [ ] **Step 1: Spawn researcher agent**

The researcher should:
1. Read the current `provision.sh.j2` ExecStart section (lines 200-222)
2. Create a standalone script `/home/vagrant/.local/bin/desktop-session.sh` that contains the startup logic
3. Update the systemd service to call the script instead of inline bash
4. Test by re-provisioning or manually deploying to the VM
5. Verify `systemctl --user status desktop-session` shows `active (running)`
6. Verify `xprop -root AT_SPI_BUS` returns a value

- [ ] **Step 2: Implement the fix in the template**

Extract the ExecStart bash logic into a script that gets written during provisioning. In `provision.sh.j2`, replace the inline ExecStart with:

1. Write a script file `/home/vagrant/.local/bin/desktop-session.sh` during provisioning
2. Change ExecStart to `ExecStart=/home/vagrant/.local/bin/desktop-session.sh`
3. The script should contain the same logic but without systemd escaping issues

- [ ] **Step 3: Test by reprovisioning VM**

```bash
uv run qt-ai-dev-tools vm run "systemctl --user restart desktop-session"
sleep 3
uv run qt-ai-dev-tools vm run "systemctl --user status desktop-session"
uv run qt-ai-dev-tools vm run "xprop -root AT_SPI_BUS"
```

Expected: Service active, AT_SPI_BUS property set.

- [ ] **Step 4: Run full test suite in VM**

Run: `make test-vm`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2
git commit -m "fix: extract desktop-session to script, fix systemd quoting (ISSUE-016)"
```

---

## Task 14: Full Test Suite Verification

- [ ] **Step 1: Run lint**

Run: `uv run poe lint_full`

Fix any issues.

- [ ] **Step 2: Run full test suite**

Run: `make test-full` (or `make test-vm` for VM tests + `make test-unit` for unit tests)

Fix any failures.

- [ ] **Step 3: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: test suite cleanup after round 2 fixes"
```

---

## Task 15: Manual Validation

- [ ] **Step 1: Re-test screenshot with SpeedCrunch**

Launch SpeedCrunch, take multiple screenshots with display changes between them, verify they differ.

- [ ] **Step 2: Re-test slider value with VLC**

Launch VLC, run `state --role slider --json`, verify value/min/max fields present.

- [ ] **Step 3: Re-test tray with KeePassXC**

Enable tray in KeePassXC, run `tray list`, verify app identity is shown.

- [ ] **Step 4: Re-test do click --index with qBittorrent**

Run `do click "File" --role "menu item" --index 0`, verify it disambiguates correctly.

- [ ] **Step 5: Re-test find visibility**

Run `find --role "table"` with Data tab hidden, verify invisible widgets are not returned by default.

- [ ] **Step 6: Re-test click on closed popup**

Without opening File menu, try `click --role "menu item" --name "New" --exact`, verify it fails with helpful message.
