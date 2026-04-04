"""Tests for notification subsystem."""

from __future__ import annotations

from unittest.mock import patch

import pytest

_MOCK_DBUS_MONITOR_OUTPUT = """signal time=1234 sender=:1.1 -> destination=(null) serial=1
method call time=1234 sender=:1.2 -> destination=:1.1 serial=2 member=Notify
   string "test-app"
   uint32 0
   string "dialog-information"
   string "Test Summary"
   string "Test body text"
   array [
      string "default"
      string "OK"
      string "reply"
      string "Reply"
   ]
   array [
   ]
   int32 5000
"""


class TestParseNotifications:
    def test_parse_single_notification(self) -> None:
        """_parse_notifications should extract app name, summary, body, and actions."""
        from qt_ai_dev_tools.subsystems.notify import _parse_notifications

        notifications = _parse_notifications(_MOCK_DBUS_MONITOR_OUTPUT)
        assert len(notifications) == 1

        notif = notifications[0]
        assert notif.app_name == "test-app"
        assert notif.summary == "Test Summary"
        assert notif.body == "Test body text"
        assert notif.id == 0

    def test_parse_notification_actions(self) -> None:
        """_parse_notifications should extract action key/label pairs."""
        from qt_ai_dev_tools.subsystems.notify import _parse_notifications

        notifications = _parse_notifications(_MOCK_DBUS_MONITOR_OUTPUT)
        notif = notifications[0]

        assert len(notif.actions) == 2
        assert notif.actions[0].key == "default"
        assert notif.actions[0].label == "OK"
        assert notif.actions[1].key == "reply"
        assert notif.actions[1].label == "Reply"

    def test_parse_empty_output(self) -> None:
        """_parse_notifications should return empty list for no notifications."""
        from qt_ai_dev_tools.subsystems.notify import _parse_notifications

        notifications = _parse_notifications("")
        assert notifications == []

    def test_parse_multiple_notifications(self) -> None:
        """_parse_notifications should handle multiple Notify calls."""
        from qt_ai_dev_tools.subsystems.notify import _parse_notifications

        output = (
            _MOCK_DBUS_MONITOR_OUTPUT
            + "\nmethod call time=5678 sender=:1.3 -> destination=:1.1 serial=3 member=Notify\n"
            '   string "other-app"\n'
            "   uint32 42\n"
            '   string "icon"\n'
            '   string "Second"\n'
            '   string "Second body"\n'
        )
        notifications = _parse_notifications(output)
        assert len(notifications) == 2
        assert notifications[1].app_name == "other-app"
        assert notifications[1].summary == "Second"
        assert notifications[1].id == 42


class TestDismiss:
    def test_dismiss_calls_busctl(self) -> None:
        """dismiss() should call busctl CloseNotification with the ID."""
        from qt_ai_dev_tools.subsystems.notify import dismiss

        with (
            patch("qt_ai_dev_tools.subsystems.notify.check_tool"),
            patch("qt_ai_dev_tools.subsystems.notify.run_tool") as mock_run,
        ):
            dismiss(42)

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "CloseNotification" in args
            assert "42" in args

    def test_dismiss_raises_on_missing_tool(self) -> None:
        """dismiss() should raise RuntimeError when busctl is not installed."""
        from qt_ai_dev_tools.subsystems.notify import dismiss

        with (
            patch("qt_ai_dev_tools.subsystems.notify.check_tool", side_effect=RuntimeError("not found")),
            pytest.raises(RuntimeError, match="not found"),
        ):
            dismiss(1)


class TestAction:
    def test_action_calls_busctl_emit(self) -> None:
        """action() should call busctl emit ActionInvoked with ID and key."""
        from qt_ai_dev_tools.subsystems.notify import action

        with (
            patch("qt_ai_dev_tools.subsystems.notify.check_tool"),
            patch("qt_ai_dev_tools.subsystems.notify.run_tool") as mock_run,
        ):
            action(42, "reply")

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "ActionInvoked" in args
            assert "42" in args
            assert "reply" in args


class TestListen:
    def test_listen_calls_dbus_monitor(self) -> None:
        """listen() should check for dbus-monitor tool."""
        from qt_ai_dev_tools.subsystems.notify import listen

        with (
            patch("qt_ai_dev_tools.subsystems.notify.check_tool") as mock_check,
            patch("subprocess.run", side_effect=_make_timeout_expired("")),
        ):
            mock_check.return_value = "/usr/bin/dbus-monitor"
            result = listen(timeout=0.1)

            mock_check.assert_called_once_with("dbus-monitor")
            assert isinstance(result, list)


def _make_timeout_expired(output: str) -> type[BaseException]:
    """Create a TimeoutExpired exception class with stdout."""
    import subprocess

    class FakeTimeout(subprocess.TimeoutExpired):
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            super().__init__(cmd="dbus-monitor", timeout=0.1)
            self.stdout = output

    return FakeTimeout
