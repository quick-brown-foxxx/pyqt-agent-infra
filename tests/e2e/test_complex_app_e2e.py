"""E2E tests for the kitchen-sink complex app.

Exercises tabs, combo boxes, tables, sliders, checkboxes, menus, and
tree snapshots against the real app via AT-SPI and bridge.
"""

from __future__ import annotations

import os
import subprocess
import time

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
]


def _bridge_eval(pid: int, code: str) -> str | None:
    """Eval code via bridge targeting a specific PID, return result or None."""
    from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

    sock = find_bridge_socket(pid=pid)
    if sock is None:
        return None
    resp = eval_code(sock, code)
    if not resp.ok:
        return None
    return resp.result


def _bridge_eval_strict(pid: int, code: str) -> str:
    """Eval code via bridge, assert success, return result."""
    from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

    sock = find_bridge_socket(pid=pid)
    assert sock is not None, "No bridge socket found"
    resp = eval_code(sock, code)
    assert resp.ok, f"Bridge eval failed: {resp.error}"
    assert resp.result is not None
    return resp.result


class TestTabNavigation:
    """Switch between tabs and verify expected widgets are findable."""

    def test_switch_to_data_tab(self, complex_app: subprocess.Popen[str]) -> None:
        """Switch to Data tab, verify the data table is findable."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Data")
        time.sleep(0.5)

        # Table should be visible on the Data tab
        tables = pilot.find(role="table")
        assert len(tables) >= 1, "Expected at least one table on the Data tab"

    def test_switch_to_settings_tab(self, complex_app: subprocess.Popen[str]) -> None:
        """Switch to Settings tab, verify scroll area is findable."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Settings")
        time.sleep(0.5)

        # Scroll area should be visible on the Settings tab
        scroll_panes = pilot.find(role="scroll pane")
        assert len(scroll_panes) >= 1, "Expected at least one scroll pane on Settings tab"

    def test_switch_to_inputs_tab(self, complex_app: subprocess.Popen[str]) -> None:
        """Switch to Inputs tab, verify combo box is findable."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Inputs")
        time.sleep(0.5)

        combos = pilot.find(role="combo box")
        assert len(combos) >= 1, "Expected at least one combo box on the Inputs tab"


class TestComboBox:
    """Test combo box selection via AT-SPI."""

    def test_select_cherry(self, complex_app: subprocess.Popen[str]) -> None:
        """Select Cherry from the fruit combo, verify via bridge."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Inputs")
        time.sleep(0.3)

        pilot.select_combo_item("Cherry")
        time.sleep(0.3)

        # Verify via bridge that the combo box current text is Cherry
        current_text = _bridge_eval_strict(complex_app.pid, "widgets['fruit_combo'].currentText()")
        assert "Cherry" in current_text


class TestTable:
    """Test table inspection via AT-SPI."""

    def test_get_cell_content(self, complex_app: subprocess.Popen[str]) -> None:
        """Read table cell (0,0) and verify it contains Alpha."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Data")
        time.sleep(0.5)

        cell_text = pilot.get_table_cell(0, 0)
        assert "Alpha" in cell_text, f"Expected 'Alpha' in cell (0,0), got: {cell_text!r}"

    def test_get_table_size(self, complex_app: subprocess.Popen[str]) -> None:
        """Verify the table has 5 rows and 3 columns."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Data")
        time.sleep(0.5)

        rows, cols = pilot.get_table_size()
        assert rows == 5, f"Expected 5 rows, got {rows}"
        assert cols == 3, f"Expected 3 columns, got {cols}"


class TestSlider:
    """Test slider value manipulation via AT-SPI."""

    def test_set_slider_value(self, complex_app: subprocess.Popen[str]) -> None:
        """Set slider to 75, verify with get_widget_value."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Inputs")
        time.sleep(0.3)

        pilot.set_slider_value(75, role="slider")
        time.sleep(0.3)

        value = pilot.get_widget_value(role="slider")
        assert value is not None, "Slider should have a Value interface"
        assert value == 75.0, f"Expected slider value 75.0, got {value}"


class TestCheckbox:
    """Test checkbox toggling via AT-SPI."""

    def test_check_notifications_checkbox(self, complex_app: subprocess.Popen[str]) -> None:
        """Toggle the notifications checkbox, verify via bridge."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Inputs")
        time.sleep(0.3)

        # Ensure unchecked first via bridge
        _bridge_eval_strict(complex_app.pid, "widgets['notify_checkbox'].setChecked(False)")
        time.sleep(0.2)

        # Toggle via AT-SPI
        pilot.check_checkbox(name="notifications")
        time.sleep(0.3)

        # Verify via bridge
        checked = _bridge_eval_strict(complex_app.pid, "widgets['notify_checkbox'].isChecked()")
        assert checked == "True", f"Expected checkbox to be checked, got: {checked}"


class TestMenuNavigation:
    """Test menu bar navigation via AT-SPI."""

    def test_select_file_new(self, complex_app: subprocess.Popen[str]) -> None:
        """Select File > New menu item, verify status via bridge."""
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.select_menu_item("File", "New")
        time.sleep(0.5)

        # The app sets status to "New clicked" when File > New is activated
        status = _bridge_eval_strict(complex_app.pid, "widgets['status_label'].text()")
        assert "New clicked" in status, f"Expected 'New clicked' in status, got: {status!r}"


class TestSnapshot:
    """Test tree snapshot capture and diff."""

    def test_snapshot_diff_detects_changes(self, complex_app: subprocess.Popen[str]) -> None:
        """Capture tree, modify state via bridge, capture again, diff shows changes."""
        from qt_ai_dev_tools.pilot import QtPilot
        from qt_ai_dev_tools.snapshot import capture_tree, diff_snapshots

        pilot = QtPilot(app_name="complex_app.py")
        assert pilot.app is not None

        # Capture initial snapshot
        snap_before = capture_tree(pilot.app)
        assert len(snap_before) > 0, "Snapshot should contain entries"

        # Modify state via bridge (change status label text)
        _bridge_eval_strict(complex_app.pid, "widgets['status_label'].setText('snapshot-test-marker')")
        time.sleep(0.3)

        # Capture after modification
        snap_after = capture_tree(pilot.app)

        # Diff should detect changes
        diff = diff_snapshots(snap_before, snap_after)
        assert diff.has_changes, "Expected snapshot diff to detect status label text change"
