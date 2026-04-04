"""Tests for bridge Qt namespace building.

Tests build_qt_namespace() in isolation — PySide6 is not available in the
test venv, so we verify the fallback behavior (empty namespace when import fails).
"""

from __future__ import annotations

import pytest

from qt_ai_dev_tools.bridge._qt_namespace import build_qt_namespace

pytestmark = pytest.mark.unit


class TestBuildQtNamespace:
    """Test namespace dict building."""

    def test_returns_dict(self) -> None:
        """Should return a dict."""
        ns = build_qt_namespace()
        assert isinstance(ns, dict)

    def test_has_underscore_key(self) -> None:
        """Should have '_' key for REPL-style last result."""
        ns = build_qt_namespace()
        assert "_" in ns
        assert ns["_"] is None

    def test_graceful_when_pyside6_unavailable(self) -> None:
        """Should return minimal namespace when PySide6 is not importable.

        In the test venv, PySide6 is typically not available (it's a system dep).
        build_qt_namespace() should suppress ImportError and return just {'_': None}.
        """
        ns = build_qt_namespace()
        # At minimum, we get the _ key
        assert "_" in ns
        # Without PySide6, we should NOT have Qt class names
        # (unless PySide6 happens to be installed in the test env)
        try:
            import PySide6  # noqa: F401

            # PySide6 available: namespace will have Qt entries
            assert "QWidget" in ns
        except ImportError:
            # PySide6 not available: namespace should be minimal
            assert "QWidget" not in ns

    def test_namespace_values_are_objects(self) -> None:
        """All namespace values should be valid Python objects (not None except _)."""
        ns = build_qt_namespace()
        for key, value in ns.items():
            if key == "_":
                assert value is None
            else:
                assert value is not None
