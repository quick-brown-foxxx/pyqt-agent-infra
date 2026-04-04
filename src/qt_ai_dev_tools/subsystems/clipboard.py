"""Clipboard operations via xclip."""

from __future__ import annotations

import os

from qt_ai_dev_tools.subsystems._subprocess import check_tool, run_tool


def _clipboard_env() -> dict[str, str]:
    """Build environment with DISPLAY defaulting to :99."""
    env = dict(os.environ)
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":99"
    return env


def write(text: str) -> None:
    """Write text to the system clipboard via xclip.

    Args:
        text: The text to copy to the clipboard.

    Raises:
        RuntimeError: If xclip is not installed or the command fails.
    """
    check_tool("xclip")
    env = _clipboard_env()
    run_tool(["xclip", "-selection", "clipboard"], input_data=text, env=env)


def read() -> str:
    """Read text from the system clipboard via xclip.

    Returns:
        The current clipboard content as a string.

    Raises:
        RuntimeError: If xclip is not installed or the command fails.
    """
    check_tool("xclip")
    env = _clipboard_env()
    return run_tool(["xclip", "-selection", "clipboard", "-o"], env=env)
