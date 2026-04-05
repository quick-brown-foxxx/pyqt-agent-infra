"""Unit tests for tree snapshot capture and diff."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

# Mock gi and Atspi before importing snapshot (it imports AtspiNode via TYPE_CHECKING,
# but we need the mock for _atspi module resolution)
_mock_gi = MagicMock()
_mock_atspi_module = MagicMock()
_mock_gi.require_version = MagicMock()
_mock_gi.repository.Atspi = _mock_atspi_module

sys.modules.setdefault("gi", _mock_gi)
sys.modules.setdefault("gi.repository", _mock_gi.repository)
sys.modules.setdefault("gi.repository.Atspi", _mock_atspi_module)

from qt_ai_dev_tools._atspi import AtspiNode  # noqa: E402
from qt_ai_dev_tools.models import SnapshotDiff, SnapshotEntry  # noqa: E402
from qt_ai_dev_tools.snapshot import (  # noqa: E402
    capture_tree,
    diff_snapshots,
    format_diff,
    load_snapshot,
    save_snapshot,
)


def _make_native(
    *,
    name: str = "Widget",
    role_name: str = "push button",
    text: str | None = None,
    children: list[MagicMock] | None = None,
) -> MagicMock:
    """Create a mock AT-SPI native object."""
    native = MagicMock()
    native.get_name.return_value = name
    native.get_role_name.return_value = role_name

    child_list = children or []
    native.get_child_count.return_value = len(child_list)
    native.get_child_at_index.side_effect = lambda i: child_list[i] if i < len(child_list) else None

    # Text interface: return text if provided, otherwise fall back to name
    if text is not None and text != name:
        text_iface = MagicMock()
        _mock_atspi_module.Text.get_character_count.return_value = len(text)
        _mock_atspi_module.Text.get_text.return_value = text
        native.get_text_iface.return_value = text_iface
    else:
        native.get_text_iface.return_value = None

    native.get_action_iface.return_value = None
    return native


class TestCaptureTree:
    def test_single_node(self) -> None:
        native = _make_native(name="Save", role_name="push button")
        node = AtspiNode(native)
        entries = capture_tree(node)

        assert len(entries) == 1
        assert entries[0].role == "push button"
        assert entries[0].name == "Save"
        assert entries[0].text is None
        assert entries[0].children_count == 0

    def test_recursive_children(self) -> None:
        child1 = _make_native(name="OK", role_name="push button")
        child2 = _make_native(name="Cancel", role_name="push button")
        root = _make_native(name="Dialog", role_name="dialog", children=[child1, child2])
        node = AtspiNode(root)

        entries = capture_tree(node)

        assert len(entries) == 3
        assert entries[0].name == "Dialog"
        assert entries[0].children_count == 2
        assert entries[1].name == "OK"
        assert entries[2].name == "Cancel"

    def test_max_depth_limits_recursion(self) -> None:
        grandchild = _make_native(name="Deep", role_name="label")
        child = _make_native(name="Mid", role_name="panel", children=[grandchild])
        root = _make_native(name="Root", role_name="frame", children=[child])
        node = AtspiNode(root)

        # max_depth=1: root (depth 0) + child (depth 1), grandchild skipped
        entries = capture_tree(node, max_depth=1)

        assert len(entries) == 2
        assert entries[0].name == "Root"
        assert entries[1].name == "Mid"

    def test_text_dedup_when_same_as_name(self) -> None:
        """When text == name, store text as None to avoid redundancy."""
        native = _make_native(name="Status", role_name="label")
        # get_text falls back to name when no text iface
        node = AtspiNode(native)
        entries = capture_tree(node)

        assert entries[0].text is None

    def test_text_preserved_when_different(self) -> None:
        native = _make_native(name="input", role_name="text", text="hello world")
        node = AtspiNode(native)
        entries = capture_tree(node)

        assert entries[0].text == "hello world"


class TestSaveLoad:
    def test_round_trip(self, tmp_path: Path) -> None:
        entries = [
            SnapshotEntry(role="push button", name="Save", children_count=0),
            SnapshotEntry(role="text", name="input", text="hello", children_count=0),
        ]
        path = tmp_path / "snapshot.json"
        save_snapshot(entries, path)
        loaded = load_snapshot(path)

        assert len(loaded) == 2
        assert loaded[0].role == "push button"
        assert loaded[0].name == "Save"
        assert loaded[0].text is None
        assert loaded[1].text == "hello"

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_snapshot(tmp_path / "nonexistent.json")

    def test_parent_dir_creation(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "snapshot.json"
        entries = [SnapshotEntry(role="label", name="test")]
        save_snapshot(entries, path)

        assert path.exists()
        loaded = load_snapshot(path)
        assert len(loaded) == 1

    def test_json_structure(self, tmp_path: Path) -> None:
        entries = [SnapshotEntry(role="label", name="Status", text="OK", children_count=2)]
        path = tmp_path / "snap.json"
        save_snapshot(entries, path)

        raw = json.loads(path.read_text())
        assert len(raw) == 1
        assert raw[0]["role"] == "label"
        assert raw[0]["text"] == "OK"
        assert raw[0]["children_count"] == 2


class TestDiffSnapshots:
    def test_no_changes(self) -> None:
        entries = [SnapshotEntry(role="button", name="OK")]
        diff = diff_snapshots(entries, entries)

        assert not diff.has_changes
        assert diff.added == []
        assert diff.removed == []
        assert diff.changed == []

    def test_added_entries(self) -> None:
        old = [SnapshotEntry(role="button", name="OK")]
        new = [
            SnapshotEntry(role="button", name="OK"),
            SnapshotEntry(role="button", name="Cancel"),
        ]
        diff = diff_snapshots(old, new)

        assert diff.has_changes
        assert len(diff.added) == 1
        assert diff.added[0].name == "Cancel"
        assert diff.removed == []

    def test_removed_entries(self) -> None:
        old = [
            SnapshotEntry(role="button", name="OK"),
            SnapshotEntry(role="button", name="Cancel"),
        ]
        new = [SnapshotEntry(role="button", name="OK")]
        diff = diff_snapshots(old, new)

        assert diff.has_changes
        assert len(diff.removed) == 1
        assert diff.removed[0].name == "Cancel"

    def test_changed_text(self) -> None:
        old = [SnapshotEntry(role="label", name="status", text="Ready")]
        new = [SnapshotEntry(role="label", name="status", text="Done")]
        diff = diff_snapshots(old, new)

        assert diff.has_changes
        assert len(diff.changed) == 1
        old_entry, new_entry = diff.changed[0]
        assert old_entry.text == "Ready"
        assert new_entry.text == "Done"

    def test_changed_children_count(self) -> None:
        old = [SnapshotEntry(role="panel", name="list", children_count=2)]
        new = [SnapshotEntry(role="panel", name="list", children_count=5)]
        diff = diff_snapshots(old, new)

        assert diff.has_changes
        assert len(diff.changed) == 1
        _, new_entry = diff.changed[0]
        assert new_entry.children_count == 5

    def test_empty_snapshots(self) -> None:
        diff = diff_snapshots([], [])
        assert not diff.has_changes

    def test_all_added_from_empty(self) -> None:
        new = [SnapshotEntry(role="button", name="OK")]
        diff = diff_snapshots([], new)

        assert diff.has_changes
        assert len(diff.added) == 1

    def test_all_removed_to_empty(self) -> None:
        old = [SnapshotEntry(role="button", name="OK")]
        diff = diff_snapshots(old, [])

        assert diff.has_changes
        assert len(diff.removed) == 1


class TestFormatDiff:
    def test_no_changes_message(self) -> None:
        diff = SnapshotDiff(added=[], removed=[], changed=[])
        assert format_diff(diff) == "No changes detected."

    def test_added_formatting(self) -> None:
        diff = SnapshotDiff(
            added=[SnapshotEntry(role="button", name="New")],
            removed=[],
            changed=[],
        )
        result = format_diff(diff)
        assert "Added:" in result
        assert '+ [button] "New"' in result

    def test_removed_formatting(self) -> None:
        diff = SnapshotDiff(
            added=[],
            removed=[SnapshotEntry(role="button", name="Old")],
            changed=[],
        )
        result = format_diff(diff)
        assert "Removed:" in result
        assert '- [button] "Old"' in result

    def test_changed_formatting(self) -> None:
        diff = SnapshotDiff(
            added=[],
            removed=[],
            changed=[
                (
                    SnapshotEntry(role="label", name="status", text="Ready", children_count=0),
                    SnapshotEntry(role="label", name="status", text="Done", children_count=3),
                )
            ],
        )
        result = format_diff(diff)
        assert "Changed:" in result
        assert '~ [label] "status"' in result
        assert "'Ready' -> 'Done'" in result
        assert "children: 0 -> 3" in result

    def test_combined_formatting(self) -> None:
        diff = SnapshotDiff(
            added=[SnapshotEntry(role="button", name="New")],
            removed=[SnapshotEntry(role="button", name="Old")],
            changed=[
                (
                    SnapshotEntry(role="label", name="x", text="a"),
                    SnapshotEntry(role="label", name="x", text="b"),
                )
            ],
        )
        result = format_diff(diff)
        assert "Added:" in result
        assert "Removed:" in result
        assert "Changed:" in result
