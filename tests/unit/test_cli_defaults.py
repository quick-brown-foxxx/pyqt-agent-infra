"""Tests for CLI command parameter consistency."""

from __future__ import annotations

import inspect


def test_tree_visible_default_matches_find() -> None:
    """tree and find should have the same default for --visible."""
    from qt_ai_dev_tools.cli import find, tree

    tree_params = inspect.signature(tree).parameters
    find_params = inspect.signature(find).parameters
    assert tree_params["visible"].default == find_params["visible"].default
