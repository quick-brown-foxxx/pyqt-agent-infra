"""Tree snapshot capture and diff utilities.

Serialize the AT-SPI widget tree to JSON for state comparison.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from qt_ai_dev_tools.models import SnapshotDiff, SnapshotEntry

if TYPE_CHECKING:
    from qt_ai_dev_tools._atspi import AtspiNode


def capture_tree(root: AtspiNode, max_depth: int = 8) -> list[SnapshotEntry]:
    """Walk the AT-SPI tree from root and collect snapshot entries.

    Args:
        root: Root node to start walking from.
        max_depth: Maximum recursion depth (default 8).

    Returns:
        Flat list of SnapshotEntry for every node visited.
    """
    entries: list[SnapshotEntry] = []
    _walk(root, entries, depth=0, max_depth=max_depth)
    return entries


def _walk(
    node: AtspiNode,
    entries: list[SnapshotEntry],
    *,
    depth: int,
    max_depth: int,
) -> None:
    """Recursively collect entries from the tree."""
    text_value = node.get_text()
    # Avoid storing redundant text when it matches the name
    text = text_value if text_value != node.name else None

    entries.append(
        SnapshotEntry(
            role=node.role_name,
            name=node.name,
            text=text,
            children_count=node.child_count,
        )
    )

    if depth >= max_depth:
        return

    for child in node.children:
        _walk(child, entries, depth=depth + 1, max_depth=max_depth)


def save_snapshot(entries: list[SnapshotEntry], path: Path) -> None:
    """Serialize snapshot entries to a JSON file.

    Creates parent directories if they don't exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [e.to_dict() for e in entries]
    path.write_text(json.dumps(data, indent=2))


def load_snapshot(path: Path) -> list[SnapshotEntry]:
    """Load snapshot entries from a JSON file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    parsed: list[dict[str, object]] = json.loads(path.read_text())  # type: ignore[assignment]  # rationale: json.loads returns Any; we validate structure via from_dict
    return [SnapshotEntry.from_dict(item) for item in parsed]


def diff_snapshots(
    old: list[SnapshotEntry],
    new: list[SnapshotEntry],
) -> SnapshotDiff:
    """Compare two snapshots and return the differences.

    Matches entries by (role, name) key. Detects added, removed,
    and changed entries (text or children_count differ).
    """
    old_map: dict[tuple[str, str], SnapshotEntry] = {}
    for entry in old:
        key = (entry.role, entry.name)
        old_map[key] = entry

    new_map: dict[tuple[str, str], SnapshotEntry] = {}
    for entry in new:
        key = (entry.role, entry.name)
        new_map[key] = entry

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    added = [new_map[k] for k in sorted(new_keys - old_keys)]
    removed = [old_map[k] for k in sorted(old_keys - new_keys)]

    changed: list[tuple[SnapshotEntry, SnapshotEntry]] = []
    for key in sorted(old_keys & new_keys):
        old_entry = old_map[key]
        new_entry = new_map[key]
        if old_entry.text != new_entry.text or old_entry.children_count != new_entry.children_count:
            changed.append((old_entry, new_entry))

    return SnapshotDiff(added=added, removed=removed, changed=changed)


def format_diff(diff: SnapshotDiff) -> str:
    """Format a SnapshotDiff as human-readable text."""
    if not diff.has_changes:
        return "No changes detected."

    lines: list[str] = []

    if diff.added:
        lines.append("Added:")
        lines.extend(f'  + [{entry.role}] "{entry.name}"' for entry in diff.added)

    if diff.removed:
        lines.append("Removed:")
        lines.extend(f'  - [{entry.role}] "{entry.name}"' for entry in diff.removed)

    if diff.changed:
        lines.append("Changed:")
        for old_entry, new_entry in diff.changed:
            lines.append(f'  ~ [{old_entry.role}] "{old_entry.name}"')
            if old_entry.text != new_entry.text:
                lines.append(f"    text: {old_entry.text!r} -> {new_entry.text!r}")
            if old_entry.children_count != new_entry.children_count:
                lines.append(f"    children: {old_entry.children_count} -> {new_entry.children_count}")

    return "\n".join(lines)
