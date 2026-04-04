"""Unit tests for qt_ai_dev_tools data models."""

import pytest

from qt_ai_dev_tools.models import Extents, WidgetInfo

pytestmark = pytest.mark.unit


class TestExtents:
    def test_center_calculation(self) -> None:
        ext = Extents(x=100, y=200, width=80, height=40)
        assert ext.center == (140, 220)

    def test_center_odd_dimensions(self) -> None:
        ext = Extents(x=0, y=0, width=101, height=51)
        assert ext.center == (50, 25)


class TestWidgetInfo:
    def test_display_format(self) -> None:
        info = WidgetInfo(role="push button", name="Save", extents=Extents(100, 200, 80, 30))
        assert str(info) == '[push button] "Save" @(100,200 80x30)'

    def test_display_no_extents(self) -> None:
        info = WidgetInfo(role="label", name="Status")
        assert str(info) == '[label] "Status"'

    def test_to_dict_full(self) -> None:
        info = WidgetInfo(
            role="text",
            name="input",
            text="hello",
            extents=Extents(10, 20, 300, 25),
            children_count=0,
        )
        d = info.to_dict()
        assert d["role"] == "text"
        assert d["name"] == "input"
        assert d["text"] == "hello"
        assert d["extents"] == {"x": 10, "y": 20, "width": 300, "height": 25}

    def test_to_dict_minimal(self) -> None:
        info = WidgetInfo(role="label", name="Status")
        d = info.to_dict()
        assert d["role"] == "label"
        assert d["name"] == "Status"
        assert "extents" not in d
        assert "text" not in d
