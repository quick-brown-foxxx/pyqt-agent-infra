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


@dataclass(slots=True)
class SnapshotEntry:
    """Single widget in a tree snapshot."""

    role: str
    name: str
    text: str | None = None
    children_count: int = 0

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict, omitting None text."""
        d: dict[str, object] = {"role": self.role, "name": self.name}
        if self.text is not None:
            d["text"] = self.text
        d["children_count"] = self.children_count
        return d

    @staticmethod
    def from_dict(d: dict[str, object]) -> SnapshotEntry:
        """Reconstruct from a dict (e.g. loaded from JSON)."""
        raw_count = d.get("children_count", 0)
        return SnapshotEntry(
            role=str(d["role"]),
            name=str(d["name"]),
            text=str(d["text"]) if d.get("text") is not None else None,
            children_count=int(raw_count),  # type: ignore[arg-type]  # rationale: raw JSON value is object, validated by int()
        )


@dataclass(slots=True)
class SnapshotDiff:
    """Difference between two tree snapshots."""

    added: list[SnapshotEntry]
    removed: list[SnapshotEntry]
    changed: list[tuple[SnapshotEntry, SnapshotEntry]]

    @property
    def has_changes(self) -> bool:
        """True if any additions, removals, or changes detected."""
        return bool(self.added or self.removed or self.changed)
