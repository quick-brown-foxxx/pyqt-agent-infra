"""AI agent infrastructure for Qt/PySide apps — inspect, interact, screenshot via AT-SPI."""

from __future__ import annotations

from typing import TYPE_CHECKING

__version__ = "0.1.0"

from qt_ai_dev_tools.models import Extents, WidgetInfo

if TYPE_CHECKING:
    from qt_ai_dev_tools.pilot import QtPilot


def __getattr__(name: str) -> object:
    """Lazy import for QtPilot (requires system gi package)."""
    if name == "QtPilot":
        from qt_ai_dev_tools.pilot import QtPilot

        return QtPilot
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = ["Extents", "QtPilot", "WidgetInfo"]
