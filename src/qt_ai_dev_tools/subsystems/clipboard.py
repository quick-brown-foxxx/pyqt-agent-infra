"""Clipboard operations via xsel (preferred) or xclip.

xsel is preferred because it exits immediately after writing. xclip stays
alive to serve the X selection, which causes subprocess timeouts.
"""

from __future__ import annotations

import os
import shutil

from qt_ai_dev_tools.subsystems._subprocess import check_tool, run_tool


def _clipboard_env() -> dict[str, str]:
    """Build environment with DISPLAY defaulting to :99."""
    env = dict(os.environ)
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":99"
    return env


def _use_xsel() -> bool:
    """Return True if xsel is available (preferred over xclip)."""
    return shutil.which("xsel") is not None


def write(text: str) -> None:
    """Write text to the system clipboard.

    Uses xsel if available (exits immediately), falls back to xclip with
    background detach.

    Args:
        text: The text to copy to the clipboard.

    Raises:
        RuntimeError: If neither xsel nor xclip is installed or the command fails.
    """
    env = _clipboard_env()
    if _use_xsel():
        check_tool("xsel")
        run_tool(["xsel", "--clipboard", "--input"], input_data=text, env=env)
    else:
        check_tool("xclip")
        # xclip -selection clipboard stays alive to serve the X selection.
        # Use -l 0 (serve zero paste requests then exit) — the selection is
        # still stored by the X server after xclip exits.
        run_tool(
            ["xclip", "-selection", "clipboard", "-l", "0"],
            input_data=text,
            env=env,
            timeout=5.0,
        )


def read() -> str:
    """Read text from the system clipboard.

    Returns:
        The current clipboard content as a string.

    Raises:
        RuntimeError: If neither xsel nor xclip is installed or the command fails.
    """
    env = _clipboard_env()
    if _use_xsel():
        check_tool("xsel")
        return run_tool(["xsel", "--clipboard", "--output"], env=env)
    check_tool("xclip")
    return run_tool(["xclip", "-selection", "clipboard", "-o"], env=env)
