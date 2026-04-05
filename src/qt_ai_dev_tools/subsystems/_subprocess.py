"""Typed subprocess wrapper for system tool invocation."""

from __future__ import annotations

import shutil
from pathlib import Path


def check_tool(name: str) -> Path:
    """Find a system tool on PATH or raise RuntimeError with install hint.

    Args:
        name: Binary name to locate (e.g. "xclip", "sox").

    Returns:
        Resolved Path to the binary.

    Raises:
        RuntimeError: If the tool is not found, with an install suggestion.
    """
    location = shutil.which(name)
    if location is None:
        msg = f"Required tool '{name}' not found. Install it with: apt-get install {name}"
        raise RuntimeError(msg)
    return Path(location)


def run_tool(
    args: list[str],
    *,
    input_data: str | None = None,
    timeout: float = 30.0,
    env: dict[str, str] | None = None,
) -> str:
    """Run a system tool and return its stdout.

    Delegates to run_command() for logging, dry-run, and execution.

    Args:
        args: Command and arguments (e.g. ["xclip", "-selection", "clipboard"]).
        input_data: Optional string to pass on stdin.
        timeout: Maximum seconds to wait (default 30).
        env: Optional environment variables (merged with current env).

    Returns:
        Captured stdout as a string.

    Raises:
        RuntimeError: If the command fails (non-zero exit) or times out.
    """
    from qt_ai_dev_tools.run import run_command

    result = run_command(args, input_data=input_data, timeout=timeout, env=env, check=True)
    return result.stdout
