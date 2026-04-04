"""Typed subprocess wrapper for system tool invocation."""

from __future__ import annotations

import os
import shutil
import subprocess
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
    merged_env: dict[str, str] | None = None
    if env is not None:
        merged_env = {**os.environ, **env}

    try:
        result = subprocess.run(
            args,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged_env,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"Command timed out after {timeout}s: {args}"
        raise RuntimeError(msg) from exc
    except FileNotFoundError as exc:
        msg = f"Command not found: {args[0]}"
        raise RuntimeError(msg) from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"Command failed (exit {result.returncode}): {args}\n{stderr}"
        raise RuntimeError(msg)

    return result.stdout
