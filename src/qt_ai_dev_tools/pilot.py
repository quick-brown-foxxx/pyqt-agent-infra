"""QtPilot — main class for AT-SPI based Qt app interaction."""

from __future__ import annotations

import time

import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection

from qt_ai_dev_tools import interact, state
from qt_ai_dev_tools.models import Extents
from qt_ai_dev_tools.screenshot import take_screenshot

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # type: ignore[import-untyped]  # noqa: E402  # rationale: system AT-SPI bindings


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
        self.app: object | None = None
        for _ in range(retries):
            desktop = Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                candidate = desktop.get_child_at_index(i)
                if candidate is None:
                    continue
                if app_name is None or app_name in (candidate.get_name() or ""):
                    self.app = candidate
                    break
            if self.app:
                break
            time.sleep(delay)

        if not self.app:
            apps: list[str] = []
            desktop = Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                c = desktop.get_child_at_index(i)
                if c:
                    apps.append(c.get_name())
            msg = f"App '{app_name}' not found on AT-SPI bus. Visible apps: {apps}"
            raise RuntimeError(msg)

    # ── Tree inspection ──────────────────────────────────────────

    def find(
        self,
        role: str | None = None,
        name: str | None = None,
        root: object | None = None,
    ) -> list[object]:
        """Find all widgets matching role and/or name (substring match)."""
        root = root or self.app
        if root is None:
            msg = "No app connected"
            raise RuntimeError(msg)
        results: list[object] = []
        self._walk(root, role, name, results)
        return results

    def find_one(
        self,
        role: str | None = None,
        name: str | None = None,
        root: object | None = None,
    ) -> object:
        """Find exactly one widget. Raises if 0 or >1 found."""
        found = self.find(role, name, root)
        if len(found) == 0:
            msg = f"No widget found: role={role}, name={name}"
            raise LookupError(msg)
        if len(found) > 1:
            descs = [
                f'[{w.get_role_name()}] "{w.get_name()}"'  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
                for w in found
            ]
            msg = f"Multiple widgets found for role={role}, name={name}: {descs}"
            raise LookupError(msg)
        return found[0]

    def dump_tree(
        self,
        root: object | None = None,
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

    def get_children(self, widget: object) -> list[object]:
        """Get direct children of a widget."""
        return state.get_children(widget)

    # ── Interaction ──────────────────────────────────────────────

    def click(self, widget: object, pause: float = 0.2) -> None:
        """Click the center of a widget using xdotool."""
        interact.click(widget, pause)

    def type_text(self, text: str, delay_ms: int = 20, pause: float = 0.2) -> None:
        """Type text via xdotool into the currently focused widget."""
        interact.type_text(text, delay_ms, pause)

    def press_key(self, key: str, pause: float = 0.1) -> None:
        """Press a key via xdotool (e.g. 'Return', 'Tab', 'ctrl+a')."""
        interact.press_key(key, pause)

    def action(self, widget: object, action_name: str = "Press", pause: float = 0.3) -> None:
        """Invoke an AT-SPI action by name (e.g. 'Press', 'SetFocus')."""
        interact.action(widget, action_name, pause)

    def focus(self, widget: object, pause: float = 0.2) -> None:
        """Focus a widget via AT-SPI SetFocus, falling back to click."""
        interact.focus(widget, pause)

    # ── State ────────────────────────────────────────────────────

    def get_name(self, widget: object) -> str:
        """Get the accessible name of a widget."""
        return state.get_name(widget)

    def get_role(self, widget: object) -> str:
        """Get the role name of a widget."""
        return state.get_role(widget)

    def get_extents(self, widget: object) -> Extents:
        """Get screen position and size of a widget."""
        return state.get_extents(widget)

    def get_text(self, widget: object) -> str:
        """Get text content from a widget."""
        return state.get_text(widget)

    # ── Screenshots ──────────────────────────────────────────────

    def screenshot(self, path: str = "/tmp/screenshot.png") -> str:  # noqa: S108
        """Take a screenshot of the Xvfb display."""
        return take_screenshot(path)

    # ── Private ──────────────────────────────────────────────────

    def _walk(
        self,
        node: object,
        role: str | None,
        name: str | None,
        results: list[object],
    ) -> None:
        for i in range(node.get_child_count()):  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
            c = node.get_child_at_index(i)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
            if c is None:
                continue
            match = True
            if role and c.get_role_name() != role:
                match = False
            if name and name not in (c.get_name() or ""):
                match = False
            if match:
                results.append(c)
            self._walk(c, role, name, results)

    def _dump(
        self,
        node: object,
        indent: int,
        max_depth: int,
        lines: list[str],
    ) -> None:
        if indent > max_depth:
            return
        widget_name = node.get_name() or ""  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        role = node.get_role_name()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        try:
            ext = node.get_extents(Atspi.CoordType.SCREEN)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
            pos = f" @({ext.x},{ext.y} {ext.width}x{ext.height})"
        except Exception:
            pos = ""
        lines.append(f'{"  " * indent}[{role}] "{widget_name}"{pos}')
        for i in range(node.get_child_count()):  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
            c = node.get_child_at_index(i)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
            if c:
                self._dump(c, indent + 1, max_depth, lines)
