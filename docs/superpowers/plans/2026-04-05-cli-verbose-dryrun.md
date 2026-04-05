# CLI Verbose & Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Skills required:** `writing-python-code`, `testing-python`, `setting-up-logging`. Load ALL before writing any code.

**Goal:** Add `-v`/`-vv` verbosity and `--dry-run` flags to the CLI so users can see every shell command spawned under the hood, view full command output, and preview what would be executed without running it.

**Architecture:** Copy the reusable logging module into `src/qt_ai_dev_tools/logging/`. Wire a global typer callback to configure verbosity. Instrument the two central execution choke-points (`run_tool()` in `_subprocess.py` and `_vagrant()` in `vm.py`) plus scattered raw `subprocess.run()` calls in `interact.py` and `screenshot.py` — route them all through a single `run_command()` function that handles logging, dry-run, and output streaming. This is a **CLI tool**, so file logging is always on, stdout logging is **never** used — user-facing messages use `write_info`/`write_error` from the non-log output module. The `-v` flag controls whether `logger.info` (command lines) and `logger.debug` (full output) are echoed to stderr via a dedicated verbose handler.

**Tech Stack:** typer (CLI), colorlog (colored output), Python logging (file + conditional stderr), subprocess (execution)

**Key design decisions:**
- `-v` shows commands being run (INFO to stderr). `-vv` shows commands + their full stdout/stderr (DEBUG to stderr).
- Verbose output goes to **stderr**, not stdout — CLI output (widget trees, JSON, screenshots) stays clean on stdout for piping.
- `--dry-run` prints commands that would run and returns synthetic empty results. It only applies to subprocess execution — AT-SPI queries and Python-level operations still execute.
- File logging is always on at DEBUG level in `~/.local/state/qt-ai-dev-tools/logs/`. This means even without `-v`, users can check `qt-ai-dev-tools.log` after the fact.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/qt_ai_dev_tools/logging/__init__.py` | Public API re-exports |
| Create | `src/qt_ai_dev_tools/logging/logger_setup.py` | `setup_file_logging()`, `setup_stderr_logging()`, `configure_logger_level()` |
| Create | `src/qt_ai_dev_tools/logging/non_log_stdout_output.py` | `write_info()`, `write_success()`, `write_warning()`, `write_error()` |
| Create | `src/qt_ai_dev_tools/run.py` | `run_command()` — single entry point for all subprocess calls with logging + dry-run |
| Modify | `src/qt_ai_dev_tools/cli.py` | Add global `-v`/`-vv`/`--dry-run` callback, init logging on startup |
| Modify | `src/qt_ai_dev_tools/subsystems/_subprocess.py` | `run_tool()` delegates to `run_command()` |
| Modify | `src/qt_ai_dev_tools/vagrant/vm.py` | `_vagrant()` delegates to `run_command()` |
| Modify | `src/qt_ai_dev_tools/interact.py` | Replace raw `subprocess.run()` with `run_command()` |
| Modify | `src/qt_ai_dev_tools/screenshot.py` | Replace raw `subprocess.run()` with `run_command()` |
| Create | `tests/test_run.py` | Tests for `run_command()` + dry-run |
| Create | `tests/test_verbose.py` | Tests for CLI verbose flag integration |

---

## Task 1: Copy Reusable Logging Module

**Files:**
- Create: `src/qt_ai_dev_tools/logging/__init__.py`
- Create: `src/qt_ai_dev_tools/logging/logger_setup.py`
- Create: `src/qt_ai_dev_tools/logging/non_log_stdout_output.py`

Copy from `coding_rules_python/reusable/logging/` and adapt imports.

**Important adaptation:** The standard reusable module has `setup_stdout_logging()` for GUI/server use. We are a **CLI tool** — we never log to stdout. Instead, adapt `setup_stdout_logging()` into `setup_stderr_logging()` that sends verbose output to **stderr**. This keeps stdout clean for CLI output (widget trees, JSON, etc.) while allowing `-v` to show debug info on stderr.

- [ ] **Step 1: Create `src/qt_ai_dev_tools/logging/logger_setup.py`**

```python
"""Logging setup utilities for qt-ai-dev-tools CLI.

File logging is always on — durable record in ~/.local/state/qt-ai-dev-tools/logs/.
Stderr logging is conditional on -v/-vv — shows commands and output during verbose mode.
Stdout is NEVER used for logging — it's the user interface (widget trees, JSON, screenshots).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog


def setup_stderr_logging(level: int = logging.INFO) -> None:
    """Set up stderr logging with colored output for verbose mode.

    Adds a colored StreamHandler writing to stderr. Used when -v or -vv
    is passed — shows commands being run and their output.

    Goes to stderr so that stdout stays clean for piped CLI output.

    Args:
        level: Logging level (INFO for -v, DEBUG for -vv).
    """
    handler = colorlog.StreamHandler(sys.stderr)
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(name)s: %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            reset=True,
        )
    )
    handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    if root_logger.level == logging.NOTSET or level < root_logger.level:
        root_logger.setLevel(level)


def setup_file_logging(
    log_dir: Path,
    app_name: str = "app",
    level: int = logging.DEBUG,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """Set up rotating file logging.

    Always active — captures everything at DEBUG level for post-mortem.

    Args:
        log_dir: Directory to store log files (created if missing).
        app_name: Name used for the log file (becomes <app_name>.log).
        level: Logging level for file handler (default: DEBUG).
        max_bytes: Max size per log file before rotation (default: 5 MB).
        backup_count: Number of rotated files to keep (default: 3).
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{app_name}.log"

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    if root_logger.level == logging.NOTSET or level < root_logger.level:
        root_logger.setLevel(level)


def configure_logger_level(logger_name: str, level: int, propagate: bool = True) -> None:
    """Configure a specific logger's level and propagation.

    Args:
        logger_name: Name of the logger to configure.
        level: Logging level to set.
        propagate: Whether to propagate to parent loggers.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = propagate
```

- [ ] **Step 2: Create `src/qt_ai_dev_tools/logging/non_log_stdout_output.py`**

Copy directly from `coding_rules_python/reusable/logging/non_log_stdout_output.py` — only update the module docstring import path:

```python
"""Colored stdout output helpers for CLI tools.

These are NOT log entries — they're colored user-facing messages.
Use instead of stdout logging in CLI tools to keep output clean for piping.

Usage:
    from qt_ai_dev_tools.logging import write_info, write_error

    write_info("Processing 42 items...")
    write_error("Connection failed")
"""

from __future__ import annotations

import logging
import sys

import colorlog


def _get_colored_text(message: str, level: str) -> str:
    """Get colored version of message.

    Args:
        message: Text to color.
        level: Level name ("INFO", "WARNING", "ERROR", "SUCCESS").

    Returns:
        Colored text string.
    """
    level_map = {
        "INFO": logging.INFO,
        "SUCCESS": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    log_level = level_map.get(level, logging.INFO)

    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(message)s%(reset)s",
        log_colors={
            "INFO": "green",
            "SUCCESS": "green",
            "WARNING": "yellow",
            "ERROR": "red",
        },
        reset=True,
        stream=sys.stdout,
    )

    record = logging.LogRecord(
        name="stdout",
        level=log_level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )

    return formatter.format(record)


def write_info(message: str) -> None:
    """Write green info message to stdout."""
    colored = _get_colored_text(message, "INFO")
    sys.stdout.write(f"{colored}\n")


def write_success(message: str) -> None:
    """Write green success message to stdout."""
    colored = _get_colored_text(message, "SUCCESS")
    sys.stdout.write(f"{colored}\n")


def write_warning(message: str) -> None:
    """Write yellow warning message to stdout."""
    colored = _get_colored_text(message, "WARNING")
    sys.stdout.write(f"{colored}\n")


def write_error(message: str) -> None:
    """Write red error message to stderr."""
    colored = _get_colored_text(message, "ERROR")
    sys.stderr.write(f"{colored}\n")
```

- [ ] **Step 3: Create `src/qt_ai_dev_tools/logging/__init__.py`**

```python
"""Logging and colored output utilities for qt-ai-dev-tools.

See the setting-up-logging skill for usage guide.
"""

from qt_ai_dev_tools.logging.logger_setup import (
    configure_logger_level,
    setup_file_logging,
    setup_stderr_logging,
)
from qt_ai_dev_tools.logging.non_log_stdout_output import (
    write_error,
    write_info,
    write_success,
    write_warning,
)

__all__ = [
    "configure_logger_level",
    "setup_file_logging",
    "setup_stderr_logging",
    "write_error",
    "write_info",
    "write_success",
    "write_warning",
]
```

- [ ] **Step 4: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: New files pass lint. Fix any issues.

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/logging/
git commit -m "feat(logging): add logging module — file logging, stderr verbose, colored output

Copy reusable logging infrastructure adapted for CLI tool:
- File logging always on (~/.local/state/qt-ai-dev-tools/logs/)
- Stderr logging for -v/-vv verbose mode (not stdout — keeps output clean)
- Colored non-log output helpers (write_info, write_error, etc.)"
```

---

## Task 2: Create `run_command()` — Central Subprocess Execution with Logging & Dry-Run

This is the core of the feature. A single function that every subprocess call routes through.

**Files:**
- Create: `src/qt_ai_dev_tools/run.py`
- Create: `tests/test_run.py`

- [ ] **Step 1: Write failing tests for `run_command()`**

```python
"""Tests for the central run_command() subprocess wrapper."""

from __future__ import annotations

import logging

import pytest

from qt_ai_dev_tools.run import run_command, set_dry_run


class TestRunCommand:
    """Tests for run_command() execution and logging."""

    def test_captures_stdout(self) -> None:
        result = run_command(["echo", "hello"])
        assert result.stdout.strip() == "hello"
        assert result.returncode == 0

    def test_captures_stderr(self) -> None:
        result = run_command(["sh", "-c", "echo err >&2"])
        assert "err" in result.stderr

    def test_returns_nonzero_exit_code(self) -> None:
        result = run_command(["sh", "-c", "exit 42"])
        assert result.returncode == 42

    def test_passes_env(self) -> None:
        result = run_command(["sh", "-c", "echo $MY_VAR"], env={"MY_VAR": "test123"})
        assert result.stdout.strip() == "test123"

    def test_passes_input_data(self) -> None:
        result = run_command(["cat"], input_data="hello from stdin")
        assert result.stdout.strip() == "hello from stdin"

    def test_timeout_raises(self) -> None:
        with pytest.raises(RuntimeError, match="timed out"):
            run_command(["sleep", "10"], timeout=0.1)

    def test_command_not_found_raises(self) -> None:
        with pytest.raises(RuntimeError, match="not found"):
            run_command(["nonexistent_binary_xyz"])

    def test_logs_command_at_info(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="qt_ai_dev_tools.run"):
            run_command(["echo", "hello"])
        assert "$ echo hello" in caplog.text

    def test_logs_output_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="qt_ai_dev_tools.run"):
            run_command(["echo", "hello"])
        assert "hello" in caplog.text

    def test_cwd(self, tmp_path: object) -> None:
        result = run_command(["pwd"], cwd=tmp_path)  # type: ignore[arg-type]
        assert str(tmp_path) in result.stdout


class TestDryRun:
    """Tests for dry-run mode."""

    def test_dry_run_does_not_execute(self, caplog: pytest.LogCaptureFixture) -> None:
        set_dry_run(enabled=True)
        try:
            with caplog.at_level(logging.INFO, logger="qt_ai_dev_tools.run"):
                result = run_command(["rm", "-rf", "/"])  # would be catastrophic if it ran
            assert result.returncode == 0
            assert result.stdout == ""
            assert "[dry-run]" in caplog.text
        finally:
            set_dry_run(enabled=False)

    def test_dry_run_shows_command(self, caplog: pytest.LogCaptureFixture) -> None:
        set_dry_run(enabled=True)
        try:
            with caplog.at_level(logging.INFO, logger="qt_ai_dev_tools.run"):
                run_command(["vagrant", "up", "--provider=libvirt"])
            assert "vagrant up --provider=libvirt" in caplog.text
        finally:
            set_dry_run(enabled=False)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/test_run.py -v`
Expected: ImportError — `qt_ai_dev_tools.run` does not exist yet.

- [ ] **Step 3: Implement `run_command()`**

```python
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
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_dry_run: bool = False


def set_dry_run(*, enabled: bool) -> None:
    """Enable or disable dry-run mode globally.

    Args:
        enabled: Whether to enable dry-run mode.
    """
    global _dry_run  # noqa: PLW0603
    _dry_run = enabled


def is_dry_run() -> bool:
    """Check if dry-run mode is active."""
    return _dry_run


def run_command(
    args: list[str],
    *,
    input_data: str | None = None,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    check: bool = False,
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

    Returns:
        CompletedProcess with captured stdout and stderr.

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

    try:
        result = subprocess.run(
            args,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged_env,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"Command timed out after {timeout}s: {cmd_str}"
        raise RuntimeError(msg) from exc
    except FileNotFoundError as exc:
        msg = f"Command not found: {args[0]}"
        raise RuntimeError(msg) from exc

    if result.stdout:
        logger.debug("stdout:\n%s", result.stdout.rstrip())
    if result.stderr:
        logger.debug("stderr:\n%s", result.stderr.rstrip())
    logger.debug("exit code: %d", result.returncode)

    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"Command failed (exit {result.returncode}): {cmd_str}\n{stderr}"
        raise RuntimeError(msg)

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/test_run.py -v`
Expected: All pass.

- [ ] **Step 5: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass. Fix any issues.

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/run.py tests/test_run.py
git commit -m "feat(run): add central run_command() with logging and dry-run

Single entry point for all subprocess execution. Logs command at INFO,
full output at DEBUG. Dry-run mode skips execution and returns synthetic
empty result."
```

---

## Task 3: Wire Global `-v`/`-vv`/`--dry-run` into CLI

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py` (lines 20-24 — typer app definition, add callback)

- [ ] **Step 1: Add typer callback with verbosity and dry-run options**

Add this right after the `app = typer.Typer(...)` definition (line 20-24 of cli.py). The callback runs before every command:

```python
@app.callback()
def main_callback(
    verbose: typing.Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Increase verbosity (-v for commands, -vv for full output).",
        ),
    ] = 0,
    dry_run: typing.Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show commands that would be run without executing them.",
        ),
    ] = False,
) -> None:
    """AI agent tools for Qt/PySide app interaction via AT-SPI."""
    import logging
    from pathlib import Path

    from qt_ai_dev_tools.logging import setup_file_logging, setup_stderr_logging
    from qt_ai_dev_tools.run import set_dry_run

    # File logging is always on
    log_dir = Path("~/.local/state/qt-ai-dev-tools/logs").expanduser()
    setup_file_logging(log_dir=log_dir, app_name="qt-ai-dev-tools")

    # Stderr logging only when -v/-vv is given
    if verbose >= 2:
        setup_stderr_logging(level=logging.DEBUG)
    elif verbose >= 1:
        setup_stderr_logging(level=logging.INFO)

    if dry_run:
        set_dry_run(enabled=True)
```

Also remove `no_args_is_help=True` from the `typer.Typer()` call (line 23) — it conflicts with callbacks. Instead add `invoke_without_command=True` and handle the no-subcommand case in the callback:

Actually, `no_args_is_help=True` should stay — it shows help when no subcommand is given, which is the right behavior. The callback is compatible with `no_args_is_help=True` in typer. Keep the Typer definition as-is and just add the callback.

- [ ] **Step 2: Test the callback manually**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run qt-ai-dev-tools --help`
Expected: Shows `--verbose` / `-v` and `--dry-run` options in help output.

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run qt-ai-dev-tools -v vm status 2>/dev/null || true`
Expected: Verbose output on stderr (may fail if no VM, but the flag should be recognized).

- [ ] **Step 3: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "feat(cli): add global -v/-vv and --dry-run flags

Typer callback configures logging on every invocation:
- File logging always on (~/.local/state/qt-ai-dev-tools/logs/)
- -v: shows commands on stderr (INFO)
- -vv: shows commands + full output on stderr (DEBUG)
- --dry-run: prints commands without executing"
```

---

## Task 4: Migrate `_subprocess.py` to Use `run_command()`

**Files:**
- Modify: `src/qt_ai_dev_tools/subsystems/_subprocess.py`

`run_tool()` currently duplicates what `run_command()` does. Replace its implementation to delegate to `run_command()` while keeping the same public API (raises `RuntimeError` on failure, returns stdout string).

- [ ] **Step 1: Rewrite `run_tool()` to use `run_command()`**

Replace the body of `run_tool()` (lines 30-76) with:

```python
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
```

Remove the now-unused imports: `os`, `subprocess`. Keep `shutil` and `Path` (used by `check_tool()`).

- [ ] **Step 2: Run existing tests to verify nothing broke**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/ -v -k "not atspi and not vm and not cli" --timeout=30`
Expected: All passing tests still pass.

- [ ] **Step 3: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/subsystems/_subprocess.py
git commit -m "refactor(subprocess): delegate run_tool() to run_command()

All subsystem tool calls (clipboard, tray, notify, audio) now go through
the central run_command() — gets logging and dry-run for free."
```

---

## Task 5: Migrate `vagrant/vm.py` to Use `run_command()`

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py`

- [ ] **Step 1: Rewrite `_vagrant()` and related functions**

Replace `_vagrant()` (lines 31-39) to use `run_command()`:

```python
def _vagrant(args: list[str], workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run a vagrant command in the workspace directory."""
    from qt_ai_dev_tools.run import run_command

    return run_command(["vagrant", *args], cwd=workspace)
```

The return type and behavior stay the same — `CompletedProcess[str]` with captured output, no check (callers handle exit codes).

For `vm_ssh()` (line 54-57) — this is interactive, so it CANNOT go through `run_command()` (which captures output). Keep it as raw `subprocess.run()` but add logging:

```python
def vm_ssh(workspace: Path | None = None) -> None:
    """SSH into the VM (interactive)."""
    import logging

    logger = logging.getLogger(__name__)

    ws = find_workspace(workspace)
    logger.info("$ vagrant ssh (interactive)")
    subprocess.run(["vagrant", "ssh"], cwd=ws, check=False)
```

For `vm_sync_auto()` (lines 72-84) — this is a background `Popen`, cannot go through `run_command()`. Add logging:

```python
def vm_sync_auto(workspace: Path | None = None) -> subprocess.Popen[str]:
    """Start background rsync-auto to keep VM files in sync."""
    import logging

    logger = logging.getLogger(__name__)

    ws = find_workspace(workspace)
    logger.info("$ vagrant rsync-auto (background)")
    return subprocess.Popen(
        ["vagrant", "rsync-auto"],
        cwd=ws,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
```

Move the logger to module level (after imports) and remove the inline `import logging`:

```python
import logging
# ... other imports ...

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Run existing tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/ -v -k "not atspi" --timeout=30`
Expected: Pass.

- [ ] **Step 3: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/vagrant/vm.py
git commit -m "refactor(vm): delegate _vagrant() to run_command()

All vagrant commands (up, status, destroy, sync, run) now logged.
Interactive ssh and background rsync-auto still use raw subprocess
but log the command at INFO."
```

---

## Task 6: Migrate `interact.py` to Use `run_command()`

**Files:**
- Modify: `src/qt_ai_dev_tools/interact.py`

The xdotool calls currently use raw `subprocess.run()` with `check=True` and no output capture. Route them through `run_command(check=True)`.

- [ ] **Step 1: Replace subprocess calls with `run_command()`**

Replace the full file content. Key changes:
- Import `run_command` instead of `subprocess`
- Replace every `subprocess.run([...], check=True, env=env)` with `run_command([...], env=env, check=True)`
- The `_xdotool_env()` helper stays — it builds the env dict
- Remove `import subprocess`

Updated functions:

```python
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

    Args:
        x: Absolute X screen coordinate.
        y: Absolute Y screen coordinate.
        button: Mouse button (1=left, 2=middle, 3=right).
        pause: Seconds to sleep after click for UI to settle.
    """
    env = _xdotool_env()
    run_command(
        ["xdotool", "mousemove", "--screen", "0", str(x), str(y)],
        env=env,
        check=True,
    )
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
```

- [ ] **Step 2: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 3: Commit**

```bash
git add src/qt_ai_dev_tools/interact.py
git commit -m "refactor(interact): route xdotool calls through run_command()

All xdotool subprocess calls now logged and dry-run aware."
```

---

## Task 7: Migrate `screenshot.py` to Use `run_command()`

**Files:**
- Modify: `src/qt_ai_dev_tools/screenshot.py`

- [ ] **Step 1: Replace subprocess call with `run_command()`**

```python
"""Screenshot capture via scrot."""

from __future__ import annotations

import logging
import os

from qt_ai_dev_tools.run import run_command

logger = logging.getLogger(__name__)


def take_screenshot(path: str = "/tmp/screenshot.png") -> str:  # noqa: S108
    """Take a screenshot of the Xvfb display using scrot.

    Returns the path to the saved screenshot.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    run_command(["scrot", path], env=env, check=True)
    size = os.path.getsize(path)
    logger.info("Screenshot saved: %s (%d bytes)", path, size)
    return path
```

- [ ] **Step 2: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 3: Commit**

```bash
git add src/qt_ai_dev_tools/screenshot.py
git commit -m "refactor(screenshot): route scrot through run_command()"
```

---

## Task 8: Migrate Remaining Raw subprocess Calls in `cli.py`

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py` (lines 93-135 — `_proxy_screenshot` uses raw subprocess for `vagrant ssh-config` and `scp`)

- [ ] **Step 1: Replace raw subprocess calls in `_proxy_screenshot()`**

In `_proxy_screenshot()`, replace the two `subprocess.run()` calls (vagrant ssh-config and scp) with `run_command()`. Add `from qt_ai_dev_tools.run import run_command` to the function's lazy imports.

Replace `subprocess.run(["vagrant", "ssh-config"], ...)` with:
```python
from qt_ai_dev_tools.run import run_command
ssh_config_result = run_command(["vagrant", "ssh-config"], cwd=ws)
```

Replace `subprocess.run(["scp", ...], ...)` with:
```python
scp_result = run_command(["scp", "-F", str(ssh_config), f"default:{remote_path}", output])
```

Remove `import subprocess` from the function's lazy imports if no longer needed.

- [ ] **Step 2: Check for any other raw subprocess calls in cli.py**

Search for remaining `subprocess.run` or `subprocess.Popen` calls in cli.py. If found, migrate them similarly.

- [ ] **Step 3: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "refactor(cli): route proxy subprocess calls through run_command()

vagrant ssh-config and scp in _proxy_screenshot() now logged and dry-run aware."
```

---

## Task 9: Migrate Raw subprocess Calls in Subsystem Modules

**Files:**
- Modify: `src/qt_ai_dev_tools/subsystems/notify.py` (line 34 — raw `subprocess.run` for dbus-monitor)
- Modify: `src/qt_ai_dev_tools/subsystems/audio.py` (lines 43, 171, 310 — Popen for pw-loopback, subprocess.run for pw-record and sox)
- Modify: `src/qt_ai_dev_tools/bridge/_bootstrap.py` (line 58 — subprocess.run for python --version)

These are special cases that can't fully use `run_command()`:

- [ ] **Step 1: `notify.py` — dbus-monitor with expected timeout**

The `listen()` function uses `subprocess.run()` with a timeout that's expected to expire (dbus-monitor runs until killed). Replace with `run_command()` and handle the `RuntimeError` for timeout:

```python
from qt_ai_dev_tools.run import run_command

# In listen():
try:
    result = run_command(
        ["dbus-monitor", "--session", f"interface={_NOTIFY_IFACE},member=Notify"],
        timeout=timeout,
        env=env,
    )
    raw = result.stdout
except RuntimeError:
    # Timeout is expected — dbus-monitor runs until killed.
    # Fall back to raw subprocess to get partial stdout from TimeoutExpired.
    ...
```

Actually, `run_command()` raises `RuntimeError` on timeout and loses the partial stdout. For this specific case, keep the raw `subprocess.run()` but add manual logging:

```python
logger.info("$ dbus-monitor --session interface=%s,member=Notify (timeout=%ss)", _NOTIFY_IFACE, timeout)
try:
    result = subprocess.run(
        ["dbus-monitor", "--session", f"interface={_NOTIFY_IFACE},member=Notify"],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    raw = result.stdout
except subprocess.TimeoutExpired as exc:
    raw = exc.stdout or ""
    if isinstance(raw, bytes):
        raw = raw.decode()
logger.debug("dbus-monitor output:\n%s", raw)
```

- [ ] **Step 2: `audio.py` — background Popen and timeout-based recording**

Similar situation:
- `virtual_mic_start()` uses `Popen` (background) — add manual logging, keep Popen.
- `record()` uses timeout-as-duration pattern — add manual logging, keep raw subprocess.
- `verify_not_silence()` uses sox stat — can use `run_command()` since it's a normal call.

For `verify_not_silence()`, replace `subprocess.run(["sox", ...])` with:
```python
result = run_command(["sox", str(path), "-n", "stat"])
stat_output = result.stderr or result.stdout  # sox outputs to stderr
```

For `virtual_mic_start()` and `record()`, add `logger.info("$ %s", shlex.join(args))` before the call.

- [ ] **Step 3: `bridge/_bootstrap.py` — python --version probe**

Replace `subprocess.run([str(exe_path), "--version"], ...)` with `run_command()`:
```python
result = run_command([str(exe_path), "--version"], timeout=5)
```

- [ ] **Step 4: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/subsystems/notify.py src/qt_ai_dev_tools/subsystems/audio.py src/qt_ai_dev_tools/bridge/_bootstrap.py
git commit -m "refactor(subsystems): add logging to remaining subprocess calls

dbus-monitor and pw-record keep raw subprocess (timeout-as-feature pattern)
but now log commands. sox stat and python --version use run_command()."
```

---

## Task 10: Integration Test for Verbose & Dry-Run

**Files:**
- Create: `tests/test_verbose.py`

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for CLI verbose and dry-run flags."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.integration
class TestVerboseFlag:
    """Test that -v/-vv flags produce expected output."""

    def test_help_shows_verbose_option(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "qt_ai_dev_tools.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--verbose" in result.stdout or "-v" in result.stdout

    def test_help_shows_dry_run_option(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "qt_ai_dev_tools.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--dry-run" in result.stdout


@pytest.mark.integration
class TestDryRunFlag:
    """Test that --dry-run prevents actual execution."""

    def test_dry_run_vm_status(self) -> None:
        """--dry-run vm status should show the vagrant command without running it."""
        result = subprocess.run(
            [sys.executable, "-m", "qt_ai_dev_tools.cli", "--dry-run", "-v", "vm", "status"],
            capture_output=True,
            text=True,
        )
        # Should show the command on stderr
        assert "vagrant" in result.stderr
        assert "[dry-run]" in result.stderr
```

Note: These tests invoke the CLI as a subprocess to test the full flag pipeline. They don't need a VM. Adapt based on how cli.py is invokable as a module — may need a `__main__.py` or use `uv run qt-ai-dev-tools` directly.

- [ ] **Step 2: Run tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/test_verbose.py -v`
Expected: Pass.

- [ ] **Step 3: Run full lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_verbose.py
git commit -m "test: add integration tests for -v/-vv and --dry-run CLI flags"
```

---

## Task 11: Update Documentation

**Files:**
- Modify: `CLAUDE.md` — document -v/-vv/--dry-run in CLI usage section
- Modify: `README.md` — mention verbose/dry-run in CLI examples

- [ ] **Step 1: Update CLAUDE.md CLI usage section**

Add after the existing CLI usage examples (around line 110):

```markdown
### Debugging

```bash
# Show all shell commands being executed:
qt-ai-dev-tools -v tree

# Show commands + their full stdout/stderr:
qt-ai-dev-tools -vv vm up

# Preview what would run without executing:
qt-ai-dev-tools --dry-run vm up

# Combine: verbose dry-run shows every command that would execute:
qt-ai-dev-tools -v --dry-run click --role "push button" --name "Save"

# Log file (always written, even without -v):
# ~/.local/state/qt-ai-dev-tools/logs/qt-ai-dev-tools.log
```
```

- [ ] **Step 2: Update README.md**

Add a brief note in the CLI section mentioning `-v` and `--dry-run`.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: document -v/-vv and --dry-run CLI flags"
```

---

## Summary of Changes

| File | Change | Why |
|------|--------|-----|
| `src/qt_ai_dev_tools/logging/` | New module (3 files) | File + stderr logging, colored CLI output |
| `src/qt_ai_dev_tools/run.py` | New module | Central subprocess execution with logging + dry-run |
| `src/qt_ai_dev_tools/cli.py` | Add callback | Global `-v`/`-vv`/`--dry-run` flags |
| `src/qt_ai_dev_tools/subsystems/_subprocess.py` | Delegate to `run_command()` | All subsystem tools get logging |
| `src/qt_ai_dev_tools/vagrant/vm.py` | Delegate to `run_command()` | All vagrant calls get logging |
| `src/qt_ai_dev_tools/interact.py` | Replace raw subprocess | xdotool calls get logging |
| `src/qt_ai_dev_tools/screenshot.py` | Replace raw subprocess | scrot calls get logging |
| `src/qt_ai_dev_tools/subsystems/notify.py` | Add manual logging | dbus-monitor (special timeout pattern) |
| `src/qt_ai_dev_tools/subsystems/audio.py` | Mixed: run_command + logging | sox via run_command, Popen/timeout via manual logging |
| `src/qt_ai_dev_tools/bridge/_bootstrap.py` | Use run_command | Python version probe |
| `tests/test_run.py` | New | Unit tests for run_command + dry-run |
| `tests/test_verbose.py` | New | Integration tests for CLI flags |
| `CLAUDE.md`, `README.md` | Docs | Document new flags |
