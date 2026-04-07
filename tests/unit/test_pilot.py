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


def _make_node(
    name: str,
    role_name: str,
    children: list[MagicMock] | None = None,
    ext_x: int = 10,
    ext_y: int = 20,
    ext_width: int = 100,
    ext_height: int = 50,
) -> MagicMock:
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
    ext.x = ext_x
    ext.y = ext_y
    ext.width = ext_width
    ext.height = ext_height
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
    """Test QtPilot.select_combo_item.

    Implementation uses keyboard navigation: click combo to open popup,
    arrow keys to navigate to target item, Enter to confirm.
    AT-SPI tree: [combo box "current"] -> [list] -> [list item]*
    """

    def test_navigates_to_matching_item(self) -> None:
        """Should click combo, arrow down to target, and press Enter."""
        item_a = _make_atspi_node_mock(name="Apple", role_name="list item")
        item_b = _make_atspi_node_mock(name="Banana", role_name="list item")
        item_c = _make_atspi_node_mock(name="Cherry", role_name="list item")
        list_node = _make_atspi_node_mock(name="", role_name="list", children=[item_a, item_b, item_c])
        combo = _make_atspi_node_mock(name="Apple", role_name="combo box", children=[list_node])
        combo.get_extents.return_value = MagicMock(center=(100, 100))

        pilot = _make_pilot_with_mock_find()
        # Patch click and press_key on the pilot instance methods to avoid xdotool
        with (
            patch.object(pilot, "find_one", return_value=combo),
            patch.object(pilot, "click") as mock_click,
            patch.object(pilot, "press_key") as mock_press,
        ):
            pilot.select_combo_item("Cherry", role="combo box")

        mock_click.assert_called()
        # Navigate from Apple (idx 0) to Cherry (idx 2) = 2 Down + Enter
        key_calls = [c[0][0] for c in mock_press.call_args_list]
        assert key_calls.count("Down") == 2
        assert "Return" in key_calls

    def test_raises_when_item_not_found(self) -> None:
        """Should raise LookupError when no child matches item_text."""
        item = _make_atspi_node_mock(name="Apple", role_name="list item")
        list_node = _make_atspi_node_mock(name="", role_name="list", children=[item])
        combo = _make_atspi_node_mock(name="Apple", role_name="combo box", children=[list_node])

        pilot = _make_pilot_with_mock_find()
        with (
            patch.object(pilot, "find_one", return_value=combo),
            pytest.raises(LookupError, match="not found in combo box"),
        ):
            pilot.select_combo_item("Mango")


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


# ── Tests for visible filter ────────────────────────────────────


class TestVisibilityFilter:
    """Test the visible parameter on find/find_one."""

    def _make_pilot_with_buttons(
        self,
        buttons: list[tuple[str, int, int]],
    ) -> QtPilot:
        """Create a pilot with push buttons of given (name, width, height)."""
        children = [_make_node(name, "push button", ext_width=w, ext_height=h) for name, w, h in buttons]
        frame = _make_node("main", "frame", children=children)
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])
        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            return QtPilot(app_name="test-app", retries=1, delay=0.0)

    def test_find_visible_excludes_zero_extent(self) -> None:
        """Visible filter should exclude widgets with 0x0 extents."""
        pilot = self._make_pilot_with_buttons(
            [
                ("OK", 100, 50),
                ("OK", 0, 0),
                ("OK", 0, 0),
            ]
        )
        results = pilot.find(role="push button", name="OK", visible=True)
        assert len(results) == 1

    def test_find_without_visible_returns_all(self) -> None:
        """Without visible filter, all matching widgets are returned."""
        pilot = self._make_pilot_with_buttons(
            [
                ("OK", 100, 50),
                ("OK", 0, 0),
                ("OK", 0, 0),
            ]
        )
        results = pilot.find(role="push button", name="OK")
        assert len(results) == 3

    def test_find_one_visible_returns_single_visible(self) -> None:
        """find_one with visible=True succeeds when exactly 1 is visible."""
        pilot = self._make_pilot_with_buttons(
            [
                ("OK", 100, 50),
                ("OK", 0, 0),
                ("OK", 0, 0),
            ]
        )
        widget = pilot.find_one(role="push button", name="OK", visible=True)
        ext = widget.get_extents()
        assert ext.width == 100

    def test_find_one_visible_raises_when_multiple_visible(self) -> None:
        """find_one with visible=True raises when 2+ are visible."""
        pilot = self._make_pilot_with_buttons(
            [
                ("OK", 100, 50),
                ("OK", 80, 40),
            ]
        )
        with pytest.raises(LookupError, match="Multiple widgets found"):
            pilot.find_one(role="push button", name="OK", visible=True)

    def test_find_visible_returns_empty_when_all_hidden(self) -> None:
        """Visible filter returns empty when all matches have 0x0 extents."""
        pilot = self._make_pilot_with_buttons(
            [
                ("OK", 0, 0),
                ("OK", 0, 0),
            ]
        )
        results = pilot.find(role="push button", name="OK", visible=True)
        assert results == []


# ── Tests for exact name match ──────────────────────────────────


class TestExactNameMatch:
    """Test the exact parameter on find/find_one."""

    def _make_pilot_with_named_buttons(self, names: list[str]) -> QtPilot:
        """Create a pilot with push buttons of given names."""
        children = [_make_node(n, "push button") for n in names]
        frame = _make_node("main", "frame", children=children)
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])
        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            return QtPilot(app_name="test-app", retries=1, delay=0.0)

    def test_find_exact_matches_only(self) -> None:
        """Exact match should return only the widget with the exact name."""
        pilot = self._make_pilot_with_named_buttons(["=", "x="])
        results = pilot.find(name="=", exact=True)
        assert len(results) == 1
        assert results[0].name == "="

    def test_find_substring_matches_both(self) -> None:
        """Substring match (default) returns both '=' and 'x='."""
        pilot = self._make_pilot_with_named_buttons(["=", "x="])
        results = pilot.find(name="=")
        assert len(results) == 2

    def test_find_exact_save_vs_save_as(self) -> None:
        """Exact match distinguishes 'Save' from 'Save As'."""
        pilot = self._make_pilot_with_named_buttons(["Save", "Save As"])
        results = pilot.find(name="Save", exact=True)
        assert len(results) == 1
        assert results[0].name == "Save"

    def test_find_one_exact_succeeds(self) -> None:
        """find_one with exact=True returns the exact match."""
        pilot = self._make_pilot_with_named_buttons(["=", "x="])
        widget = pilot.find_one(name="=", exact=True)
        assert widget.name == "="

    def test_find_exact_no_match(self) -> None:
        """Exact match returns empty when no widget has that exact name."""
        pilot = self._make_pilot_with_named_buttons(["=", "x="])
        results = pilot.find(name="equals", exact=True)
        assert results == []


# ── Tests for index parameter ───────────────────────────────────


class TestIndexParameter:
    """Test the index parameter on find_one."""

    def test_find_one_index_zero_returns_first(self) -> None:
        """index=0 returns the first match."""
        txt1 = _make_node("", "text", ext_height=300)
        txt2 = _make_node("", "text", ext_height=30)
        frame = _make_node("main", "frame", children=[txt1, txt2])
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])
        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
        widget = pilot.find_one(role="text", index=0)
        assert widget.get_extents().height == 300

    def test_find_one_index_one_returns_second(self) -> None:
        """index=1 returns the second match."""
        txt1 = _make_node("", "text", ext_height=300)
        txt2 = _make_node("", "text", ext_height=30)
        frame = _make_node("main", "frame", children=[txt1, txt2])
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])
        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
        widget = pilot.find_one(role="text", index=1)
        assert widget.get_extents().height == 30

    def test_find_one_index_out_of_range_raises(self) -> None:
        """index=5 with only 2 matches raises LookupError."""
        txt1 = _make_node("", "text")
        txt2 = _make_node("", "text")
        frame = _make_node("main", "frame", children=[txt1, txt2])
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])
        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
        with pytest.raises(LookupError, match="out of range"):
            pilot.find_one(role="text", index=5)

    def test_find_one_index_with_visible_filter(self) -> None:
        """index=0 with visible=True skips hidden widgets."""
        hidden = _make_node("", "text", ext_width=0, ext_height=0)
        visible = _make_node("", "text", ext_width=200, ext_height=40)
        frame = _make_node("main", "frame", children=[hidden, visible])
        app_native = _make_node("test-app", "application", children=[frame])
        desktop_native = _make_node("desktop", "desktop", children=[app_native])
        with patch.object(AtspiNode, "desktop", return_value=AtspiNode(desktop_native)):
            pilot = QtPilot(app_name="test-app", retries=1, delay=0.0)
        widget = pilot.find_one(role="text", visible=True, index=0)
        assert widget.get_extents().width == 200
