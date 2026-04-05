"""System tray interaction via D-Bus StatusNotifierItem (SNI).

Left-click uses D-Bus Activate (fast, reliable).
Right-click uses xdotool on stalonetray/snixembed to open context menus.
Menu item selection uses D-Bus dbusmenu Event with correct item IDs.
"""

from __future__ import annotations

import logging
import re

from qt_ai_dev_tools.subsystems._subprocess import check_tool, run_tool
from qt_ai_dev_tools.subsystems.models import TrayItem, TrayMenuEntry

# D-Bus interface for the SNI watcher
_SNI_WATCHER_DEST = "org.kde.StatusNotifierWatcher"
_SNI_WATCHER_PATH = "/StatusNotifierWatcher"
_SNI_WATCHER_IFACE = "org.freedesktop.DBus.Properties"

# D-Bus interface for SNI items
_SNI_ITEM_IFACE = "org.kde.StatusNotifierItem"

logger = logging.getLogger(__name__)


def _query_sni_property(bus_name: str, object_path: str, prop: str) -> str | None:
    """Query a single property from an SNI item via busctl.

    Args:
        bus_name: D-Bus connection name (e.g. ":1.340").
        object_path: Object path (e.g. "/StatusNotifierItem").
        prop: Property name (e.g. "Id", "Menu").

    Returns:
        The property value as a string, or None if the query fails.
    """
    try:
        output = run_tool(
            [
                "busctl",
                "--user",
                "get-property",
                "--",
                bus_name,
                object_path,
                _SNI_ITEM_IFACE,
                prop,
            ]
        )
    except RuntimeError:
        return None
    # busctl output for string: s "value"
    # busctl output for object path: o "/MenuBar"
    m = re.search(r'[so]\s+"([^"]*)"', output)
    if m:
        return m.group(1)
    return None


def _resolve_menu_path(item: TrayItem) -> str:
    """Resolve the DBusMenu object path for a tray item.

    Queries the SNI item's Menu property first. Falls back to
    object_path + "/Menu" if the property is not available.

    Args:
        item: The tray item to resolve the menu path for.

    Returns:
        The D-Bus object path for the item's menu.
    """
    menu_prop = _query_sni_property(item.bus_name, item.object_path, "Menu")
    if menu_prop and menu_prop.startswith("/"):
        return menu_prop

    # Fallback: append /Menu to the object path
    fallback = item.object_path + "/Menu"
    if not fallback.startswith("/"):
        fallback = "/" + fallback
    return fallback


def _xdotool_env() -> dict[str, str]:
    """Environment with DISPLAY set for xdotool."""
    import os

    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    return env


def _find_stalonetray_wid() -> str:
    """Find the stalonetray X window ID via xdotool.

    Returns:
        The X window ID as a string.

    Raises:
        RuntimeError: If stalonetray is not running or xdotool is not found.
    """
    check_tool("xdotool")
    output = run_tool(
        ["xdotool", "search", "--class", "stalonetray"],
        env=_xdotool_env(),
    )
    wid = output.strip().splitlines()[0] if output.strip() else ""
    if not wid:
        msg = "stalonetray window not found — is stalonetray running?"
        raise RuntimeError(msg)
    return wid


def _find_icon_center(stalone_wid: str, app_name: str) -> tuple[int, int]:
    """Find the screen coordinates of a tray icon for a given app.

    Parses xwininfo -tree to find child windows with matching WM_CLASS.
    snixembed sets WM_CLASS to the SNI Id property value.

    Args:
        stalone_wid: X window ID of the stalonetray window.
        app_name: Application name to match in WM_CLASS.

    Returns:
        Absolute (x, y) center coordinates of the icon.

    Raises:
        LookupError: If no matching icon is found in stalonetray.
        RuntimeError: If xwininfo or xdotool is not found.
    """
    check_tool("xwininfo")
    check_tool("xdotool")

    # Get stalonetray absolute position
    geom_output = run_tool(
        ["xdotool", "getwindowgeometry", stalone_wid],
        env=_xdotool_env(),
    )
    # Output: "Window 12345\n  Position: 1872,0 (screen: 0)\n  Geometry: 48x24"
    pos_match = re.search(r"Position:\s+(\d+),(\d+)", geom_output)
    if not pos_match:
        msg = f"Could not parse stalonetray position from: {geom_output}"
        raise RuntimeError(msg)
    stalone_x = int(pos_match.group(1))
    stalone_y = int(pos_match.group(2))

    # Parse xwininfo tree to find child with matching WM_CLASS
    tree_output = run_tool(
        ["xwininfo", "-tree", "-id", stalone_wid],
        env=_xdotool_env(),
    )

    # Lines look like (two formats — named or unnamed windows):
    #   0x80000b "snixembed": ("tray_app.py" "tray_app.py")  24x24+0+0  +0+0
    #   0x3400003 (has no name): ("tray_app.py" "tray_app.py")  24x24+0+0  +1896+0
    # Match WM_CLASS in parentheses, then geometry with absolute +X+Y at end
    icon_pattern = re.compile(
        r"0x[0-9a-f]+\s+(?:\"[^\"]*\"|[^:]+):\s+"
        r'\("([^"]+)"\s+"[^"]+"\)\s+'
        r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\s+\+(-?\d+)\+(-?\d+)"
    )

    for m in icon_pattern.finditer(tree_output):
        wm_class = m.group(1)
        if app_name.lower() in wm_class.lower():
            # Use absolute coordinates from xwininfo (the last +X+Y)
            abs_x = int(m.group(6))
            abs_y = int(m.group(7))
            icon_w = int(m.group(2))
            icon_h = int(m.group(3))
            cx = abs_x + icon_w // 2
            cy = abs_y + icon_h // 2
            return (cx, cy)

    # Fallback: try matching with relative offset if absolute coords not found
    rel_pattern = re.compile(
        r"0x[0-9a-f]+\s+(?:\"[^\"]*\"|[^:]+):\s+"
        r'\("([^"]+)"\s+"[^"]+"\)\s+'
        r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)"
    )
    for m in rel_pattern.finditer(tree_output):
        wm_class = m.group(1)
        if app_name.lower() in wm_class.lower():
            icon_w = int(m.group(2))
            icon_h = int(m.group(3))
            offset_x = int(m.group(4))
            offset_y = int(m.group(5))
            cx = stalone_x + offset_x + icon_w // 2
            cy = stalone_y + offset_y + icon_h // 2
            return (cx, cy)

    msg = f"Tray icon for '{app_name}' not found in stalonetray. xwininfo output:\n{tree_output}"
    raise LookupError(msg)


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
    except RuntimeError as exc:
        if "ServiceUnknown" in str(exc) or "not found" in str(exc):
            logger.warning(
                "StatusNotifierWatcher D-Bus service not available — install an SNI host (KDE/GNOME or snixembed)"
            )
            return []
        raise
    return _parse_registered_items(output)


def _parse_registered_items(output: str) -> list[TrayItem]:
    """Parse busctl output for RegisteredStatusNotifierItems.

    The output format is:
        as N "bus_name/obj_path" "bus_name2/obj_path2" ...

    For connection IDs (e.g. ":1.340"), queries the SNI item's Id
    property to get the real application name.

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

        # If the name is just a number (connection ID like :1.340 -> "340"),
        # query the SNI item's Id property to get the real app name
        if name.isdigit():
            sni_id = _query_sni_property(bus_name, obj_path, "Id")
            if sni_id:
                name = sni_id

        items.append(
            TrayItem(
                name=name,
                bus_name=bus_name,
                object_path=obj_path,
                protocol="SNI",
            )
        )
    return items


def click(app_name: str, button: str = "left") -> None:
    """Click a tray item by application name.

    Args:
        app_name: Name substring to match against tray items.
        button: "left" for D-Bus Activate, "right" to open context menu
                via xdotool right-click on stalonetray icon.

    Raises:
        LookupError: If no matching tray item is found.
        RuntimeError: If required tools are not found or calls fail.
        ValueError: If button is not "left" or "right".
    """
    if button == "left":
        item = _find_item(app_name)
        check_tool("busctl")
        run_tool(
            [
                "busctl",
                "--user",
                "call",
                "--",
                item.bus_name,
                item.object_path,
                _SNI_ITEM_IFACE,
                "Activate",
                "ii",
                "0",
                "0",
            ]
        )
    elif button == "right":
        stalone_wid = _find_stalonetray_wid()
        cx, cy = _find_icon_center(stalone_wid, app_name)
        check_tool("xdotool")
        env = _xdotool_env()
        run_tool(
            ["xdotool", "mousemove", "--screen", "0", str(cx), str(cy)],
            env=env,
        )
        run_tool(["xdotool", "click", "3"], env=env)
    else:
        msg = f"Invalid button '{button}', must be 'left' or 'right'"
        raise ValueError(msg)


def menu(app_name: str) -> list[TrayMenuEntry]:
    """Get the context menu entries for a tray item.

    Calls the DBusMenu interface to retrieve menu items.
    Resolves the menu path from the SNI item's Menu property,
    falling back to object_path + "/Menu" and then object_path.

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

    menu_path = _resolve_menu_path(item)

    try:
        output = run_tool(
            [
                "busctl",
                "--user",
                "call",
                "--",
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
        # Some apps use the item's own object path for the menu
        output = run_tool(
            [
                "busctl",
                "--user",
                "call",
                "--",
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

    The output is complex nested data. Each menu item appears as:
        ``(ia{sv}av) <dbus_id> <num_props> "key" <type> <value> ...``

    We extract the D-Bus item ID, label, and enabled flag from each item.

    Args:
        output: Raw busctl output from GetLayout call.

    Returns:
        List of TrayMenuEntry objects with correct D-Bus IDs.
    """
    entries: list[TrayMenuEntry] = []

    # Match each menu item block: (ia{sv}av) <id> <nprops> ...
    # Extract everything from the item marker to the next item marker (or end)
    item_pattern = re.compile(r"\(ia\{sv\}av\)\s+(\d+)\s+(\d+)\s+(.*?)(?=\(ia\{sv\}av\)|$)", re.DOTALL)
    label_pattern = re.compile(r'"label"\s+[sv]\s+"([^"]*)"')
    enabled_pattern = re.compile(r'"enabled"\s+[bsv]\s+(\w+)')

    entry_index = 0
    for m in item_pattern.finditer(output):
        dbus_id = int(m.group(1))
        props_text = m.group(3)

        # Extract label
        label_match = label_pattern.search(props_text)
        if not label_match:
            continue
        label = label_match.group(1)
        if not label or label.startswith("_"):
            continue

        # Extract enabled flag
        enabled = True
        enabled_match = enabled_pattern.search(props_text)
        if enabled_match and enabled_match.group(1).lower() == "false":
            enabled = False

        entries.append(TrayMenuEntry(label=label, enabled=enabled, index=entry_index, dbus_id=dbus_id))
        entry_index += 1

    return entries


def select(app_name: str, item_label: str) -> None:
    """Select a context menu item from a tray icon.

    Finds the menu item by label via D-Bus GetLayout, then triggers it
    using a D-Bus dbusmenu Event call with the correct item ID.

    Args:
        app_name: Name substring to match against tray items.
        item_label: Label of the menu item to click.

    Raises:
        LookupError: If no matching tray icon or menu item is found.
        RuntimeError: If required tools are not found or the D-Bus call fails.
    """
    item = _find_item(app_name)
    entries = menu(app_name)

    # Find the entry with matching label
    target: TrayMenuEntry | None = None
    for entry in entries:
        if item_label.lower() in entry.label.lower():
            target = entry
            break
    if target is None:
        available = [e.label for e in entries]
        msg = f"Menu item '{item_label}' not found. Available: {available}"
        raise LookupError(msg)

    if target.dbus_id < 0:
        msg = f"Menu item '{item_label}' has no valid D-Bus ID (parsing failed)"
        raise RuntimeError(msg)

    # Trigger the menu item via D-Bus dbusmenu Event
    menu_path = _resolve_menu_path(item)
    check_tool("busctl")
    try:
        run_tool(
            [
                "busctl",
                "--user",
                "call",
                "--",
                item.bus_name,
                menu_path,
                "com.canonical.dbusmenu",
                "Event",
                "isvu",
                str(target.dbus_id),
                "clicked",
                "s",
                "",
                "0",
            ]
        )
    except RuntimeError:
        # Fallback: try the item's own object path
        run_tool(
            [
                "busctl",
                "--user",
                "call",
                "--",
                item.bus_name,
                item.object_path,
                "com.canonical.dbusmenu",
                "Event",
                "isvu",
                str(target.dbus_id),
                "clicked",
                "s",
                "",
                "0",
            ]
        )


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
