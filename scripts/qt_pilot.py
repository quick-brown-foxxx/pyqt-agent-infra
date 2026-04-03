"""
qt_pilot — lightweight AT-SPI + xdotool helper for agent-driven Qt interaction.

Usage:
    from qt_pilot import QtPilot

    pilot = QtPilot()                     # finds the first Qt app on the AT-SPI bus
    pilot = QtPilot(app_name="main.py")   # or by name

    # Tree inspection
    pilot.dump_tree()                     # print full widget tree
    widgets = pilot.find(role="push button", name="Save")
    widget  = pilot.find_one(role="text")

    # Interaction
    pilot.click(widget)                   # click center via xdotool
    pilot.type_text("hello")             # type via xdotool (into focused widget)
    pilot.action(widget, "Press")         # AT-SPI action (buttons, menus)
    pilot.focus(widget)                   # AT-SPI SetFocus action

    # State
    print(pilot.get_name(widget))
    print(pilot.get_value(widget))
    print(pilot.get_children(widget))
    ext = pilot.get_extents(widget)       # (x, y, w, h)

    # Screenshots
    pilot.screenshot("/tmp/shot.png")     # scrot on DISPLAY=:99
"""
import os
import subprocess
import time
from dataclasses import dataclass

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi


@dataclass
class Extents:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)


class QtPilot:
    def __init__(self, app_name: str | None = None, retries: int = 5, delay: float = 1.0):
        """Connect to a running Qt app via AT-SPI.

        Args:
            app_name: substring match against app name (default: first app found)
            retries: how many times to poll for the app to appear
            delay: seconds between retries
        """
        self.app = None
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
            apps = []
            desktop = Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                c = desktop.get_child_at_index(i)
                if c:
                    apps.append(c.get_name())
            raise RuntimeError(
                f"App '{app_name}' not found on AT-SPI bus. "
                f"Visible apps: {apps}"
            )

    # ── Tree inspection ──────────────────────────────────────────────────────

    def find(self, role: str | None = None, name: str | None = None,
             root=None) -> list:
        """Find all widgets matching role and/or name (substring match)."""
        root = root or self.app
        results = []
        self._walk(root, role, name, results)
        return results

    def find_one(self, role: str | None = None, name: str | None = None,
                 root=None):
        """Find exactly one widget. Raises if 0 or >1 found."""
        found = self.find(role, name, root)
        if len(found) == 0:
            raise LookupError(f"No widget found: role={role}, name={name}")
        if len(found) > 1:
            descs = [f"[{w.get_role_name()}] \"{w.get_name()}\"" for w in found]
            raise LookupError(
                f"Multiple widgets found for role={role}, name={name}: {descs}"
            )
        return found[0]

    def dump_tree(self, root=None, indent: int = 0, max_depth: int = 8) -> str:
        """Return a text dump of the widget tree."""
        root = root or self.app
        lines = []
        self._dump(root, indent, max_depth, lines)
        text = "\n".join(lines)
        print(text)
        return text

    def get_children(self, widget) -> list:
        """Get direct children of a widget."""
        children = []
        for i in range(widget.get_child_count()):
            c = widget.get_child_at_index(i)
            if c:
                children.append(c)
        return children

    # ── Interaction ──────────────────────────────────────────────────────────

    def click(self, widget, pause: float = 0.2):
        """Click the center of a widget using xdotool."""
        ext = self.get_extents(widget)
        cx, cy = ext.center
        subprocess.run(["xdotool", "mousemove", str(cx), str(cy)],
                        check=True, env=self._xdotool_env())
        subprocess.run(["xdotool", "click", "1"],
                        check=True, env=self._xdotool_env())
        time.sleep(pause)

    def type_text(self, text: str, delay_ms: int = 20, pause: float = 0.2):
        """Type text via xdotool into the currently focused widget."""
        subprocess.run(["xdotool", "type", "--delay", str(delay_ms), text],
                        check=True, env=self._xdotool_env())
        time.sleep(pause)

    def press_key(self, key: str, pause: float = 0.1):
        """Press a key via xdotool (e.g. 'Return', 'Tab', 'ctrl+a')."""
        subprocess.run(["xdotool", "key", key],
                        check=True, env=self._xdotool_env())
        time.sleep(pause)

    def action(self, widget, action_name: str = "Press", pause: float = 0.3):
        """Invoke an AT-SPI action by name (e.g. 'Press', 'SetFocus')."""
        iface = widget.get_action_iface()
        if not iface:
            raise RuntimeError(
                f"Widget [{widget.get_role_name()}] \"{widget.get_name()}\" "
                f"has no action interface"
            )
        for i in range(iface.get_n_actions()):
            if iface.get_action_name(i) == action_name:
                iface.do_action(i)
                time.sleep(pause)
                return
        available = [iface.get_action_name(i) for i in range(iface.get_n_actions())]
        raise LookupError(
            f"Action '{action_name}' not found. Available: {available}"
        )

    def focus(self, widget, pause: float = 0.2):
        """Focus a widget via AT-SPI SetFocus action, falling back to click."""
        try:
            self.action(widget, "SetFocus", pause=pause)
        except (RuntimeError, LookupError):
            self.click(widget, pause=pause)

    # ── State ────────────────────────────────────────────────────────────────

    def get_name(self, widget) -> str:
        return widget.get_name() or ""

    def get_role(self, widget) -> str:
        return widget.get_role_name()

    def get_extents(self, widget) -> Extents:
        ext = widget.get_extents(Atspi.CoordType.SCREEN)
        return Extents(ext.x, ext.y, ext.width, ext.height)

    def get_text(self, widget) -> str:
        """Get text content from a text widget."""
        iface = widget.get_text_iface()
        if iface:
            return iface.get_text(0, iface.get_character_count())
        return widget.get_name() or ""

    # ── Screenshots ──────────────────────────────────────────────────────────

    def screenshot(self, path: str = "/tmp/screenshot.png"):
        """Take a screenshot of the Xvfb display."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        subprocess.run(["scrot", path], check=True, env=self._xdotool_env())
        size = os.path.getsize(path)
        print(f"Screenshot: {path} ({size} bytes)")
        return path

    # ── Private ──────────────────────────────────────────────────────────────

    def _walk(self, node, role, name, results):
        for i in range(node.get_child_count()):
            c = node.get_child_at_index(i)
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

    def _dump(self, node, indent, max_depth, lines):
        if indent > max_depth:
            return
        name = node.get_name() or ""
        role = node.get_role_name()
        try:
            ext = node.get_extents(Atspi.CoordType.SCREEN)
            pos = f" @({ext.x},{ext.y} {ext.width}x{ext.height})"
        except Exception:
            pos = ""
        lines.append(f"{'  ' * indent}[{role}] \"{name}\"{pos}")
        for i in range(node.get_child_count()):
            c = node.get_child_at_index(i)
            if c:
                self._dump(c, indent + 1, max_depth, lines)

    def _xdotool_env(self):
        env = os.environ.copy()
        env.setdefault("DISPLAY", ":99")
        return env
