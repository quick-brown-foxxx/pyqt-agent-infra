"""Read widget state from AT-SPI objects."""

from __future__ import annotations

from qt_ai_dev_tools._atspi import AtspiNode
from qt_ai_dev_tools.models import Extents


def get_name(widget: AtspiNode) -> str:
    """Get the accessible name of a widget."""
    return widget.name


def get_role(widget: AtspiNode) -> str:
    """Get the role name of a widget (e.g. 'push button', 'text', 'label')."""
    return widget.role_name


def get_extents(widget: AtspiNode) -> Extents:
    """Get screen position and size of a widget."""
    return widget.get_extents()


def get_text(widget: AtspiNode) -> str:
    """Get text content from a widget. Falls back to accessible name."""
    return widget.get_text()


def get_children(widget: AtspiNode) -> list[AtspiNode]:
    """Get direct children of a widget."""
    return widget.children
