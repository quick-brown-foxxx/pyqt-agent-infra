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
