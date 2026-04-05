"""Tests for QtPilot — AT-SPI based Qt app interaction."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock gi and Atspi before importing pilot, since gi is a system package.
_mock_gi = MagicMock()
_mock_atspi_module = MagicMock()
_mock_gi.require_version = MagicMock()
_mock_gi.repository.Atspi = _mock_atspi_module

with patch.dict(sys.modules, {"gi": _mock_gi, "gi.repository": _mock_gi.repository}):
    from qt_ai_dev_tools._atspi import AtspiNode
    from qt_ai_dev_tools.pilot import QtPilot

pytestmark = pytest.mark.unit


def _make_node(name: str, role_name: str, children: list[MagicMock] | None = None) -> MagicMock:
    """Create a mock AT-SPI native object."""
    native = MagicMock()
    native.get_name.return_value = name
    native.get_role_name.return_value = role_name
    native.get_child_count.return_value = len(children) if children else 0
    native.get_child_at_index.side_effect = lambda i: children[i] if children and i < len(children) else None
    native.get_text_iface.return_value = None
    native.get_action_iface.return_value = None

    # Extents mock
    ext = MagicMock()
    ext.x = 10
    ext.y = 20
    ext.width = 100
    ext.height = 50
    native.get_extents.return_value = ext

    return native


class TestQtPilotInit:
    """Test QtPilot initialization and app discovery."""

    def test_finds_app_by_name(self) -> None:
        """Should find an app by name substring on the AT-SPI bus."""
        app_native = _make_node("main.py", "application")
        desktop_native = _make_node("desktop", "desktop", children=[app_native])

        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="main.py", retries=1, delay=0.0)
            assert pilot.app is not None
            assert pilot.app.name == "main.py"

    def test_finds_first_app_when_no_name(self) -> None:
        """Should find the first app when no name is specified."""
        app_native = _make_node("some-app", "application")
        desktop_native = _make_node("desktop", "desktop", children=[app_native])

        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name=None, retries=1, delay=0.0)
            assert pilot.app is not None
            assert pilot.app.name == "some-app"

    def test_raises_when_app_not_found(self) -> None:
        """Should raise RuntimeError when app is not on the AT-SPI bus."""
        desktop_native = _make_node("desktop", "desktop", children=[])

        with (
            patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)),
            pytest.raises(RuntimeError, match="not found on AT-SPI bus"),
        ):
            QtPilot(app_name="nonexistent", retries=1, delay=0.0)


class TestQtPilotFind:
    """Test widget search methods."""

    @pytest.fixture
    def pilot_with_tree(self) -> QtPilot:
        """Create a QtPilot with a simple widget tree for testing."""
        btn = _make_node("Save", "push button")
        label = _make_node("Status", "label")
        text = _make_node("input", "text")
        frame = _make_node("main", "frame", children=[btn, label, text])
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])

        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            return QtPilot(app_name="test-app", retries=1, delay=0.0)

    def test_find_by_role(self, pilot_with_tree: QtPilot) -> None:
        """Should find widgets matching a specific role."""
        results = pilot_with_tree.find(role="push button")
        assert len(results) == 1
        assert results[0].name == "Save"

    def test_find_by_name(self, pilot_with_tree: QtPilot) -> None:
        """Should find widgets matching a name substring."""
        results = pilot_with_tree.find(name="Status")
        assert len(results) == 1
        assert results[0].role_name == "label"

    def test_find_by_role_and_name(self, pilot_with_tree: QtPilot) -> None:
        """Should find widgets matching both role and name."""
        results = pilot_with_tree.find(role="text", name="input")
        assert len(results) == 1

    def test_find_returns_empty_for_no_match(self, pilot_with_tree: QtPilot) -> None:
        """Should return empty list when no widgets match."""
        results = pilot_with_tree.find(role="slider")
        assert results == []

    def test_find_one_returns_single_match(self, pilot_with_tree: QtPilot) -> None:
        """Should return the single matching widget."""
        widget = pilot_with_tree.find_one(role="push button", name="Save")
        assert widget.name == "Save"

    def test_find_one_raises_when_none_found(self, pilot_with_tree: QtPilot) -> None:
        """Should raise LookupError when no widget found."""
        with pytest.raises(LookupError, match="No widget found"):
            pilot_with_tree.find_one(role="slider")

    def test_find_one_raises_when_multiple_found(self) -> None:
        """Should raise LookupError when multiple widgets match."""
        btn1 = _make_node("OK", "push button")
        btn2 = _make_node("Cancel", "push button")
        frame = _make_node("main", "frame", children=[btn1, btn2])
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])

        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
            with pytest.raises(LookupError, match="Multiple widgets found"):
                pilot.find_one(role="push button")


class TestQtPilotDumpTree:
    """Test tree dump functionality."""

    def test_dump_tree_output(self) -> None:
        """Should produce indented tree text."""
        label = _make_node("Hello", "label")
        frame = _make_node("main", "frame", children=[label])
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])

        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
            tree = pilot.dump_tree()
            assert '[application] "test-app"' in tree
            assert '[frame] "main"' in tree
            assert '[label] "Hello"' in tree


class TestQtPilotNoApp:
    """Test error handling when no app is connected."""

    def test_find_raises_without_app(self) -> None:
        """Should raise RuntimeError when find is called with no app."""
        app_native = _make_node("test-app", "application")
        desktop_native2 = _make_node("desktop", "desktop", children=[app_native])

        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native2)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
            pilot.app = None  # Simulate disconnected state
            with pytest.raises(RuntimeError, match="No app connected"):
                pilot.find(role="button")

    def test_dump_tree_raises_without_app(self) -> None:
        """Should raise RuntimeError when dump_tree is called with no app."""
        app_native = _make_node("test-app", "application")
        desktop_native = _make_node("desktop", "desktop", children=[app_native])

        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
            pilot.app = None
            with pytest.raises(RuntimeError, match="No app connected"):
                pilot.dump_tree()


# ── Helper to build a QtPilot with find_one/find mocked ─────────


def _make_pilot_with_mock_find() -> QtPilot:
    """Create a QtPilot and return it (app set to a dummy node).

    Callers should patch find_one / find on the returned pilot.
    """
    app_native = _make_node("test-app", "application")
    desktop_native = _make_node("desktop", "desktop", children=[app_native])
    with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
        return QtPilot(app_name="test-app", retries=1, delay=0.0)


def _make_atspi_node_mock(
    name: str = "",
    role_name: str = "",
    children: list[MagicMock] | None = None,
) -> MagicMock:
    """Create a MagicMock that behaves like an AtspiNode."""
    node = MagicMock(spec=AtspiNode)
    node.name = name
    node.role_name = role_name
    node.children = children or []
    node.child_count = len(node.children)
    return node


# ── Tests for select_combo_item ──────────────────────────────────


class TestSelectComboItem:
    """Test QtPilot.select_combo_item."""

    def test_selects_matching_child(self) -> None:
        """Should call select_child with the correct index."""
        child_a = _make_atspi_node_mock(name="Apple")
        child_b = _make_atspi_node_mock(name="Banana")
        combo = _make_atspi_node_mock(name="fruit", role_name="combo box", children=[child_a, child_b])

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=combo):
            pilot.select_combo_item("Banana", role="combo box", name="fruit")

        combo.select_child.assert_called_once_with(1)

    def test_raises_when_item_not_found(self) -> None:
        """Should raise LookupError when no child matches item_text."""
        child = _make_atspi_node_mock(name="Apple")
        combo = _make_atspi_node_mock(name="fruit", role_name="combo box", children=[child])

        pilot = _make_pilot_with_mock_find()
        with (
            patch.object(pilot, "find_one", return_value=combo),
            pytest.raises(LookupError, match="not found in combo box"),
        ):
            pilot.select_combo_item("Cherry")


# ── Tests for switch_tab ─────────────────────────────────────────


class TestSwitchTab:
    """Test QtPilot.switch_tab."""

    def test_selects_matching_tab_by_substring(self) -> None:
        """Should select the tab whose name contains tab_text."""
        tab_a = _make_atspi_node_mock(name="General Settings")
        tab_b = _make_atspi_node_mock(name="Advanced Options")
        tab_list = _make_atspi_node_mock(name="tabs", role_name="page tab list", children=[tab_a, tab_b])

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=tab_list):
            pilot.switch_tab("Advanced")

        tab_list.select_child.assert_called_once_with(1)

    def test_raises_when_tab_not_found(self) -> None:
        """Should raise LookupError when no tab contains tab_text."""
        tab = _make_atspi_node_mock(name="General")
        tab_list = _make_atspi_node_mock(name="tabs", role_name="page tab list", children=[tab])

        pilot = _make_pilot_with_mock_find()
        with (
            patch.object(pilot, "find_one", return_value=tab_list),
            pytest.raises(LookupError, match="not found"),
        ):
            pilot.switch_tab("Network")


# ── Tests for get_table_cell ─────────────────────────────────────


class TestGetTableCell:
    """Test QtPilot.get_table_cell."""

    def test_returns_cell_text(self) -> None:
        """Should return text of the cell at (row, col)."""
        cell = _make_atspi_node_mock(name="cell-0-1")
        cell.get_text.return_value = "hello"

        table = _make_atspi_node_mock(name="data", role_name="table")
        table.get_cell_at.return_value = cell

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=table):
            result = pilot.get_table_cell(0, 1)

        assert result == "hello"
        table.get_cell_at.assert_called_once_with(0, 1)

    def test_raises_for_none_cell(self) -> None:
        """Should raise LookupError when cell is None."""
        table = _make_atspi_node_mock(name="data", role_name="table")
        table.get_cell_at.return_value = None

        pilot = _make_pilot_with_mock_find()
        with (
            patch.object(pilot, "find_one", return_value=table),
            pytest.raises(LookupError, match="No cell at"),
        ):
            pilot.get_table_cell(5, 5)


# ── Tests for get_table_size ─────────────────────────────────────


class TestGetTableSize:
    """Test QtPilot.get_table_size."""

    def test_returns_rows_and_cols(self) -> None:
        """Should return (rows, columns) tuple."""
        table = _make_atspi_node_mock(name="data", role_name="table")
        table.get_n_rows.return_value = 3
        table.get_n_columns.return_value = 5

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=table):
            result = pilot.get_table_size()

        assert result == (3, 5)


# ── Tests for check_checkbox ─────────────────────────────────────


class TestCheckCheckbox:
    """Test QtPilot.check_checkbox."""

    def test_invokes_toggle_action(self) -> None:
        """Should call do_action('Toggle') on the checkbox."""
        widget = _make_atspi_node_mock(name="Accept", role_name="check box")

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=widget):
            pilot.check_checkbox(checked=True, name="Accept")

        widget.do_action.assert_called_once_with("Toggle")

    def test_falls_back_to_press_when_toggle_unavailable(self) -> None:
        """Should fall back to do_action('Press') when Toggle raises."""
        widget = _make_atspi_node_mock(name="Accept", role_name="check box")
        widget.do_action.side_effect = [LookupError("no Toggle"), None]

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=widget):
            pilot.check_checkbox(name="Accept")

        assert widget.do_action.call_count == 2
        widget.do_action.assert_any_call("Toggle")
        widget.do_action.assert_any_call("Press")


# ── Tests for set_slider_value ───────────────────────────────────


class TestSetSliderValue:
    """Test QtPilot.set_slider_value."""

    def test_calls_set_value(self) -> None:
        """Should call set_value on the widget."""
        widget = _make_atspi_node_mock(name="volume", role_name="slider")

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=widget):
            pilot.set_slider_value(75.0, name="volume")

        widget.set_value.assert_called_once_with(75.0)


# ── Tests for get_widget_value ───────────────────────────────────


class TestGetWidgetValue:
    """Test QtPilot.get_widget_value."""

    def test_returns_value(self) -> None:
        """Should return the numeric value from the widget."""
        widget = _make_atspi_node_mock(name="volume", role_name="slider")
        widget.get_value.return_value = 42.0

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=widget):
            result = pilot.get_widget_value(role="slider", name="volume")

        assert result == 42.0

    def test_returns_none_when_no_value_iface(self) -> None:
        """Should return None when widget has no Value interface."""
        widget = _make_atspi_node_mock(name="label", role_name="label")
        widget.get_value.return_value = None

        pilot = _make_pilot_with_mock_find()
        with patch.object(pilot, "find_one", return_value=widget):
            result = pilot.get_widget_value(role="label", name="label")

        assert result is None


# ── Tests for select_menu_item ───────────────────────────────────


class TestSelectMenuItem:
    """Test QtPilot.select_menu_item."""

    def test_clicks_through_menu_path(self) -> None:
        """Should find and click each item in the menu path."""
        file_item = _make_atspi_node_mock(name="File", role_name="menu")
        save_item = _make_atspi_node_mock(name="Save", role_name="menu item")

        pilot = _make_pilot_with_mock_find()
        with (
            patch.object(pilot, "find", side_effect=[[file_item], [save_item]]),
            patch.object(pilot, "click") as mock_click,
        ):
            pilot.select_menu_item("File", "Save", pause=0.1)

        assert mock_click.call_count == 2
        mock_click.assert_any_call(file_item, pause=0.1)
        mock_click.assert_any_call(save_item, pause=0.1)

    def test_raises_when_menu_item_not_found(self) -> None:
        """Should raise LookupError when a path item is not found."""
        file_item = _make_atspi_node_mock(name="File", role_name="menu")

        pilot = _make_pilot_with_mock_find()
        with (
            patch.object(pilot, "find", side_effect=[[file_item], []]),
            patch.object(pilot, "click"),
            pytest.raises(LookupError, match="not found"),
        ):
            pilot.select_menu_item("File", "Nonexistent")
