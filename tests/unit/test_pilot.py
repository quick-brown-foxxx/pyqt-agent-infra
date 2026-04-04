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
