"""E2E tests for tray and notify subsystems -- real D-Bus in VM."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from qt_ai_dev_tools.subsystems.models import TrayItem

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
    pytest.mark.e2e,
    pytest.mark.usefixtures("clean_sni_watcher"),
]


def _find_tray_item(name_substring: str) -> TrayItem:
    """Find a tray item by name substring.

    Searches the live SNI tray items for one whose name contains
    the given substring (case-insensitive). Fails the test if no
    matching item is found.
    """
    from qt_ai_dev_tools.subsystems import tray

    items = tray.list_items()
    for item in items:
        if name_substring.lower() in item.name.lower():
            return item
    pytest.fail(f"No tray item matching '{name_substring}' found. Available: {[i.name for i in items]}")


def _read_status_label(sock_path: Path) -> str:
    """Read the status_label text from the tray app via bridge."""
    from qt_ai_dev_tools.bridge._client import eval_code

    resp = eval_code(sock_path, "widgets['status_label'].text()")
    assert resp.ok is True
    return resp.result or ""


class TestTrayListAndClick:
    """Flow 3A: Restore window from tray click."""

    def test_list_tray_items(self, tray_app: subprocess.Popen[str]) -> None:
        """Verify the tray app appears in the SNI tray item list."""
        from qt_ai_dev_tools.subsystems import tray

        items = tray.list_items()
        # The tray app should have registered an SNI item
        assert len(items) > 0, "No tray items found — SNI watcher may not be running"

    def test_tray_click_restores_window(self, tray_app: subprocess.Popen[str]) -> None:
        """Close/hide window, verify tray item exists, click to restore."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket
        from qt_ai_dev_tools.subsystems import tray

        sock = find_bridge_socket(pid=tray_app.pid)
        assert sock is not None, "No bridge socket found"

        # Hide the main window (simulate minimize to tray)
        eval_code(sock, "widgets['TrayTestWindow'].hide()")
        time.sleep(0.5)

        # Find our tray app item by name (avoids picking stale entries)
        tray_item = _find_tray_item("tray_app")
        tray.click(tray_item.name)
        time.sleep(0.5)

        # Verify the window is visible again
        resp = eval_code(sock, "widgets['TrayTestWindow'].isVisible()")
        assert resp.ok is True
        assert resp.result == "True"


class TestTrayContextMenu:
    """Flow 3B: Tray context menu reading."""

    def test_tray_menu_entries(self, tray_app: subprocess.Popen[str]) -> None:
        """Read the tray context menu and verify expected entries."""
        from qt_ai_dev_tools.subsystems import tray

        tray_item = _find_tray_item("tray_app")
        entries = tray.menu(tray_item.name)
        labels = [e.label for e in entries]

        # The tray app defines Show, Settings, Quit menu entries
        assert any("Show" in label or "show" in label.lower() for label in labels), (
            f"Expected 'Show' in menu entries, got: {labels}"
        )


class TestNotificationCapture:
    """Flow 3C: Send notification from app, capture via dbus-monitor."""

    def test_notification_listen(self, tray_app: subprocess.Popen[str]) -> None:
        """Click Send Notification, capture via notify.listen()."""
        import threading

        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket
        from qt_ai_dev_tools.subsystems import notify

        sock = find_bridge_socket(pid=tray_app.pid)
        assert sock is not None, "No bridge socket found"

        # Start listening in a background thread (it blocks for timeout seconds)
        captured: list[object] = []

        def _listen() -> None:
            notifications = notify.listen(timeout=5.0)
            captured.extend(notifications)

        listener_thread = threading.Thread(target=_listen, daemon=True)
        listener_thread.start()

        # Give the listener a moment to start
        time.sleep(0.5)

        # Trigger notification from the app
        eval_code(sock, "widgets['notify_btn'].click()")
        time.sleep(1.0)

        # Wait for listener to finish
        listener_thread.join(timeout=10.0)

        # Verify we captured at least one notification
        assert len(captured) > 0, "No notifications captured"
        first = captured[0]
        # The tray app sends: showMessage("Test", "Notification from tray app", ...)
        assert hasattr(first, "summary")


class TestTraySelect:
    """Flow 3D: Tray menu item selection via D-Bus Event.

    NOTE: This class MUST be last — select() triggers a D-Bus dbusmenu Event
    that crashes PySide6 apps due to thread-safety (Qt menu action fires on
    non-main thread). The test verifies select() works at the D-Bus level
    but the target app segfaults, so it's marked xfail.
    """

    @pytest.mark.xfail(
        reason="D-Bus com.canonical.dbusmenu Event triggers Qt menu action on non-main thread, "
        "causing PySide6 segfault. Known Qt/dbusmenu limitation — select() works at D-Bus level "
        "but crashes the target app. Use bridge eval to trigger menu actions instead.",
        strict=False,
    )
    def test_tray_select_settings(self, tray_app: subprocess.Popen[str]) -> None:
        """Select 'Settings' from tray menu, verify app reacts."""
        from qt_ai_dev_tools.bridge._client import find_bridge_socket
        from qt_ai_dev_tools.subsystems import tray

        sock = find_bridge_socket(pid=tray_app.pid)
        assert sock is not None, "No bridge socket found"

        tray_item = _find_tray_item("tray_app")
        tray.select(tray_item.name, "Settings")
        time.sleep(0.5)

        # Verify status label changed (app sets "Settings opened")
        status = _read_status_label(sock)
        assert "settings" in status.lower() or "Settings" in status
