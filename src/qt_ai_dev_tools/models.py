"""Data types for qt-ai-dev-tools."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Extents:
    """Screen coordinates and dimensions of a widget."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        """Center point of the widget bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass(slots=True)
class WidgetInfo:
    """Serializable widget information (decoupled from AT-SPI objects)."""

    role: str
    name: str
    extents: Extents | None = None
    text: str | None = None
    children_count: int = 0

    def __str__(self) -> str:
        """Human-readable representation for CLI output."""
        s = f'[{self.role}] "{self.name}"'
        if self.extents:
            e = self.extents
            s += f" @({e.x},{e.y} {e.width}x{e.height})"
        return s

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict, omitting None fields."""
        d: dict[str, object] = {"role": self.role, "name": self.name}
        if self.extents:
            d["extents"] = {
                "x": self.extents.x,
                "y": self.extents.y,
                "width": self.extents.width,
                "height": self.extents.height,
            }
        if self.text is not None:
            d["text"] = self.text
        d["children_count"] = self.children_count
        return d
