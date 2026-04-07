"""Tests for CLI helper functions (_widget_line and _widget_dict)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from qt_ai_dev_tools.models import Extents

# Mock gi and Atspi before importing CLI helpers, since gi is a system package.
# Patches must persist (not context-managed) because _widget_dict does a lazy
# import of qt_ai_dev_tools.pilot which triggers _atspi.py → gi at call time.
_mock_gi = MagicMock()
_mock_gi.require_version = MagicMock()
_mock_gi.repository.Atspi = MagicMock()
sys.modules.setdefault("gi", _mock_gi)
sys.modules.setdefault("gi.repository", _mock_gi.repository)

from qt_ai_dev_tools.cli import _widget_dict, _widget_line  # noqa: E402

pytestmark = pytest.mark.unit


def _make_widget(name: str, role_name: str, extents: Extents, text: str = "", *, showing: bool = True) -> MagicMock:
    """Create a mock AtspiNode-like widget."""
    widget = MagicMock()
    widget.name = name
    widget.role_name = role_name
    widget.get_extents.return_value = extents
    widget.get_text.return_value = text
    widget.is_showing = showing
    return widget


class TestWidgetLine:
    """Tests for _widget_line formatting."""

    def test_formats_correctly(self) -> None:
        widget = _make_widget("OK", "push button", Extents(x=100, y=200, width=80, height=30))

        result = _widget_line(widget)

        assert result == '[push button] "OK" @(100,200 80x30)'

    def test_empty_name(self) -> None:
        widget = _make_widget("", "label", Extents(x=0, y=0, width=50, height=20))

        result = _widget_line(widget)

        assert result == '[label] "" @(0,0 50x20)'


class TestWidgetDict:
    """Tests for _widget_dict serialization."""

    def test_includes_visible_true(self) -> None:
        widget = _make_widget("Save", "push button", Extents(x=10, y=20, width=80, height=30), text="")

        result = _widget_dict(widget)

        assert result["visible"] is True
        assert result["role"] == "push button"
        assert result["name"] == "Save"

    def test_includes_visible_false_zero_size(self) -> None:
        widget = _make_widget("Hidden", "label", Extents(x=0, y=0, width=0, height=0), text="ghost")

        result = _widget_dict(widget)

        assert result["visible"] is False
        assert result["text"] == "ghost"

    def test_includes_visible_false_zero_width(self) -> None:
        widget = _make_widget("Collapsed", "panel", Extents(x=5, y=5, width=0, height=100))

        result = _widget_dict(widget)

        assert result["visible"] is False

    def test_widget_dict_not_showing_is_not_visible(self) -> None:
        """Widget with showing=False should have visible=False even with valid extents."""
        widget = _make_widget("Button", "push button", Extents(10, 20, 100, 50), showing=False)
        result = _widget_dict(widget)
        assert result["visible"] is False

    def test_extents_dict(self) -> None:
        widget = _make_widget("Btn", "push button", Extents(x=10, y=20, width=80, height=30))

        result = _widget_dict(widget)

        assert result["extents"] == {"x": 10, "y": 20, "width": 80, "height": 30}
