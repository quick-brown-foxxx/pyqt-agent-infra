"""Read widget state from AT-SPI objects."""

from __future__ import annotations

import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection

from qt_ai_dev_tools.models import Extents

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # type: ignore[import-untyped]  # noqa: E402  # rationale: system AT-SPI bindings


def get_name(widget: object) -> str:
    """Get the accessible name of a widget."""
    return widget.get_name() or ""  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs


def get_role(widget: object) -> str:
    """Get the role name of a widget (e.g. 'push button', 'text', 'label')."""
    return widget.get_role_name()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs


def get_extents(widget: object) -> Extents:
    """Get screen position and size of a widget."""
    ext = widget.get_extents(Atspi.CoordType.SCREEN)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
    return Extents(ext.x, ext.y, ext.width, ext.height)


def get_text(widget: object) -> str:
    """Get text content from a widget. Falls back to accessible name."""
    iface = widget.get_text_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if iface:
        return iface.get_text(0, iface.get_character_count())  # type: ignore[no-any-return]  # rationale: AT-SPI
    return widget.get_name() or ""  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs


def get_children(widget: object) -> list[object]:
    """Get direct children of a widget."""
    children: list[object] = []
    for i in range(widget.get_child_count()):  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        c = widget.get_child_at_index(i)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        if c:
            children.append(c)
    return children
