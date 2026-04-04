"""QtPilot — main class for AT-SPI based Qt app interaction."""

from __future__ import annotations

import time

from qt_ai_dev_tools import interact, state
from qt_ai_dev_tools._atspi import AtspiNode
from qt_ai_dev_tools.models import Extents
from qt_ai_dev_tools.screenshot import take_screenshot


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
            descs = [
                f'[{w.role_name}] "{w.name}"'
                for w in found
            ]
            msg = f"Multiple widgets found for role={role}, name={name}: {descs}"
            raise LookupError(msg)
        return found[0]

    def dump_tree(
        self,
        root: AtspiNode | None = None,
        indent: int = 0,
        max_depth: int = 8,
    ) -> str:
        """Return and print a text dump of the widget tree."""
        root = root or self.app
        if root is None:
            msg = "No app connected"
            raise RuntimeError(msg)
        lines: list[str] = []
        self._dump(root, indent, max_depth, lines)
        text = "\n".join(lines)
        print(text)
        return text

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
