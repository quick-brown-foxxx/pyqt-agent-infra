"""Unit tests for AtspiNode typed wrapper.

Tests focus on real logic: None handling, fallback behavior, error paths,
dataclass conversion, and interface availability checks. Tautological tests
(mock returns what it was told to return) have been removed.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# Mock gi and Atspi before importing _atspi, since gi is a system package
# that may not be available in the test venv.
_mock_gi = MagicMock()
_mock_atspi_module = MagicMock()
_mock_gi.require_version = MagicMock()
_mock_gi.repository.Atspi = _mock_atspi_module

sys.modules.setdefault("gi", _mock_gi)
sys.modules.setdefault("gi.repository", _mock_gi.repository)
sys.modules.setdefault("gi.repository.Atspi", _mock_atspi_module)

from qt_ai_dev_tools._atspi import AtspiNode  # noqa: E402
from qt_ai_dev_tools.models import Extents  # noqa: E402


def _make_native(
    *,
    name: str | None = "TestWidget",
    role_name: str = "push button",
    child_count: int = 0,
    children: list[object] | None = None,
) -> MagicMock:
    """Create a mock AT-SPI native object with sensible defaults."""
    native = MagicMock()
    native.get_name.return_value = name
    native.get_role_name.return_value = role_name
    native.get_child_count.return_value = child_count

    if children is not None:
        native.get_child_at_index.side_effect = lambda i: children[i] if i < len(children) else None
    else:
        native.get_child_at_index.return_value = None

    # Default: no interfaces
    native.get_text_iface.return_value = None
    native.get_action_iface.return_value = None
    native.get_value_iface.return_value = None
    native.get_selection_iface.return_value = None
    native.get_table_iface.return_value = None

    return native


# ------------------------------------------------------------------
# Name property: only the None/empty → "" conversion logic is tested
# ------------------------------------------------------------------


class TestNameProperty:
    def test_none_name_returns_empty_string(self) -> None:
        native = _make_native(name=None)
        node = AtspiNode(native)
        assert node.name == ""

    def test_empty_name_returns_empty_string(self) -> None:
        native = _make_native(name="")
        node = AtspiNode(native)
        assert node.name == ""


# ------------------------------------------------------------------
# Children: filtering None entries is real logic
# ------------------------------------------------------------------


class TestChildrenFiltering:
    def test_filters_none_children(self) -> None:
        child1 = _make_native(name="A")
        child2 = _make_native(name="B")
        native = _make_native(child_count=3, children=[child1, None, child2])
        node = AtspiNode(native)

        children = node.children
        assert len(children) == 2
        assert children[0].name == "A"
        assert children[1].name == "B"

    def test_returns_empty_list_for_no_children(self) -> None:
        native = _make_native(child_count=0)
        node = AtspiNode(native)
        assert node.children == []

    def test_all_none_children(self) -> None:
        native = _make_native(child_count=3, children=[None, None, None])
        node = AtspiNode(native)
        assert node.children == []


# ------------------------------------------------------------------
# child_at: only None-wrapping logic tested (not tautological wrap)
# ------------------------------------------------------------------


class TestChildAt:
    def test_returns_none_for_none_child(self) -> None:
        native = _make_native(child_count=1, children=[None])
        node = AtspiNode(native)

        child = node.child_at(0)
        assert child is None


# ------------------------------------------------------------------
# Extents: tests conversion to Extents dataclass + center calc
# ------------------------------------------------------------------


class TestGetExtents:
    def test_converts_to_extents_dataclass(self) -> None:
        native = _make_native()
        ext_mock = MagicMock()
        ext_mock.x = 10
        ext_mock.y = 20
        ext_mock.width = 100
        ext_mock.height = 50
        native.get_extents.return_value = ext_mock
        node = AtspiNode(native)

        extents = node.get_extents()
        assert isinstance(extents, Extents)
        assert extents.x == 10
        assert extents.y == 20
        assert extents.width == 100
        assert extents.height == 50

    def test_center_calculation(self) -> None:
        native = _make_native()
        ext_mock = MagicMock()
        ext_mock.x = 100
        ext_mock.y = 200
        ext_mock.width = 60
        ext_mock.height = 40
        native.get_extents.return_value = ext_mock
        node = AtspiNode(native)

        extents = node.get_extents()
        assert extents.center == (130, 220)


# ------------------------------------------------------------------
# Text: fallback logic (text iface → name)
# ------------------------------------------------------------------


class TestGetText:
    def test_returns_text_from_text_iface(self) -> None:
        from qt_ai_dev_tools import _atspi as _atspi_mod

        native = _make_native(name="FallbackName")
        text_iface = MagicMock()
        native.get_text_iface.return_value = text_iface

        mock_text = MagicMock()
        mock_text.get_character_count.return_value = 11
        mock_text.get_text.return_value = "Hello World"
        with patch.object(_atspi_mod, "Atspi", **{"Text": mock_text}):
            node = AtspiNode(native)
            assert node.get_text() == "Hello World"
            mock_text.get_text.assert_called_once_with(text_iface, 0, 11)

    def test_falls_back_to_name_when_no_text_iface(self) -> None:
        native = _make_native(name="ButtonLabel")
        native.get_text_iface.return_value = None
        node = AtspiNode(native)

        assert node.get_text() == "ButtonLabel"

    def test_empty_text_returns_empty_string(self) -> None:
        from qt_ai_dev_tools import _atspi as _atspi_mod

        native = _make_native(name="")
        text_iface = MagicMock()
        native.get_text_iface.return_value = text_iface

        mock_text = MagicMock()
        mock_text.get_character_count.return_value = 0
        mock_text.get_text.return_value = ""
        with patch.object(_atspi_mod, "Atspi", **{"Text": mock_text}):
            node = AtspiNode(native)
            assert node.get_text() == ""

    def test_no_text_iface_and_none_name_returns_empty(self) -> None:
        native = _make_native(name=None)
        native.get_text_iface.return_value = None
        node = AtspiNode(native)

        assert node.get_text() == ""


# ------------------------------------------------------------------
# Actions: lookup logic, error paths
# ------------------------------------------------------------------


class TestGetActionNames:
    def test_returns_action_names(self) -> None:
        native = _make_native()
        action_iface = MagicMock()
        action_iface.get_n_actions.return_value = 2
        action_iface.get_action_name.side_effect = lambda i: ["click", "press"][i]
        native.get_action_iface.return_value = action_iface
        node = AtspiNode(native)

        assert node.get_action_names() == ["click", "press"]

    def test_returns_empty_list_when_no_action_iface(self) -> None:
        native = _make_native()
        native.get_action_iface.return_value = None
        node = AtspiNode(native)

        assert node.get_action_names() == []


class TestDoAction:
    def test_executes_matching_action(self) -> None:
        native = _make_native()
        action_iface = MagicMock()
        action_iface.get_n_actions.return_value = 2
        action_iface.get_action_name.side_effect = lambda i: ["click", "press"][i]
        native.get_action_iface.return_value = action_iface
        node = AtspiNode(native)

        node.do_action("press", pause=0.0)
        action_iface.do_action.assert_called_once_with(1)

    def test_raises_lookup_error_for_unknown_action(self) -> None:
        native = _make_native()
        action_iface = MagicMock()
        action_iface.get_n_actions.return_value = 1
        action_iface.get_action_name.side_effect = lambda i: ["click"][i]
        native.get_action_iface.return_value = action_iface
        node = AtspiNode(native)

        with pytest.raises(LookupError, match="nonexistent"):
            node.do_action("nonexistent", pause=0.0)

    def test_raises_runtime_error_when_no_action_iface(self) -> None:
        native = _make_native()
        native.get_action_iface.return_value = None
        node = AtspiNode(native)

        with pytest.raises(RuntimeError, match="no action interface"):
            node.do_action("click", pause=0.0)


class TestHasActionIface:
    def test_true_when_iface_exists(self) -> None:
        native = _make_native()
        native.get_action_iface.return_value = MagicMock()
        node = AtspiNode(native)

        assert node.has_action_iface is True

    def test_false_when_no_iface(self) -> None:
        native = _make_native()
        native.get_action_iface.return_value = None
        node = AtspiNode(native)

        assert node.has_action_iface is False


# ------------------------------------------------------------------
# Value interface
# ------------------------------------------------------------------


class TestValueInterface:
    def test_has_value_iface_true(self) -> None:
        native = _make_native()
        native.get_value_iface.return_value = MagicMock()
        node = AtspiNode(native)
        assert node.has_value_iface is True

    def test_has_value_iface_false(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.has_value_iface is False

    def test_get_value_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_value() is None

    def test_get_value_returns_current_value(self) -> None:
        native = _make_native()
        value_iface = MagicMock()
        value_iface.get_current_value.return_value = 42.5
        native.get_value_iface.return_value = value_iface
        node = AtspiNode(native)
        assert node.get_value() == 42.5

    def test_set_value_raises_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        with pytest.raises(RuntimeError, match="no value interface"):
            node.set_value(10.0)

    def test_set_value_calls_iface(self) -> None:
        native = _make_native()
        value_iface = MagicMock()
        native.get_value_iface.return_value = value_iface
        node = AtspiNode(native)
        node.set_value(75.0)
        value_iface.set_current_value.assert_called_once_with(75.0)

    def test_get_minimum_value_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_minimum_value() is None

    def test_get_maximum_value_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_maximum_value() is None

    def test_get_minimum_value_returns_value(self) -> None:
        native = _make_native()
        value_iface = MagicMock()
        value_iface.get_minimum_value.return_value = 0.0
        native.get_value_iface.return_value = value_iface
        node = AtspiNode(native)
        assert node.get_minimum_value() == 0.0

    def test_get_maximum_value_returns_value(self) -> None:
        native = _make_native()
        value_iface = MagicMock()
        value_iface.get_maximum_value.return_value = 100.0
        native.get_value_iface.return_value = value_iface
        node = AtspiNode(native)
        assert node.get_maximum_value() == 100.0


# ------------------------------------------------------------------
# Selection interface
# ------------------------------------------------------------------


class TestSelectionInterface:
    def test_has_selection_iface_true(self) -> None:
        native = _make_native()
        native.get_selection_iface.return_value = MagicMock()
        node = AtspiNode(native)
        assert node.has_selection_iface is True

    def test_has_selection_iface_false(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.has_selection_iface is False

    def test_get_n_selected_returns_zero_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_n_selected_children() == 0

    def test_select_child_returns_false_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.select_child(0) is False

    def test_select_child_calls_iface(self) -> None:
        native = _make_native()
        sel_iface = MagicMock()
        sel_iface.select_child.return_value = True
        native.get_selection_iface.return_value = sel_iface
        node = AtspiNode(native)
        result = node.select_child(2)
        assert result is True
        sel_iface.select_child.assert_called_once_with(2)

    def test_get_selected_child_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_selected_child() is None

    def test_get_selected_child_wraps_result(self) -> None:
        native = _make_native()
        sel_iface = MagicMock()
        child_native = _make_native(name="Selected")
        sel_iface.get_selected_child.return_value = child_native
        native.get_selection_iface.return_value = sel_iface
        node = AtspiNode(native)

        child = node.get_selected_child(0)
        assert child is not None
        assert child.name == "Selected"

    def test_get_selected_child_returns_none_for_none_child(self) -> None:
        native = _make_native()
        sel_iface = MagicMock()
        sel_iface.get_selected_child.return_value = None
        native.get_selection_iface.return_value = sel_iface
        node = AtspiNode(native)
        assert node.get_selected_child(0) is None

    def test_is_child_selected_returns_false_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.is_child_selected(0) is False

    def test_deselect_child_returns_false_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.deselect_child(0) is False


# ------------------------------------------------------------------
# Table interface
# ------------------------------------------------------------------


class TestTableInterface:
    def test_has_table_iface_true(self) -> None:
        native = _make_native()
        native.get_table_iface.return_value = MagicMock()
        node = AtspiNode(native)
        assert node.has_table_iface is True

    def test_has_table_iface_false(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.has_table_iface is False

    def test_get_n_rows_returns_zero_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_n_rows() == 0

    def test_get_n_columns_returns_zero_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_n_columns() == 0

    def test_get_cell_at_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        node = AtspiNode(native)
        assert node.get_cell_at(0, 0) is None

    def test_get_cell_at_wraps_result(self) -> None:
        native = _make_native()
        table_iface = MagicMock()
        cell_native = _make_native(name="Cell_0_1")
        table_iface.get_accessible_at.return_value = cell_native
        native.get_table_iface.return_value = table_iface
        node = AtspiNode(native)

        cell = node.get_cell_at(0, 1)
        assert cell is not None
        assert cell.name == "Cell_0_1"
        table_iface.get_accessible_at.assert_called_once_with(0, 1)

    def test_get_cell_at_returns_none_for_none_cell(self) -> None:
        native = _make_native()
        table_iface = MagicMock()
        table_iface.get_accessible_at.return_value = None
        native.get_table_iface.return_value = table_iface
        node = AtspiNode(native)
        assert node.get_cell_at(0, 0) is None


# ------------------------------------------------------------------
# Desktop + repr
# ------------------------------------------------------------------


class TestDesktop:
    @patch("qt_ai_dev_tools._atspi.Atspi")
    def test_wraps_atspi_desktop(self, mock_atspi: MagicMock) -> None:
        desktop_native = _make_native(name="Desktop", role_name="desktop frame")
        mock_atspi.get_desktop.return_value = desktop_native

        node = AtspiNode.desktop(0)
        assert node.name == "Desktop"
        mock_atspi.get_desktop.assert_called_once_with(0)


class TestRepr:
    def test_repr_format(self) -> None:
        native = _make_native(name="Save", role_name="push button")
        node = AtspiNode(native)

        assert repr(node) == 'AtspiNode([push button] "Save")'
