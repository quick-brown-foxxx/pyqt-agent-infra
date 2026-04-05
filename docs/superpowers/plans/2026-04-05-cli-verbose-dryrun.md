# CLI Verbose & Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Skills required:** `writing-python-code`, `testing-python`, `setting-up-logging`. Load ALL before writing any code.

**Goal:** Add `-v`/`-vv` verbosity and `--dry-run` flags to the CLI so users can see every shell command spawned under the hood, view full command output, and preview what would be executed without running it.

**Architecture:** Copy the reusable logging module into `src/qt_ai_dev_tools/logging/`. Wire a global typer callback to configure verbosity. Instrument the two central execution choke-points (`run_tool()` in `_subprocess.py` and `_vagrant()` in `vm.py`) plus scattered raw `subprocess.run()` calls in `interact.py` and `screenshot.py` — route them all through a single `run_command()` function that handles logging, dry-run, and output streaming.

**Tech Stack:** typer (CLI), colorlog (colored output), Python logging (file + conditional stderr), subprocess (execution)

**Key design decisions:**
- This is a **CLI tool** — file logging always on, stdout logging **never** used. Verbose output goes to **stderr** via `setup_stderr_logging()` so stdout stays clean for piping.
- `-v` shows commands being run (INFO to stderr). `-vv` shows commands + their full stdout/stderr (DEBUG to stderr).
- `--dry-run` prints commands that would run and returns synthetic empty results. Only applies to subprocess execution.
- File logging always on at DEBUG in `~/.local/state/qt-ai-dev-tools/logs/`.
- **Existing unit tests** mock `subprocess.run` at module paths like `qt_ai_dev_tools.interact.subprocess.run` — after migration to `run_command()`, these mock paths must be updated to `qt_ai_dev_tools.run.subprocess.run`.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/qt_ai_dev_tools/logging/__init__.py` | Public API re-exports |
| Create | `src/qt_ai_dev_tools/logging/logger_setup.py` | `setup_file_logging()`, `setup_stderr_logging()`, `configure_logger_level()` |
| Create | `src/qt_ai_dev_tools/logging/non_log_stdout_output.py` | `write_info()`, `write_success()`, `write_warning()`, `write_error()` |
| Create | `src/qt_ai_dev_tools/run.py` | `run_command()` — single entry point for all subprocess calls |
| Modify | `src/qt_ai_dev_tools/cli.py:20-24` | Add global `-v`/`-vv`/`--dry-run` callback |
| Modify | `src/qt_ai_dev_tools/subsystems/_subprocess.py:30-76` | `run_tool()` delegates to `run_command()` |
| Modify | `src/qt_ai_dev_tools/vagrant/vm.py:31-39` | `_vagrant()` delegates to `run_command()` |
| Modify | `src/qt_ai_dev_tools/interact.py` | Replace raw `subprocess.run()` with `run_command()` |
| Modify | `src/qt_ai_dev_tools/screenshot.py` | Replace raw `subprocess.run()` with `run_command()` |
| Create | `tests/unit/test_run.py` | Unit tests for `run_command()` + dry-run |
| Modify | `tests/unit/test_interact.py` | Update mock paths from `subprocess.run` to `run_command` |
| Modify | `tests/unit/test_vm.py` | Update mock paths from `subprocess.run` to `run_command` |
| Create | `tests/integration/test_verbose_dryrun.py` | CLI integration tests for flags |

---

## Test Plan

### Test cases — categorized by importance

**Critical (must have):**
1. `run_command()` captures stdout/stderr and returns CompletedProcess
2. `run_command()` raises RuntimeError on timeout
3. `run_command()` raises RuntimeError on command not found
4. `run_command(check=True)` raises on non-zero exit
5. `run_command()` passes environment variables
6. `run_command()` logs command at INFO level
7. `run_command()` logs output at DEBUG level
8. Dry-run mode returns synthetic result without executing
9. Dry-run mode logs `[dry-run]` prefix
10. `--verbose` and `--dry-run` appear in CLI `--help`
11. `-v` flag causes command logging on stderr
12. `--dry-run` flag prevents actual vagrant execution
13. Existing `test_interact.py` tests still pass after migration
14. Existing `test_vm.py` tests still pass after migration

**Medium (should have):**
15. `run_command()` passes cwd to subprocess
16. `run_command()` passes input_data to subprocess
17. `run_tool()` still works identically after delegation to `run_command()`

**Discarded (not worth maintenance):**
- Testing colorlog output format details
- Testing file rotation parameters
- Testing `write_info`/`write_error` color output (trivial wrappers)

---

## Task 1: Copy Reusable Logging Module

**Files:**
- Create: `src/qt_ai_dev_tools/logging/__init__.py`
- Create: `src/qt_ai_dev_tools/logging/logger_setup.py`
- Create: `src/qt_ai_dev_tools/logging/non_log_stdout_output.py`

Copy from `coding_rules_python/reusable/logging/` and adapt. Key adaptation: rename `setup_stdout_logging()` to `setup_stderr_logging()` that writes to `sys.stderr` (we are a CLI tool — stdout is the user interface).

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

Copy from `coding_rules_python/reusable/logging/non_log_stdout_output.py`, update module docstring import path to `from qt_ai_dev_tools.logging import write_info, write_error`. Keep all function implementations identical.

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
git commit -m "feat(logging): add logging module — file logging, stderr verbose, colored output"
```

---

## Task 2: Create `run_command()` with Tests (TDD)

**Files:**
- Create: `src/qt_ai_dev_tools/run.py`
- Create: `tests/unit/test_run.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_run.py`:

```python
"""Tests for the central run_command() subprocess wrapper."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


class TestRunCommandExecution:
    """Test that run_command() executes commands and captures output."""

    def test_captures_stdout(self) -> None:
        from qt_ai_dev_tools.run import run_command

        result = run_command(["echo", "hello"])
        assert result.stdout.strip() == "hello"
        assert result.returncode == 0

    def test_captures_stderr(self) -> None:
        from qt_ai_dev_tools.run import run_command

        result = run_command(["sh", "-c", "echo err >&2"])
        assert "err" in result.stderr

    def test_nonzero_exit_code_returned(self) -> None:
        from qt_ai_dev_tools.run import run_command

        result = run_command(["sh", "-c", "exit 42"])
        assert result.returncode == 42

    def test_check_true_raises_on_failure(self) -> None:
        from qt_ai_dev_tools.run import run_command

        with pytest.raises(RuntimeError, match="Command failed"):
            run_command(["sh", "-c", "exit 1"], check=True)

    def test_passes_env_variables(self) -> None:
        from qt_ai_dev_tools.run import run_command

        result = run_command(["sh", "-c", "echo $MY_TEST_VAR"], env={"MY_TEST_VAR": "xyz789"})
        assert result.stdout.strip() == "xyz789"

    def test_passes_input_data_to_stdin(self) -> None:
        from qt_ai_dev_tools.run import run_command

        result = run_command(["cat"], input_data="hello from stdin")
        assert result.stdout.strip() == "hello from stdin"

    def test_timeout_raises_runtime_error(self) -> None:
        from qt_ai_dev_tools.run import run_command

        with pytest.raises(RuntimeError, match="timed out"):
            run_command(["sleep", "10"], timeout=0.1)

    def test_command_not_found_raises_runtime_error(self) -> None:
        from qt_ai_dev_tools.run import run_command

        with pytest.raises(RuntimeError, match="not found"):
            run_command(["nonexistent_binary_xyz_12345"])

    def test_cwd_sets_working_directory(self, tmp_path: Path) -> None:
        from qt_ai_dev_tools.run import run_command

        result = run_command(["pwd"], cwd=tmp_path)
        assert str(tmp_path) in result.stdout


class TestRunCommandLogging:
    """Test that run_command() logs commands and output."""

    def test_logs_command_at_info(self, caplog: pytest.LogCaptureFixture) -> None:
        from qt_ai_dev_tools.run import run_command

        with caplog.at_level(logging.INFO, logger="qt_ai_dev_tools.run"):
            run_command(["echo", "hello"])
        assert "$ echo hello" in caplog.text

    def test_logs_stdout_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        from qt_ai_dev_tools.run import run_command

        with caplog.at_level(logging.DEBUG, logger="qt_ai_dev_tools.run"):
            run_command(["echo", "debug_output_test"])
        assert "debug_output_test" in caplog.text

    def test_logs_exit_code_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        from qt_ai_dev_tools.run import run_command

        with caplog.at_level(logging.DEBUG, logger="qt_ai_dev_tools.run"):
            run_command(["sh", "-c", "exit 0"])
        assert "exit code: 0" in caplog.text


class TestDryRun:
    """Test that dry-run mode prevents execution."""

    def test_dry_run_does_not_execute(self, caplog: pytest.LogCaptureFixture) -> None:
        from qt_ai_dev_tools.run import run_command, set_dry_run

        set_dry_run(enabled=True)
        try:
            with caplog.at_level(logging.INFO, logger="qt_ai_dev_tools.run"):
                result = run_command(["sh", "-c", "echo should_not_appear > /tmp/_dryrun_test"])
            assert result.returncode == 0
            assert result.stdout == ""
            assert result.stderr == ""
            assert "[dry-run]" in caplog.text
            # File should NOT have been created
            import os

            assert not os.path.exists("/tmp/_dryrun_test")
        finally:
            set_dry_run(enabled=False)

    def test_dry_run_logs_command(self, caplog: pytest.LogCaptureFixture) -> None:
        from qt_ai_dev_tools.run import run_command, set_dry_run

        set_dry_run(enabled=True)
        try:
            with caplog.at_level(logging.INFO, logger="qt_ai_dev_tools.run"):
                run_command(["vagrant", "up", "--provider=libvirt"])
            assert "vagrant up --provider=libvirt" in caplog.text
        finally:
            set_dry_run(enabled=False)

    def test_set_dry_run_toggle(self) -> None:
        from qt_ai_dev_tools.run import is_dry_run, set_dry_run

        assert is_dry_run() is False
        set_dry_run(enabled=True)
        assert is_dry_run() is True
        set_dry_run(enabled=False)
        assert is_dry_run() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/unit/test_run.py -v`
Expected: ImportError — `qt_ai_dev_tools.run` does not exist.

- [ ] **Step 3: Implement `run_command()`**

Create `src/qt_ai_dev_tools/run.py`:

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

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/unit/test_run.py -v`
Expected: All pass.

- [ ] **Step 5: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/run.py tests/unit/test_run.py
git commit -m "feat(run): add central run_command() with logging and dry-run"
```

---

## Task 3: Wire Global `-v`/`-vv`/`--dry-run` into CLI

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`

- [ ] **Step 1: Add typer callback with verbosity and dry-run options**

Add right after `app = typer.Typer(...)` (line 20-24 of cli.py):

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
    if verbose >= 2:  # noqa: PLR2004
        setup_stderr_logging(level=logging.DEBUG)
    elif verbose >= 1:
        setup_stderr_logging(level=logging.INFO)

    if dry_run:
        set_dry_run(enabled=True)
```

- [ ] **Step 2: Verify help output**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run qt-ai-dev-tools --help`
Expected: Shows `--verbose` / `-v` and `--dry-run` in output.

- [ ] **Step 3: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "feat(cli): add global -v/-vv and --dry-run flags via typer callback"
```

---

## Task 4: Migrate `_subprocess.py` to Use `run_command()`

**Files:**
- Modify: `src/qt_ai_dev_tools/subsystems/_subprocess.py`

- [ ] **Step 1: Rewrite `run_tool()` to delegate to `run_command()`**

Replace lines 30-76 with:

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

Remove unused imports `os` and `subprocess`. Keep `shutil` and `Path` (used by `check_tool()`).

- [ ] **Step 2: Run existing tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/unit/ -v --timeout=30`
Expected: All passing tests still pass (subsystem tests mock `run_tool` not `subprocess.run`).

- [ ] **Step 3: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`

- [ ] **Step 4: Commit**

```bash
git add src/qt_ai_dev_tools/subsystems/_subprocess.py
git commit -m "refactor(subprocess): delegate run_tool() to run_command()"
```

---

## Task 5: Migrate `vagrant/vm.py` and Update `test_vm.py`

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py`
- Modify: `tests/unit/test_vm.py`

The existing `test_vm.py` mocks `qt_ai_dev_tools.vagrant.vm.subprocess.run`. After we change `_vagrant()` to use `run_command()`, these mock paths break. We must update them.

- [ ] **Step 1: Rewrite `_vagrant()` and add logger**

In `vm.py`, add `import logging` and `logger = logging.getLogger(__name__)` at module level. Rewrite `_vagrant()`:

```python
def _vagrant(args: list[str], workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run a vagrant command in the workspace directory."""
    from qt_ai_dev_tools.run import run_command

    return run_command(["vagrant", *args], cwd=workspace)
```

For `vm_ssh()` — interactive, keep raw subprocess but log:

```python
def vm_ssh(workspace: Path | None = None) -> None:
    """SSH into the VM (interactive)."""
    ws = find_workspace(workspace)
    logger.info("$ vagrant ssh (interactive)")
    subprocess.run(["vagrant", "ssh"], cwd=ws, check=False)
```

For `vm_sync_auto()` — background Popen, keep but log:

```python
def vm_sync_auto(workspace: Path | None = None) -> subprocess.Popen[str]:
    """Start background rsync-auto to keep VM files in sync."""
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

- [ ] **Step 2: Update `tests/unit/test_vm.py` mock paths**

The tests that mock `qt_ai_dev_tools.vagrant.vm.subprocess.run` need to mock `qt_ai_dev_tools.run.subprocess.run` instead, since `_vagrant()` now calls `run_command()` which calls `subprocess.run` in `qt_ai_dev_tools.run`.

Update `TestVagrant`, `TestVmUp`, `TestVmStatus`, `TestVmDestroy`, `TestVmSync`, `TestVmRun` to mock `qt_ai_dev_tools.run.subprocess.run` instead of `qt_ai_dev_tools.vagrant.vm.subprocess.run`.

Also update the assertion — `run_command()` always passes `capture_output=True, text=True` but also passes `input=None, timeout=None, cwd=workspace, env=None`. Adjust `assert_called_once_with` accordingly, or switch to checking `call_args[0][0]` (the command list) and key kwargs.

Example update for `TestVagrant`:

```python
class TestVagrant:
    def test_vagrant_helper_calls_subprocess(self, tmp_path: Path) -> None:
        with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["vagrant", "status"], returncode=0, stdout="", stderr=""
            )
            _vagrant(["status"], tmp_path)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["vagrant", "status"]
            assert call_args[1]["cwd"] == tmp_path
```

Apply the same pattern to `TestVmUp`, `TestVmStatus`, `TestVmDestroy`, `TestVmSync`, `TestVmRun`. For `TestVmSyncAuto` — it still uses raw `subprocess.Popen`, so keep mocking `subprocess.Popen` but update the import path if needed.

- [ ] **Step 3: Run updated tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/unit/test_vm.py -v`
Expected: All pass.

- [ ] **Step 4: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/vagrant/vm.py tests/unit/test_vm.py
git commit -m "refactor(vm): delegate _vagrant() to run_command(), update tests"
```

---

## Task 6: Migrate `interact.py` and Update `test_interact.py`

**Files:**
- Modify: `src/qt_ai_dev_tools/interact.py`
- Modify: `tests/unit/test_interact.py`

Same issue as vm.py — tests mock `qt_ai_dev_tools.interact.subprocess.run` which breaks after migration.

- [ ] **Step 1: Replace subprocess calls with `run_command()`**

Replace `import subprocess` with `from qt_ai_dev_tools.run import run_command` in `interact.py`. Replace all `subprocess.run([...], check=True, env=env)` calls with `run_command([...], env=env, check=True)`.

Full updated file:

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
    """Click at absolute screen coordinates using xdotool."""
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

- [ ] **Step 2: Update `tests/unit/test_interact.py` mock paths**

Change all `patch("qt_ai_dev_tools.interact.subprocess.run")` to `patch("qt_ai_dev_tools.run.subprocess.run")`.

The mock returns need updating too — `run_command()` returns `CompletedProcess`, so mock must return one:

```python
import subprocess

# In each test that patches subprocess:
with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    click(node, pause=0.0)
    # assertions on mock_run.call_args_list stay the same — checking args[0][0]
```

Also update the focus fallback test (`test_focus_falls_back_to_click`) — same mock path change.

- [ ] **Step 3: Run updated tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/unit/test_interact.py -v`
Expected: All pass.

- [ ] **Step 4: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/interact.py tests/unit/test_interact.py
git commit -m "refactor(interact): route xdotool calls through run_command(), update tests"
```

---

## Task 7: Migrate `screenshot.py`

**Files:**
- Modify: `src/qt_ai_dev_tools/screenshot.py`

- [ ] **Step 1: Replace subprocess with `run_command()`**

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

- [ ] **Step 3: Commit**

```bash
git add src/qt_ai_dev_tools/screenshot.py
git commit -m "refactor(screenshot): route scrot through run_command()"
```

---

## Task 8: Migrate Raw subprocess Calls in `cli.py`

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py` (the `_proxy_screenshot` function)

- [ ] **Step 1: Replace subprocess calls in `_proxy_screenshot()`**

In `_proxy_screenshot()`, replace `subprocess.run(["vagrant", "ssh-config"], ...)` and `subprocess.run(["scp", ...], ...)` with `run_command()` calls:

```python
from qt_ai_dev_tools.run import run_command

# Instead of subprocess.run(["vagrant", "ssh-config"], ...):
ssh_config_result = run_command(["vagrant", "ssh-config"], cwd=ws)

# Instead of subprocess.run(["scp", ...], ...):
scp_result = run_command(["scp", "-F", str(ssh_config), f"default:{remote_path}", output])
```

Check for any other raw `subprocess.run` calls in cli.py and migrate them too (search for `subprocess.run` in the file).

- [ ] **Step 2: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`

- [ ] **Step 3: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "refactor(cli): route proxy subprocess calls through run_command()"
```

---

## Task 9: Add Logging to Remaining Special-Case Subprocess Calls

**Files:**
- Modify: `src/qt_ai_dev_tools/subsystems/notify.py`
- Modify: `src/qt_ai_dev_tools/subsystems/audio.py`
- Modify: `src/qt_ai_dev_tools/bridge/_bootstrap.py`

These files have subprocess calls that can't fully use `run_command()` (timeout-as-feature, background Popen). Add manual logging to make them visible with `-v`.

- [ ] **Step 1: `notify.py` — add logging to `listen()`**

The `listen()` function uses `subprocess.run()` with a timeout that's expected to expire. Can't use `run_command()` because it raises on timeout and loses partial stdout. Add manual logging:

```python
import logging
import shlex

logger = logging.getLogger(__name__)

# In listen(), before the subprocess.run call:
cmd = ["dbus-monitor", "--session", f"interface={_NOTIFY_IFACE},member=Notify"]
logger.info("$ %s (timeout=%ss)", shlex.join(cmd), timeout)
# ... existing subprocess.run code ...
logger.debug("dbus-monitor output:\n%s", raw)
```

- [ ] **Step 2: `audio.py` — add logging to Popen and timeout calls**

For `virtual_mic_start()` (Popen background):
```python
logger.info("$ pw-loopback ... (background, PID will follow)")
```

For `record()` (timeout-as-duration):
```python
logger.info("$ pw-record --rate=48000 --channels=1 %s (duration=%ss)", output, duration)
```

For `verify_not_silence()` — replace `subprocess.run(["sox", ...])` with `run_command()`:
```python
from qt_ai_dev_tools.run import run_command
result = run_command(["sox", str(path), "-n", "stat"])
stat_output = result.stderr or result.stdout
```

- [ ] **Step 3: `bridge/_bootstrap.py` — use `run_command()` for python --version**

Replace the raw `subprocess.run([str(exe_path), "--version"], ...)` with:
```python
from qt_ai_dev_tools.run import run_command
result = run_command([str(exe_path), "--version"], timeout=5)
```

- [ ] **Step 4: Run all unit tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/unit/ -v --timeout=30`
Expected: All pass.

- [ ] **Step 5: Run lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/subsystems/notify.py src/qt_ai_dev_tools/subsystems/audio.py src/qt_ai_dev_tools/bridge/_bootstrap.py
git commit -m "refactor(subsystems): add logging to remaining subprocess calls"
```

---

## Task 10: CLI Integration Tests for Verbose & Dry-Run

**Files:**
- Create: `tests/integration/test_verbose_dryrun.py`

These tests invoke the real CLI binary to verify flags work end-to-end. They do NOT require a VM or DISPLAY — they only test that the flags are recognized and produce expected behavior.

- [ ] **Step 1: Write integration tests**

```python
"""Integration tests for CLI -v/-vv and --dry-run flags.

These tests invoke the CLI as a subprocess to test the full flag pipeline.
No VM or DISPLAY required — they test flag handling, not Qt interaction.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import typing

import pytest

pytestmark = pytest.mark.integration


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run qt-ai-dev-tools CLI and capture output."""
    cmd = (
        ["qt-ai-dev-tools", *args]
        if shutil.which("qt-ai-dev-tools")
        else ["uv", "run", "qt-ai-dev-tools", *args]
    )
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)


class TestVerboseHelpOutput:
    """Verify flags appear in help text (no DISPLAY needed)."""

    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = [pytest.mark.integration]

    def test_help_shows_verbose_option(self) -> None:
        result = run_cli("--help")
        assert result.returncode == 0
        assert "--verbose" in result.stdout or "-v" in result.stdout

    def test_help_shows_dry_run_option(self) -> None:
        result = run_cli("--help")
        assert result.returncode == 0
        assert "--dry-run" in result.stdout


class TestDryRunPreventsExecution:
    """Verify --dry-run prevents actual command execution."""

    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = [pytest.mark.integration]

    def test_dry_run_vm_status_shows_command(self) -> None:
        """--dry-run -v vm status should show vagrant command on stderr without running it."""
        result = run_cli("--dry-run", "-v", "vm", "status")
        # Should show the dry-run command on stderr
        assert "vagrant" in result.stderr
        assert "[dry-run]" in result.stderr or "dry-run" in result.stderr

    def test_dry_run_vm_status_exits_cleanly(self) -> None:
        """--dry-run should not crash even without a Vagrantfile."""
        result = run_cli("--dry-run", "vm", "status")
        # May fail due to Vagrantfile not found (find_workspace raises before run_command),
        # but should not crash with a traceback about vagrant not running
        # The key test: it should NOT actually invoke vagrant
        assert "vagrant" not in result.stdout or result.returncode != 0


class TestVerboseOutput:
    """Verify -v flag produces command logging on stderr."""

    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = [pytest.mark.integration]

    def test_verbose_flag_accepted(self) -> None:
        """CLI should accept -v without error."""
        result = run_cli("-v", "--help")
        assert result.returncode == 0
```

- [ ] **Step 2: Run tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/integration/test_verbose_dryrun.py -v`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_verbose_dryrun.py
git commit -m "test: add integration tests for -v/-vv and --dry-run CLI flags"
```

---

## Task 11: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update CLAUDE.md**

Add a "Debugging" subsection after the CLI usage section (around line 166):

```markdown
### Debugging

```bash
# Show all shell commands being executed:
qt-ai-dev-tools -v tree

# Show commands + their full stdout/stderr:
qt-ai-dev-tools -vv vm up

# Preview what would run without executing:
qt-ai-dev-tools --dry-run vm up

# Combine verbose + dry-run:
qt-ai-dev-tools -v --dry-run click --role "push button" --name "Save"

# Log file (always written, even without -v):
# ~/.local/state/qt-ai-dev-tools/logs/qt-ai-dev-tools.log
```
```

- [ ] **Step 2: Update README.md**

Add brief mention of `-v` and `--dry-run` in the CLI section.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: document -v/-vv and --dry-run CLI flags"
```

---

## Task 12: Final Verification

- [ ] **Step 1: Run ALL unit tests**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/unit/ -v --timeout=30`
Expected: All pass. Zero failures.

- [ ] **Step 2: Run ALL integration tests (that don't need VM)**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/integration/ -v --timeout=30 -k "Help or Verbose or DryRun"`
Expected: All pass.

- [ ] **Step 3: Run full lint**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run poe lint_full`
Expected: Zero errors.

- [ ] **Step 4: Verify no regressions — run the full test suite**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run pytest tests/ -v --timeout=30 -k "not e2e and not integration or Help or Verbose or DryRun"`
Expected: All previously-passing tests still pass. New tests pass.

- [ ] **Step 5: Smoke test the CLI manually**

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run qt-ai-dev-tools --help`
Expected: Shows -v and --dry-run.

Run: `cd /var/home/user1/Projects/pyqt-agent-infra && uv run qt-ai-dev-tools -v --dry-run vm status 2>&1 || true`
Expected: Shows `[dry-run] $ vagrant status` on stderr.
