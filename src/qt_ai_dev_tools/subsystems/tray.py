"""System tray interaction via D-Bus StatusNotifierItem (SNI)."""

from __future__ import annotations

import re
import sys

from qt_ai_dev_tools.subsystems._subprocess import check_tool, run_tool
from qt_ai_dev_tools.subsystems.models import TrayItem, TrayMenuEntry

# D-Bus interface for the SNI watcher
_SNI_WATCHER_DEST = "org.kde.StatusNotifierWatcher"
_SNI_WATCHER_PATH = "/StatusNotifierWatcher"
_SNI_WATCHER_IFACE = "org.freedesktop.DBus.Properties"

# D-Bus interface for SNI items
_SNI_ITEM_IFACE = "org.kde.StatusNotifierItem"


def list_items() -> list[TrayItem]:
    """Query the StatusNotifierWatcher for registered tray items.

    Uses busctl to read the RegisteredStatusNotifierItems property
    from the SNI watcher service.

    Returns:
        List of TrayItem objects for each registered tray icon.
        Returns an empty list with a warning if StatusNotifierWatcher
        is not available (no SNI host running).

    Raises:
        RuntimeError: If busctl is not found.
    """
    check_tool("busctl")
    try:
        output = run_tool(
            [
                "busctl",
                "--user",
                "get-property",
                _SNI_WATCHER_DEST,
                _SNI_WATCHER_PATH,
                "org.kde.StatusNotifierWatcher",
                "RegisteredStatusNotifierItems",
            ]
        )
    except RuntimeError:
        print(
            "Warning: StatusNotifierWatcher D-Bus service not available. "
            "Install an SNI host (e.g. stalonetray, snixembed) to enable tray support.",
            file=sys.stderr,
        )
        return []
    return _parse_registered_items(output)


def _parse_registered_items(output: str) -> list[TrayItem]:
    """Parse busctl output for RegisteredStatusNotifierItems.

    The output format is:
        as N "bus_name/obj_path" "bus_name2/obj_path2" ...

    Args:
        output: Raw busctl output string.

    Returns:
        Parsed list of TrayItem objects.
    """
    items: list[TrayItem] = []
    # Match quoted strings like ":1.45/StatusNotifierItem" or "org.app/path"
    pattern = re.compile(r'"([^"]+)"')
    for m in pattern.finditer(output):
        value: str = m.group(1)
        # Split on first / to get bus_name and object_path
        if "/" in value:
            bus_name, raw_path = value.split("/", 1)
            obj_path = "/" + raw_path
        else:
            bus_name = value
            obj_path = "/StatusNotifierItem"

        # Extract a readable name from the bus name
        name = bus_name.split(".")[-1] if "." in bus_name else bus_name

        items.append(
            TrayItem(
                name=name,
                bus_name=bus_name,
                object_path=obj_path,
                protocol="SNI",
            )
        )
    return items


def click(app_name: str) -> None:
    """Activate (left-click) a tray item by application name.

    Searches registered SNI items for one matching app_name,
    then calls the Activate method on it.

    Args:
        app_name: Name substring to match against tray items.

    Raises:
        LookupError: If no matching tray item is found.
        RuntimeError: If busctl is not found or the D-Bus call fails.
    """
    item = _find_item(app_name)
    check_tool("busctl")
    run_tool(
        [
            "busctl",
            "--user",
            "call",
            item.bus_name,
            item.object_path,
            _SNI_ITEM_IFACE,
            "Activate",
            "ii",
            "0",
            "0",
        ]
    )


def menu(app_name: str) -> list[TrayMenuEntry]:
    """Get the context menu entries for a tray item.

    Calls the DBusMenu interface to retrieve menu items.

    Args:
        app_name: Name substring to match against tray items.

    Returns:
        List of TrayMenuEntry objects.

    Raises:
        LookupError: If no matching tray item is found.
        RuntimeError: If busctl is not found or the D-Bus call fails.
    """
    item = _find_item(app_name)
    check_tool("busctl")

    # DBusMenu is usually at object_path + "/Menu" or a Menu property
    menu_path = item.object_path + "/Menu"
    if not menu_path.startswith("/"):
        menu_path = "/" + menu_path

    try:
        output = run_tool(
            [
                "busctl",
                "--user",
                "call",
                item.bus_name,
                menu_path,
                "com.canonical.dbusmenu",
                "GetLayout",
                "iias",
                "0",  # parent ID
                "-1",  # recursion depth (-1 = all)
                "0",  # properties (empty array)
            ]
        )
    except RuntimeError:
        # Some apps use a different menu path
        output = run_tool(
            [
                "busctl",
                "--user",
                "call",
                item.bus_name,
                item.object_path,
                "com.canonical.dbusmenu",
                "GetLayout",
                "iias",
                "0",
                "-1",
                "0",
            ]
        )

    return _parse_menu_output(output)


def _parse_menu_output(output: str) -> list[TrayMenuEntry]:
    """Parse busctl GetLayout output into menu entries.

    The output is complex nested data; we extract label strings
    and create indexed entries.

    Args:
        output: Raw busctl output from GetLayout call.

    Returns:
        List of TrayMenuEntry objects.
    """
    entries: list[TrayMenuEntry] = []
    # Look for "label" followed by a quoted string
    label_pattern = re.compile(r'"label"\s+[sv]\s+"([^"]*)"')
    enabled_pattern = re.compile(r'"enabled"\s+[sv]\s+"?(\w+)"?')

    labels: list[str] = [m.group(1) for m in label_pattern.finditer(output)]
    enabled_flags: list[str] = [m.group(1) for m in enabled_pattern.finditer(output)]

    for i, label in enumerate(labels):
        if not label or label.startswith("_"):
            continue
        enabled = True
        if i < len(enabled_flags):
            enabled = enabled_flags[i].lower() != "false"
        entries.append(TrayMenuEntry(label=label, enabled=enabled, index=i))

    return entries


def select(app_name: str, item_label: str) -> None:
    """Open the context menu and click a menu item by label.

    Args:
        app_name: Name substring to match against tray items.
        item_label: Label of the menu item to click.

    Raises:
        LookupError: If no matching tray item or menu item is found.
        RuntimeError: If busctl is not found or the D-Bus call fails.
    """
    entries = menu(app_name)
    for entry in entries:
        if item_label.lower() in entry.label.lower():
            item = _find_item(app_name)
            menu_path = item.object_path + "/Menu"
            if not menu_path.startswith("/"):
                menu_path = "/" + menu_path

            try:
                run_tool(
                    [
                        "busctl",
                        "--user",
                        "call",
                        item.bus_name,
                        menu_path,
                        "com.canonical.dbusmenu",
                        "Event",
                        "isvu",
                        str(entry.index),
                        "clicked",
                        "s",
                        "",
                        "0",
                    ]
                )
            except RuntimeError:
                run_tool(
                    [
                        "busctl",
                        "--user",
                        "call",
                        item.bus_name,
                        item.object_path,
                        "com.canonical.dbusmenu",
                        "Event",
                        "isvu",
                        str(entry.index),
                        "clicked",
                        "s",
                        "",
                        "0",
                    ]
                )
            return

    available = [e.label for e in entries]
    msg = f"Menu item '{item_label}' not found. Available: {available}"
    raise LookupError(msg)


def _find_item(app_name: str) -> TrayItem:
    """Find a tray item matching the given application name.

    Args:
        app_name: Name substring to match.

    Returns:
        The matching TrayItem.

    Raises:
        LookupError: If no matching item is found.
    """
    items = list_items()
    for item in items:
        if app_name.lower() in item.name.lower() or app_name.lower() in item.bus_name.lower():
            return item

    available = [f"{item.name} ({item.bus_name})" for item in items]
    msg = f"No tray item matching '{app_name}'. Available: {available}"
    raise LookupError(msg)
