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
    value = node.get_value()

    entries.append(
        SnapshotEntry(
            role=node.role_name,
            name=node.name,
            text=text,
            value=value,
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
    # Group entries by (role, name) key, preserving order for duplicates
    old_map: dict[tuple[str, str], list[SnapshotEntry]] = {}
    for entry in old:
        old_map.setdefault((entry.role, entry.name), []).append(entry)

    new_map: dict[tuple[str, str], list[SnapshotEntry]] = {}
    for entry in new:
        new_map.setdefault((entry.role, entry.name), []).append(entry)

    all_keys = sorted(set(old_map.keys()) | set(new_map.keys()))

    added: list[SnapshotEntry] = []
    removed: list[SnapshotEntry] = []
    changed: list[tuple[SnapshotEntry, SnapshotEntry]] = []

    for key in all_keys:
        old_entries = old_map.get(key, [])
        new_entries = new_map.get(key, [])
        paired = min(len(old_entries), len(new_entries))

        # Positional matching for entries sharing the same (role, name)
        for i in range(paired):
            old_entry = old_entries[i]
            new_entry = new_entries[i]
            if (
                old_entry.text != new_entry.text
                or old_entry.value != new_entry.value
                or old_entry.children_count != new_entry.children_count
            ):
                changed.append((old_entry, new_entry))

        # Extra entries in new → added
        added.extend(new_entries[paired:])
        # Extra entries in old → removed
        removed.extend(old_entries[paired:])

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
            if old_entry.value != new_entry.value:
                lines.append(f"    value: {old_entry.value} -> {new_entry.value}")
            if old_entry.children_count != new_entry.children_count:
                lines.append(f"    children: {old_entry.children_count} -> {new_entry.children_count}")

    return "\n".join(lines)
