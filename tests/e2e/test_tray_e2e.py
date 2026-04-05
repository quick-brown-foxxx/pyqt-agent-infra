"""E2E tests for tray and notify subsystems -- real D-Bus in VM."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
    pytest.mark.e2e,
]


_skip_no_sni = pytest.mark.skip(
    reason="SNI watcher (org.kde.StatusNotifierWatcher) not available — "
    "openbox+stalonetray provides XEmbed only, not StatusNotifierItem D-Bus interface"
)


def _read_status_label(sock_path: Path) -> str:
    """Read the status_label text from the tray app via bridge."""
    from qt_ai_dev_tools.bridge._client import eval_code

    resp = eval_code(sock_path, "widgets['status_label'].text()")
    assert resp.ok is True
    return resp.result or ""


class TestTrayListAndClick:
    """Flow 3A: Restore window from tray click."""

    @_skip_no_sni
    def test_list_tray_items(self, tray_app: subprocess.Popen[str]) -> None:
        """Verify the tray app appears in the SNI tray item list."""
        from qt_ai_dev_tools.subsystems import tray

        items = tray.list_items()
        # The tray app should have registered an SNI item
        assert len(items) > 0, "No tray items found — SNI watcher may not be running"

    @_skip_no_sni
    def test_tray_click_restores_window(self, tray_app: subprocess.Popen[str]) -> None:
        """Close/hide window, verify tray item exists, click to restore."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket
        from qt_ai_dev_tools.subsystems import tray

        sock = find_bridge_socket(pid=tray_app.pid)
        assert sock is not None, "No bridge socket found"

        # Hide the main window (simulate minimize to tray)
        eval_code(sock, "widgets['TrayTestWindow'].hide()")
        time.sleep(0.5)

        # Verify tray items exist
        items = tray.list_items()
        assert len(items) > 0, "No tray items found after hiding window"

        # Click the tray item to restore — try matching any available item
        # The bus name or item name should partially match
        tray_item = items[0]
        tray.click(tray_item.name)
        time.sleep(0.5)

        # Verify the window is visible again
        resp = eval_code(sock, "widgets['TrayTestWindow'].isVisible()")
        assert resp.ok is True
        assert resp.result == "True"


class TestTrayContextMenu:
    """Flow 3B: Tray context menu interaction."""

    @_skip_no_sni
    def test_tray_menu_entries(self, tray_app: subprocess.Popen[str]) -> None:
        """Read the tray context menu and verify expected entries."""
        from qt_ai_dev_tools.subsystems import tray

        items = tray.list_items()
        assert len(items) > 0, "No tray items found"

        tray_item = items[0]
        entries = tray.menu(tray_item.name)
        labels = [e.label for e in entries]

        # The tray app defines Show, Settings, Quit menu entries
        assert any("Show" in label or "show" in label.lower() for label in labels), (
            f"Expected 'Show' in menu entries, got: {labels}"
        )

    @_skip_no_sni
    def test_tray_select_settings(self, tray_app: subprocess.Popen[str]) -> None:
        """Select 'Settings' from tray menu, verify app reacts."""
        from qt_ai_dev_tools.bridge._client import find_bridge_socket
        from qt_ai_dev_tools.subsystems import tray

        sock = find_bridge_socket(pid=tray_app.pid)
        assert sock is not None, "No bridge socket found"

        items = tray.list_items()
        assert len(items) > 0
        tray_item = items[0]

        tray.select(tray_item.name, "Settings")
        time.sleep(0.5)

        # Verify status label changed (app sets "Settings opened")
        status = _read_status_label(sock)
        assert "settings" in status.lower() or "Settings" in status


class TestNotificationCapture:
    """Flow 3C: Send notification from app, capture via dbus-monitor."""

    @pytest.mark.xfail(
        reason="Qt QSystemTrayIcon.showMessage() may not emit standard D-Bus Notify — "
        "depends on notification daemon and Qt backend; works with notify-send but not always with Qt",
        strict=False,
    )
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
