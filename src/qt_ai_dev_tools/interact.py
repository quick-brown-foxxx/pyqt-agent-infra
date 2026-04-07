"""Widget interaction via xdotool and AT-SPI actions."""

from __future__ import annotations

import os
import time

from qt_ai_dev_tools._atspi import AtspiNode
from qt_ai_dev_tools.run import run_command


def _xdotool_env() -> dict[str, str]:
    """Environment with DISPLAY set for xdotool."""
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    return env


def click_at(x: int, y: int, button: int = 1, pause: float = 0.2) -> None:
    """Click at absolute screen coordinates using xdotool.

    Moves the mouse, activates the window under the cursor (to handle
    focus loss between separate CLI invocations), then clicks.

    Args:
        x: Absolute X screen coordinate.
        y: Absolute Y screen coordinate.
        button: Mouse button (1=left, 2=middle, 3=right).
        pause: Seconds to sleep after click for UI to settle.
    """
    env = _xdotool_env()
    # Check display bounds to prevent silent false-success clicks (ISSUE-012)
    geo_result = run_command(
        ["xdotool", "getdisplaygeometry"],
        env=env,
        check=False,
    )
    if geo_result.returncode == 0 and geo_result.stdout.strip():
        parts = geo_result.stdout.strip().split()
        if len(parts) == 2:
            display_w, display_h = int(parts[0]), int(parts[1])
            if x < 0 or y < 0 or x > display_w or y > display_h:
                msg = (
                    f"Coordinates ({x}, {y}) outside display bounds "
                    f"({display_w}x{display_h}). Widget may need scrolling into view."
                )
                raise ValueError(msg)
    if x == 0 and y == 0:
        msg = (
            "Widget is at coordinates (0, 0), which typically means it is inside a "
            "closed popup menu or not yet rendered. Open the parent menu first."
        )
        raise ValueError(msg)
    run_command(
        ["xdotool", "mousemove", "--screen", "0", str(x), str(y)],
        env=env,
        check=True,
    )
    # Focus the window under the cursor so it receives the click.
    # This prevents a race condition where the target window loses X11
    # focus between separate CLI subprocess invocations (e.g. fill then do click).
    # Uses windowfocus (not windowactivate) because windowactivate requires
    # _NET_WM_DESKTOP which may not be set in Xvfb + openbox environments.
    result = run_command(
        ["xdotool", "getmouselocation", "--shell"],
        env=env,
        check=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("WINDOW="):
            window_id = line.split("=", 1)[1]
            run_command(
                ["xdotool", "windowfocus", window_id],
                env=env,
                check=False,
            )
            break
    time.sleep(0.05)
    run_command(["xdotool", "click", str(button)], env=env, check=True)
    time.sleep(pause)


def click(widget: AtspiNode, pause: float = 0.2) -> None:
    """Click the center of a widget using xdotool."""
    ext = widget.get_extents()
    cx, cy = ext.center
    click_at(cx, cy, button=1, pause=pause)


def type_text(text: str, delay_ms: int = 20, pause: float = 0.2) -> None:
    """Type text via xdotool into the currently focused widget."""
    run_command(
        ["xdotool", "type", "--delay", str(delay_ms), text],
        env=_xdotool_env(),
        check=True,
    )
    time.sleep(pause)


def press_key(key: str, pause: float = 0.1) -> None:
    """Press a key via xdotool (e.g. 'Return', 'Tab', 'ctrl+a')."""
    run_command(["xdotool", "key", key], env=_xdotool_env(), check=True)
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
