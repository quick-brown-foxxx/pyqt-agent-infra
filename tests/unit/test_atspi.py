"""Unit tests for AtspiNode typed wrapper."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# Mock gi and Atspi before importing _atspi, since gi is a system package
# that may not be available in the test venv.
#
# setdefault is a no-op if real gi is already imported (VM environment).
# When running without real gi (host), the mock is installed permanently
# for this process. The _ensure_real_atspi fixture in e2e/conftest.py
# cleans up if needed for serial pytest runs. With xdist (-n auto),
# unit and e2e tests run in separate worker processes, so no cleanup
# is needed.
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

    # Default: no text iface, no action iface
    native.get_text_iface.return_value = None
    native.get_action_iface.return_value = None

    return native


class TestNameProperty:
    def test_returns_name(self) -> None:
        native = _make_native(name="Save")
        node = AtspiNode(native)
        assert node.name == "Save"

    def test_returns_empty_string_for_none(self) -> None:
        native = _make_native(name=None)
        node = AtspiNode(native)
        assert node.name == ""

    def test_returns_empty_string_for_empty(self) -> None:
        native = _make_native(name="")
        node = AtspiNode(native)
        assert node.name == ""


class TestRoleNameProperty:
    def test_returns_role_name(self) -> None:
        native = _make_native(role_name="label")
        node = AtspiNode(native)
        assert node.role_name == "label"


class TestChildCount:
    def test_returns_count(self) -> None:
        native = _make_native(child_count=5)
        node = AtspiNode(native)
        assert node.child_count == 5

    def test_returns_zero(self) -> None:
        native = _make_native(child_count=0)
        node = AtspiNode(native)
        assert node.child_count == 0


class TestChildAt:
    def test_returns_node_for_valid_child(self) -> None:
        child_native = _make_native(name="Child")
        native = _make_native(child_count=1, children=[child_native])
        node = AtspiNode(native)

        child = node.child_at(0)
        assert child is not None
        assert child.name == "Child"

    def test_returns_none_for_none_child(self) -> None:
        native = _make_native(child_count=1, children=[None])
        node = AtspiNode(native)

        child = node.child_at(0)
        assert child is None


class TestChildrenProperty:
    def test_returns_all_non_none_children(self) -> None:
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


class TestGetExtents:
    def test_returns_extents(self) -> None:
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


class TestGetText:
    def test_returns_text_from_text_iface(self) -> None:
        from qt_ai_dev_tools import _atspi as _atspi_mod

        native = _make_native(name="FallbackName")
        text_iface = MagicMock()
        native.get_text_iface.return_value = text_iface

        # get_text calls Atspi.Text.get_character_count / Atspi.Text.get_text (class-level).
        # Patch Atspi on the actual _atspi module (may be real gi or mock depending on env).
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
