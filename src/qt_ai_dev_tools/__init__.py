"""AI agent infrastructure for Qt/PySide apps — inspect, interact, screenshot via AT-SPI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qt_ai_dev_tools.__version__ import __version__
from qt_ai_dev_tools.models import Extents, WidgetInfo

if TYPE_CHECKING:
    from qt_ai_dev_tools._atspi import AtspiNode
    from qt_ai_dev_tools.pilot import QtPilot


def __getattr__(name: str) -> object:
    """Lazy import for QtPilot and AtspiNode (require system gi package)."""
    if name == "QtPilot":
        from qt_ai_dev_tools.pilot import QtPilot

        return QtPilot
    if name == "AtspiNode":
        from qt_ai_dev_tools._atspi import AtspiNode

        return AtspiNode
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = ["AtspiNode", "Extents", "QtPilot", "WidgetInfo", "__version__"]
