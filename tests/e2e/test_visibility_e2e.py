"""E2E tests for visibility filter (AT-SPI SHOWING state).

Verifies that the SHOWING-based visibility filter correctly identifies
visible vs hidden widgets in real Qt apps with AT-SPI.
"""

from __future__ import annotations

import os
import subprocess
import time

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
]


def _run_cli(*args: str, timeout: int = 15, app: str | None = "complex_app.py") -> subprocess.CompletedProcess[str]:
    """Run a qt-ai-dev-tools CLI command targeting the complex app."""
    app_args: tuple[str, ...] = ("--app", app) if app is not None else ()
    cmd = ["python3", "-m", "qt_ai_dev_tools", *args, *app_args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


class TestShowingState:
    """Tests that AT-SPI SHOWING state reflects actual widget visibility."""

    def test_visible_buttons_have_showing_state(self, complex_app: subprocess.Popen[str]) -> None:
        """Visible buttons in the running app report is_showing = True."""
        from qt_ai_dev_tools.pilot import QtPilot

        _ = complex_app
        pilot = QtPilot(app_name="complex_app.py")

        # Switch to Settings tab which has the "Show Dialog" button
        pilot.switch_tab("Settings")
        time.sleep(0.5)

        # Find buttons with visible=True — they must all have is_showing
        visible_buttons = pilot.find(role="push button", visible=True)
        assert len(visible_buttons) >= 1, "Expected at least one visible push button"

        for btn in visible_buttons:
            assert btn.is_showing, (
                f"Button '{btn.name}' was returned by find(visible=True) "
                "but is_showing is False"
            )

    def test_find_visible_returns_only_showing_widgets(self, complex_app: subprocess.Popen[str]) -> None:
        """pilot.find(visible=True) only returns widgets with is_showing=True."""
        from qt_ai_dev_tools.pilot import QtPilot

        _ = complex_app
        pilot = QtPilot(app_name="complex_app.py")

        # Switch to Inputs tab so some widgets are visible
        pilot.switch_tab("Inputs")
        time.sleep(0.5)

        visible_widgets = pilot.find(role="push button", visible=True)
        all_widgets = pilot.find(role="push button", visible=False)

        # visible should be a subset of all
        assert len(all_widgets) >= len(visible_widgets), (
            f"All widgets ({len(all_widgets)}) should be >= "
            f"visible widgets ({len(visible_widgets)})"
        )

        # Every visible widget must have is_showing
        for widget in visible_widgets:
            assert widget.is_showing, (
                f"Widget '{widget.name}' (role={widget.role_name}) returned by "
                "find(visible=True) but is_showing is False"
            )

    def test_find_no_visible_filter_includes_hidden(self, complex_app: subprocess.Popen[str]) -> None:
        """find(visible=False) returns >= count of find(visible=True)."""
        from qt_ai_dev_tools.pilot import QtPilot

        _ = complex_app
        pilot = QtPilot(app_name="complex_app.py")

        # All labels (some may be on hidden tabs)
        all_labels = pilot.find(role="label", visible=False)
        visible_labels = pilot.find(role="label", visible=True)

        assert len(all_labels) >= len(visible_labels), (
            f"Unfiltered labels ({len(all_labels)}) should be >= "
            f"visible labels ({len(visible_labels)})"
        )

    def test_closed_menu_items_not_showing(self, complex_app: subprocess.Popen[str]) -> None:
        """Submenu items in closed menus should have is_showing = False.

        Note: top-level menu bar items (File, Edit, Help) are always
        visible as they live in the menu bar.  Only items inside popup
        submenus (New, Save, Undo, About, etc.) should be hidden when
        their parent menu is closed.
        """
        from qt_ai_dev_tools.pilot import QtPilot

        _ = complex_app
        pilot = QtPilot(app_name="complex_app.py")

        # Make sure menus are closed
        _run_cli("key", "Escape", app=None)
        _run_cli("key", "Escape", app=None)
        time.sleep(0.3)

        # Look for specific submenu items that should be hidden
        # "New" is inside File menu, "Undo" is inside Edit menu
        submenu_names = ["New", "Save", "Undo", "About"]
        for name in submenu_names:
            items = pilot.find(role="menu item", name=name, visible=False)
            if not items:
                continue  # some AT-SPI versions may not expose closed menu items
            for item in items:
                assert not item.is_showing, (
                    f"Submenu item '{item.name}' should not be showing "
                    "with its parent menu closed"
                )

        # Also verify via visible filter: these submenu items should NOT appear
        for name in submenu_names:
            visible_items = pilot.find(role="menu item", name=name, visible=True)
            assert len(visible_items) == 0, (
                f"Submenu item '{name}' should not be visible with menus closed, "
                f"but find(visible=True) returned {len(visible_items)} results"
            )
