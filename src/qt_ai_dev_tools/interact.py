"""Widget interaction via xdotool and AT-SPI actions."""

from __future__ import annotations

import os
import subprocess
import time

import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection

from qt_ai_dev_tools.state import get_extents

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # type: ignore[import-untyped]  # noqa: E402, F401  # rationale: system AT-SPI bindings


def _xdotool_env() -> dict[str, str]:
    """Environment with DISPLAY set for xdotool."""
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    return env


def click(widget: object, pause: float = 0.2) -> None:
    """Click the center of a widget using xdotool."""
    ext = get_extents(widget)
    cx, cy = ext.center
    env = _xdotool_env()
    subprocess.run(["xdotool", "mousemove", str(cx), str(cy)], check=True, env=env)
    subprocess.run(["xdotool", "click", "1"], check=True, env=env)
    time.sleep(pause)


def type_text(text: str, delay_ms: int = 20, pause: float = 0.2) -> None:
    """Type text via xdotool into the currently focused widget."""
    subprocess.run(
        ["xdotool", "type", "--delay", str(delay_ms), text],
        check=True,
        env=_xdotool_env(),
    )
    time.sleep(pause)


def press_key(key: str, pause: float = 0.1) -> None:
    """Press a key via xdotool (e.g. 'Return', 'Tab', 'ctrl+a')."""
    subprocess.run(["xdotool", "key", key], check=True, env=_xdotool_env())
    time.sleep(pause)


def action(widget: object, action_name: str = "Press", pause: float = 0.3) -> None:
    """Invoke an AT-SPI action by name (e.g. 'Press', 'SetFocus')."""
    iface = widget.get_action_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        role = widget.get_role_name()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        name = widget.get_name()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        msg = f'Widget [{role}] "{name}" has no action interface'
        raise RuntimeError(msg)
    for i in range(iface.get_n_actions()):
        if iface.get_action_name(i) == action_name:
            iface.do_action(i)
            time.sleep(pause)
            return
    available = [iface.get_action_name(i) for i in range(iface.get_n_actions())]
    msg = f"Action '{action_name}' not found. Available: {available}"
    raise LookupError(msg)


def focus(widget: object, pause: float = 0.2) -> None:
    """Focus a widget via AT-SPI SetFocus, falling back to click."""
    try:
        action(widget, "SetFocus", pause=pause)
    except (RuntimeError, LookupError):
        click(widget, pause=pause)
