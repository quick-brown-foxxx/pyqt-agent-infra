"""Desktop notification interaction via D-Bus."""

from __future__ import annotations

import re
import subprocess

from qt_ai_dev_tools.subsystems._subprocess import check_tool, run_tool
from qt_ai_dev_tools.subsystems.models import Notification, NotificationAction

# D-Bus destination for notification daemon
_NOTIFY_DEST = "org.freedesktop.Notifications"
_NOTIFY_PATH = "/org/freedesktop/Notifications"
_NOTIFY_IFACE = "org.freedesktop.Notifications"


def listen(timeout: float = 5.0) -> list[Notification]:
    """Listen for desktop notifications via dbus-monitor.

    Monitors the org.freedesktop.Notifications interface for Notify
    method calls and returns captured notifications.

    Args:
        timeout: Seconds to listen before returning (default 5.0).

    Returns:
        List of captured Notification objects.

    Raises:
        RuntimeError: If dbus-monitor is not found.
    """
    check_tool("dbus-monitor")
    try:
        result = subprocess.run(
            [
                "dbus-monitor",
                "--session",
                f"interface={_NOTIFY_IFACE},member=Notify",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
    except subprocess.TimeoutExpired as exc:
        # Expected: dbus-monitor runs until killed/timeout
        output = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")

    return _parse_notifications(output)


def _parse_notifications(output: str) -> list[Notification]:
    """Parse dbus-monitor output for Notify method calls.

    The Notify method signature is:
        Notify(app_name, replaces_id, icon, summary, body, actions, hints, timeout)

    Args:
        output: Raw dbus-monitor output.

    Returns:
        Parsed list of Notification objects.
    """
    notifications: list[Notification] = []

    # Split on method call boundaries
    blocks = re.split(r"method call.*?member=Notify", output)

    for block in blocks[1:]:  # skip text before first Notify
        strings: list[str] = [m.group(1) for m in re.finditer(r'string "([^"]*)"', block)]
        uint32s: list[str] = [m.group(1) for m in re.finditer(r"uint32 (\d+)", block)]

        if len(strings) < 3:
            continue

        app_name = strings[0]
        summary = strings[2] if len(strings) > 2 else ""
        body = strings[3] if len(strings) > 3 else ""

        notification_id = int(uint32s[0]) if uint32s else 0

        # Parse actions (pairs of key, label strings after body)
        action_strings = strings[4:] if len(strings) > 4 else []
        actions: list[NotificationAction] = [
            NotificationAction(key=action_strings[i], label=action_strings[i + 1])
            for i in range(0, len(action_strings) - 1, 2)
        ]

        notifications.append(
            Notification(
                id=notification_id,
                app_name=app_name,
                summary=summary,
                body=body,
                actions=actions,
            )
        )

    return notifications


def dismiss(notification_id: int) -> None:
    """Close a notification by its ID.

    Args:
        notification_id: The notification ID to dismiss.

    Raises:
        RuntimeError: If busctl is not found or the D-Bus call fails.
    """
    check_tool("busctl")
    run_tool(
        [
            "busctl",
            "--user",
            "call",
            _NOTIFY_DEST,
            _NOTIFY_PATH,
            _NOTIFY_IFACE,
            "CloseNotification",
            "u",
            str(notification_id),
        ]
    )


def action(notification_id: int, action_key: str) -> None:
    """Invoke an action on a notification.

    Emits the ActionInvoked signal for the notification daemon to handle.

    Args:
        notification_id: The notification ID.
        action_key: The action key string (e.g. "default", "reply").

    Raises:
        RuntimeError: If busctl is not found or the D-Bus call fails.
    """
    check_tool("busctl")
    run_tool(
        [
            "busctl",
            "--user",
            "emit",
            _NOTIFY_PATH,
            _NOTIFY_IFACE,
            "ActionInvoked",
            "us",
            str(notification_id),
            action_key,
        ]
    )
