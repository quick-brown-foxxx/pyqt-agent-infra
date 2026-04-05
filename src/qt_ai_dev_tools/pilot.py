"""QtPilot — main class for AT-SPI based Qt app interaction."""

from __future__ import annotations

import logging
import time

from qt_ai_dev_tools import interact, state
from qt_ai_dev_tools._atspi import AtspiNode
from qt_ai_dev_tools.models import Extents
from qt_ai_dev_tools.screenshot import take_screenshot

logger = logging.getLogger(__name__)


class QtPilot:
    """Connect to a running Qt app via AT-SPI and interact with it.

    Usage:
        pilot = QtPilot()                     # finds the first Qt app
        pilot = QtPilot(app_name="main.py")   # by name substring

        pilot.dump_tree()
        btn = pilot.find_one(role="push button", name="Save")
        pilot.click(btn)
        pilot.type_text("hello")
    """

    def __init__(self, app_name: str | None = None, retries: int = 5, delay: float = 1.0) -> None:
        self.app: AtspiNode | None = None
        for _ in range(retries):
            desktop = AtspiNode.desktop(0)
            for child in desktop.children:
                if app_name is None or app_name in child.name:
                    self.app = child
                    break
            if self.app:
                break
            time.sleep(delay)

        if not self.app:
            desktop = AtspiNode.desktop(0)
            apps = [child.name for child in desktop.children]
            msg = f"App '{app_name}' not found on AT-SPI bus. Visible apps: {apps}"
            raise RuntimeError(msg)

    # ── Tree inspection ──────────────────────────────────────────

    def find(
        self,
        role: str | None = None,
        name: str | None = None,
        root: AtspiNode | None = None,
    ) -> list[AtspiNode]:
        """Find all widgets matching role and/or name (substring match)."""
        root = root or self.app
        if root is None:
            msg = "No app connected"
            raise RuntimeError(msg)
        results: list[AtspiNode] = []
        self._walk(root, role, name, results)
        return results

    def find_one(
        self,
        role: str | None = None,
        name: str | None = None,
        root: AtspiNode | None = None,
    ) -> AtspiNode:
        """Find exactly one widget. Raises if 0 or >1 found."""
        found = self.find(role, name, root)
        if len(found) == 0:
            msg = f"No widget found: role={role}, name={name}"
            raise LookupError(msg)
        if len(found) > 1:
            descs = [f'[{w.role_name}] "{w.name}"' for w in found]
            msg = f"Multiple widgets found for role={role}, name={name}: {descs}"
            raise LookupError(msg)
        return found[0]

    def dump_tree(
        self,
        root: AtspiNode | None = None,
        indent: int = 0,
        max_depth: int = 8,
    ) -> str:
        """Return a text dump of the widget tree."""
        root = root or self.app
        if root is None:
            msg = "No app connected"
            raise RuntimeError(msg)
        lines: list[str] = []
        self._dump(root, indent, max_depth, lines)
        return "\n".join(lines)

    def get_children(self, widget: AtspiNode) -> list[AtspiNode]:
        """Get direct children of a widget."""
        return widget.children

    # ── Interaction ──────────────────────────────────────────────

    def click(self, widget: AtspiNode, pause: float = 0.2) -> None:
        """Click the center of a widget using xdotool."""
        interact.click(widget, pause)

    def type_text(self, text: str, delay_ms: int = 20, pause: float = 0.2) -> None:
        """Type text via xdotool into the currently focused widget."""
        interact.type_text(text, delay_ms, pause)

    def press_key(self, key: str, pause: float = 0.1) -> None:
        """Press a key via xdotool (e.g. 'Return', 'Tab', 'ctrl+a')."""
        interact.press_key(key, pause)

    def action(self, widget: AtspiNode, action_name: str = "Press", pause: float = 0.3) -> None:
        """Invoke an AT-SPI action by name (e.g. 'Press', 'SetFocus')."""
        interact.action(widget, action_name, pause)

    def focus(self, widget: AtspiNode, pause: float = 0.2) -> None:
        """Focus a widget via AT-SPI SetFocus, falling back to click."""
        interact.focus(widget, pause)

    # ── State ────────────────────────────────────────────────────

    def get_name(self, widget: AtspiNode) -> str:
        """Get the accessible name of a widget."""
        return state.get_name(widget)

    def get_role(self, widget: AtspiNode) -> str:
        """Get the role name of a widget."""
        return state.get_role(widget)

    def get_extents(self, widget: AtspiNode) -> Extents:
        """Get screen position and size of a widget."""
        return state.get_extents(widget)

    def get_text(self, widget: AtspiNode) -> str:
        """Get text content from a widget."""
        return state.get_text(widget)

    # ── Compound actions ─────────────────────────────────────────

    def fill(
        self,
        role: str = "text",
        name: str | None = None,
        value: str = "",
        clear_first: bool = True,
    ) -> None:
        """Focus a text widget, optionally clear it, and type a value.

        This is a compound action: focus -> clear -> type.
        """
        widget = self.find_one(role=role, name=name)
        self.focus(widget)
        if clear_first:
            interact.press_key("ctrl+a")
            interact.press_key("Delete")
        self.type_text(value)

    def select_combo_item(
        self,
        item_text: str,
        role: str = "combo box",
        name: str | None = None,
    ) -> None:
        """Select an item in a combo box by keyboard navigation.

        Qt's AT-SPI Selection interface does not work for QComboBox
        (select_child returns False), and clicking popup items is
        unreliable because the popup overlaps the combo box.

        Instead, this method:
        1. Reads the item list from the combo's AT-SPI children
        2. Clicks the combo to open its popup
        3. Navigates to the target item using arrow keys
        4. Presses Enter to confirm the selection

        Raises:
            LookupError: If no item matches item_text.
        """
        combo = self.find_one(role=role, name=name)

        # AT-SPI tree: [combo box] -> [list] -> [list item]*
        items: list[AtspiNode] = []
        for child in combo.children:
            if child.role_name == "list":
                items = child.children
                break

        if not items:
            items = combo.children

        item_names = [it.name for it in items]

        # Find the target index
        target_index = -1
        for i, it in enumerate(items):
            if it.name == item_text:
                target_index = i
                break

        if target_index < 0:
            msg = f"Item {item_text!r} not found in combo box. Available: {item_names}"
            raise LookupError(msg)

        # Find the currently selected index
        current_index = -1
        current_name = combo.name  # combo's accessible name = current selection
        for i, it in enumerate(items):
            if it.name == current_name:
                current_index = i
                break

        logger.debug(
            "select_combo_item: target=%r (idx=%d), current=%r (idx=%d), items=%r",
            item_text,
            target_index,
            current_name,
            current_index,
            item_names,
        )

        # Click to open the popup (popup opens with current item highlighted)
        self.click(combo, pause=0.3)

        # Navigate from current to target using arrow keys
        if current_index >= 0:
            diff = target_index - current_index
            key = "Down" if diff > 0 else "Up"
            for _ in range(abs(diff)):
                self.press_key(key, pause=0.05)
        else:
            # Unknown current position: go to top, then navigate down
            for _ in range(len(items)):
                self.press_key("Up", pause=0.02)
            for _ in range(target_index):
                self.press_key("Down", pause=0.05)

        # Confirm selection
        self.press_key("Return", pause=0.2)

    def switch_tab(
        self,
        tab_text: str,
        role: str = "page tab list",
        name: str | None = None,
    ) -> None:
        """Switch to a tab by substring match on tab name.

        Finds the tab list, iterates its children, and selects the first
        tab whose name contains tab_text.

        Raises:
            LookupError: If no tab name contains tab_text.
        """
        tab_list = self.find_one(role=role, name=name)
        for i, child in enumerate(tab_list.children):
            if tab_text in child.name:
                tab_list.select_child(i)
                return
        available = [c.name for c in tab_list.children]
        msg = f"Tab {tab_text!r} not found. Available: {available}"
        raise LookupError(msg)

    def get_table_cell(
        self,
        row: int,
        col: int,
        role: str = "table",
        name: str | None = None,
    ) -> str:
        """Get text content of a table cell.

        Raises:
            LookupError: If the cell at (row, col) does not exist.
        """
        table = self.find_one(role=role, name=name)
        cell = table.get_cell_at(row, col)
        if cell is None:
            msg = f"No cell at ({row}, {col}) in table"
            raise LookupError(msg)
        return cell.get_text()

    def get_table_size(
        self,
        role: str = "table",
        name: str | None = None,
    ) -> tuple[int, int]:
        """Get (rows, columns) of a table."""
        table = self.find_one(role=role, name=name)
        return (table.get_n_rows(), table.get_n_columns())

    def check_checkbox(
        self,
        checked: bool = True,
        role: str = "check box",
        name: str | None = None,
    ) -> None:
        """Toggle a checkbox via AT-SPI action.

        Tries the 'Toggle' action first, falls back to 'Press'.

        Args:
            checked: Unused — AT-SPI only supports toggling, not setting
                     a specific state. Kept for API symmetry.
            role: Widget role to search for.
            name: Widget name substring to match.
        """
        _ = checked  # AT-SPI only supports toggle, not set-to-state
        widget = self.find_one(role=role, name=name)
        try:
            widget.do_action("Toggle")
        except LookupError:
            widget.do_action("Press")

    def set_slider_value(
        self,
        value: float,
        role: str = "slider",
        name: str | None = None,
    ) -> None:
        """Set a slider (or spinner) to a specific value via the Value interface."""
        widget = self.find_one(role=role, name=name)
        widget.set_value(value)

    def get_widget_value(
        self,
        role: str | None = None,
        name: str | None = None,
    ) -> float | None:
        """Get the numeric value of a widget via the Value interface.

        Returns None if the widget has no Value interface.
        """
        widget = self.find_one(role=role, name=name)
        return widget.get_value()

    def select_menu_item(self, *path: str, pause: float = 0.3) -> None:
        """Navigate a menu hierarchy by clicking each level.

        Each string in path is a menu item name. The method finds and clicks
        widgets matching that name in sequence, pausing between each click
        for the submenu to appear.

        Raises:
            LookupError: If any item in the path is not found.
        """
        for menu_text in path:
            found = self.find(name=menu_text)
            if not found:
                msg = f"Menu item {menu_text!r} not found"
                raise LookupError(msg)
            self.click(found[0], pause=pause)

    # ── Screenshots ──────────────────────────────────────────────

    def screenshot(self, path: str = "/tmp/screenshot.png") -> str:  # noqa: S108
        """Take a screenshot of the Xvfb display."""
        return take_screenshot(path)

    # ── Private ──────────────────────────────────────────────────

    def _walk(
        self,
        node: AtspiNode,
        role: str | None,
        name: str | None,
        results: list[AtspiNode],
    ) -> None:
        for i in range(node.child_count):
            c = node.child_at(i)
            if c is None:
                continue
            match = True
            if role and c.role_name != role:
                match = False
            if name and name not in c.name:
                match = False
            if match:
                results.append(c)
            self._walk(c, role, name, results)

    def _dump(
        self,
        node: AtspiNode,
        indent: int,
        max_depth: int,
        lines: list[str],
    ) -> None:
        if indent > max_depth:
            return
        widget_name = node.name
        role = node.role_name
        try:
            ext = node.get_extents()
            pos = f" @({ext.x},{ext.y} {ext.width}x{ext.height})"
        except Exception:
            pos = ""
        lines.append(f'{"  " * indent}[{role}] "{widget_name}"{pos}')
        for i in range(node.child_count):
            c = node.child_at(i)
            if c:
                self._dump(c, indent + 1, max_depth, lines)
