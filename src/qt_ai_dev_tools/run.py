"""Central subprocess execution with logging and dry-run support.

Every subprocess call in the project routes through run_command().
This gives uniform logging of all shell commands and dry-run capability.

Verbosity levels (controlled by -v/-vv on the CLI):
    - Default: no output (file log only)
    - INFO (-v): logs the command line: "$ vagrant up --provider=libvirt"
    - DEBUG (-vv): logs command line + full stdout/stderr

Dry-run (--dry-run): logs commands but does not execute them. Returns
a synthetic CompletedProcess with returncode=0 and empty stdout/stderr.
"""

from __future__ import annotations

import logging
import os
import shlex
import signal
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_dry_run: bool = False
_silent: bool = False


def set_dry_run(*, enabled: bool) -> None:
    """Enable or disable dry-run mode globally.

    Args:
        enabled: Whether to enable dry-run mode.
    """
    global _dry_run
    _dry_run = enabled


def is_dry_run() -> bool:
    """Check if dry-run mode is active."""
    return _dry_run


def set_silent(*, enabled: bool) -> None:
    """Enable or disable silent mode globally.

    Args:
        enabled: Whether to enable silent mode.
    """
    global _silent
    _silent = enabled


def is_silent() -> bool:
    """Check if silent mode is active."""
    return _silent


def _terminate_process(proc: subprocess.Popen[str], cmd_str: str) -> None:
    """Terminate a subprocess and its children via process group signals.

    Sends SIGTERM to the process group, waits up to 3 seconds for graceful
    shutdown, then escalates to SIGKILL if the process is still alive.
    """
    pid = proc.pid
    logger.debug("Terminating process %d: %s", pid, cmd_str)

    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        logger.debug("Sent SIGTERM to process group %d", pgid)
    except (ProcessLookupError, PermissionError):
        logger.debug("Process %d already gone (SIGTERM phase)", pid)
        return

    try:
        proc.wait(timeout=3)
        logger.debug("Process %d terminated gracefully", pid)
    except subprocess.TimeoutExpired:
        logger.debug("Process %d did not exit after SIGTERM, sending SIGKILL", pid)
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGKILL)
            logger.debug("Sent SIGKILL to process group %d", pgid)
        except (ProcessLookupError, PermissionError):
            logger.debug("Process %d already gone (SIGKILL phase)", pid)
        proc.wait()


def run_command(
    args: list[str],
    *,
    input_data: str | None = None,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    check: bool = False,
    stream: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with logging and optional dry-run.

    This is the single entry point for all subprocess execution in the project.
    Every command is logged at INFO (command line) and DEBUG (full output).

    Args:
        args: Command and arguments (e.g. ["xdotool", "click", "1"]).
        input_data: Optional string to pass on stdin.
        timeout: Maximum seconds to wait (None = no timeout).
        env: Extra environment variables (merged with current env).
        cwd: Working directory for the command.
        check: If True, raise RuntimeError on non-zero exit code.
        stream: If True, let stdout/stderr inherit from parent (print to terminal).
            Returns CompletedProcess with empty stdout/stderr.

    Returns:
        CompletedProcess with captured stdout and stderr (empty when stream=True).

    Raises:
        RuntimeError: If command times out, is not found, or fails with check=True.
    """
    cmd_str = shlex.join(args)

    if _dry_run:
        logger.info("[dry-run] $ %s", cmd_str)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    logger.info("$ %s", cmd_str)

    merged_env: dict[str, str] | None = None
    if env is not None:
        merged_env = {**os.environ, **env}

    if stream:
        try:
            proc = subprocess.Popen(
                args,
                text=True,
                env=merged_env,
                cwd=cwd,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            msg = f"Command not found: {args[0]}"
            raise RuntimeError(msg) from exc

        try:
            returncode = proc.wait(timeout=timeout)
        except KeyboardInterrupt:
            _terminate_process(proc, cmd_str)
            raise
        except subprocess.TimeoutExpired as exc:
            _terminate_process(proc, cmd_str)
            msg = f"Command timed out after {timeout}s: {cmd_str}"
            raise RuntimeError(msg) from exc

        if check and returncode != 0:
            msg = f"Command failed (exit {returncode}): {cmd_str}"
            raise RuntimeError(msg)

        return subprocess.CompletedProcess(args=args, returncode=returncode, stdout="", stderr="")

    try:
        proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if input_data is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=merged_env,
            cwd=cwd,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        msg = f"Command not found: {args[0]}"
        raise RuntimeError(msg) from exc

    try:
        stdout, stderr = proc.communicate(input=input_data, timeout=timeout)
        result = subprocess.CompletedProcess(
            args=args,
            returncode=proc.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
        )
    except KeyboardInterrupt:
        _terminate_process(proc, cmd_str)
        raise
    except subprocess.TimeoutExpired as exc:
        _terminate_process(proc, cmd_str)
        msg = f"Command timed out after {timeout}s: {cmd_str}"
        raise RuntimeError(msg) from exc

    if result.stdout:
        logger.debug("stdout:\n%s", result.stdout.rstrip())
    if result.stderr:
        logger.debug("stderr:\n%s", result.stderr.rstrip())
    logger.debug("exit code: %d", result.returncode)

    if check and result.returncode != 0:
        stderr_text = result.stderr.strip()
        msg = f"Command failed (exit {result.returncode}): {cmd_str}\n{stderr_text}"
        raise RuntimeError(msg)

    return result
