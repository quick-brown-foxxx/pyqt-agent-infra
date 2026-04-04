"""Widget interaction via xdotool and AT-SPI actions."""

from __future__ import annotations

import os
import subprocess
import time

from qt_ai_dev_tools._atspi import AtspiNode


def _xdotool_env() -> dict[str, str]:
    """Environment with DISPLAY set for xdotool."""
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    return env


def click(widget: AtspiNode, pause: float = 0.2) -> None:
    """Click the center of a widget using xdotool."""
    ext = widget.get_extents()
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


def action(widget: AtspiNode, action_name: str = "Press", pause: float = 0.3) -> None:
    """Invoke an AT-SPI action by name (e.g. 'Press', 'SetFocus')."""
    widget.do_action(action_name, pause)


def focus(widget: AtspiNode, pause: float = 0.2) -> None:
    """Focus a widget via AT-SPI SetFocus, falling back to click."""
    try:
        action(widget, "SetFocus", pause=pause)
    except (RuntimeError, LookupError):
        click(widget, pause=pause)
