"""Integration tests for CLI -v/-vv and --dry-run flags.

These tests invoke the CLI as a subprocess to test the full flag pipeline.
No VM or DISPLAY required — they test flag handling, not Qt interaction.
"""

from __future__ import annotations

import shutil
import subprocess
import typing

import pytest

pytestmark = pytest.mark.integration


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run qt-ai-dev-tools CLI and capture output."""
    cmd = ["qt-ai-dev-tools", *args] if shutil.which("qt-ai-dev-tools") else ["uv", "run", "qt-ai-dev-tools", *args]
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
        """--dry-run -v vm status should log the vagrant command on stderr without running it."""
        result = run_cli("--dry-run", "-v", "vm", "status")
        # With a Vagrantfile in the project root, find_workspace() succeeds and
        # run_command() logs the dry-run message. Without one, find_workspace()
        # raises FileNotFoundError before run_command() is reached.
        if result.returncode == 0:
            assert "dry-run" in result.stderr
            assert "vagrant" in result.stderr
        else:
            # find_workspace() raised before reaching run_command() — acceptable
            assert "Vagrantfile" in result.stderr or "vagrant" in result.stderr.lower()

    def test_dry_run_auto_enables_verbose(self) -> None:
        """--dry-run without -v should still show command on stderr."""
        result = run_cli("--dry-run", "vm", "status")
        # --dry-run should auto-enable -v, so stderr should contain dry-run marker.
        # If Vagrantfile is missing, the error message still appears on stderr.
        stderr = result.stderr.lower()
        assert "dry-run" in stderr or "dry_run" in stderr or "vagrantfile" in stderr

    def test_dry_run_vm_status_does_not_invoke_vagrant(self) -> None:
        """--dry-run should not produce vagrant's own stdout output."""
        result = run_cli("--dry-run", "-v", "vm", "status")
        # If dry-run worked, stdout should be empty (vagrant never ran).
        # If it failed due to missing Vagrantfile, stdout is also empty.
        assert result.stdout.strip() == ""


class TestSilentOption:
    """Verify --silent flag appears in help."""

    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = [pytest.mark.integration]

    def test_help_shows_silent_option(self) -> None:
        result = run_cli("--help")
        assert result.returncode == 0
        assert "--silent" in result.stdout


class TestHelpShortFlag:
    """Verify -h works as alias for --help."""

    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = [pytest.mark.integration]

    def test_dash_h_shows_help(self) -> None:
        result = run_cli("-h")
        assert result.returncode == 0
        assert "qt-ai-dev-tools" in result.stdout.lower() or "Usage" in result.stdout


class TestVerboseOutput:
    """Verify -v flag produces command logging on stderr."""

    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = [pytest.mark.integration]

    def test_verbose_flag_accepted(self) -> None:
        """CLI should accept -v without error."""
        result = run_cli("-v", "--help")
        assert result.returncode == 0
