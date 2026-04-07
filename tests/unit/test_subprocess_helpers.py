"""Tests for subprocess helper functions: check_tool() and run_tool()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestCheckTool:
    """Test check_tool() binary lookup via shutil.which."""

    def test_returns_path_when_found(self) -> None:
        """check_tool() should return a Path when the tool exists."""
        from qt_ai_dev_tools.subsystems._subprocess import check_tool

        with patch("qt_ai_dev_tools.subsystems._subprocess.shutil.which", return_value="/usr/bin/xsel"):
            result = check_tool("xsel")

        from pathlib import Path

        assert result == Path("/usr/bin/xsel")

    def test_raises_runtime_error_when_not_found(self) -> None:
        """check_tool() should raise RuntimeError with install hint when tool is missing."""
        from qt_ai_dev_tools.subsystems._subprocess import check_tool

        with (
            patch("qt_ai_dev_tools.subsystems._subprocess.shutil.which", return_value=None),
            pytest.raises(RuntimeError, match="Required tool 'nonexistent'"),
        ):
            check_tool("nonexistent")

    def test_error_message_includes_install_hint(self) -> None:
        """The error message should include an apt-get install suggestion."""
        from qt_ai_dev_tools.subsystems._subprocess import check_tool

        with (
            patch("qt_ai_dev_tools.subsystems._subprocess.shutil.which", return_value=None),
            pytest.raises(RuntimeError, match="apt-get install mytool"),
        ):
            check_tool("mytool")


class TestRunTool:
    """Test run_tool() delegation to run_command()."""

    def test_passes_args_to_run_command(self) -> None:
        """run_tool() should pass args list as first positional arg."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="output")
            run_tool(["xsel", "--clipboard", "--output"])

            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["xsel", "--clipboard", "--output"]

    def test_returns_stdout(self) -> None:
        """run_tool() should return the stdout from run_command()."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="hello world")
            result = run_tool(["echo", "hello", "world"])

        assert result == "hello world"

    def test_passes_input_data(self) -> None:
        """run_tool() should forward input_data to run_command()."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            run_tool(["cat"], input_data="stdin text")

            assert mock_run.call_args[1]["input_data"] == "stdin text"

    def test_passes_timeout(self) -> None:
        """run_tool() should forward timeout to run_command()."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            run_tool(["sleep", "1"], timeout=5.0)

            assert mock_run.call_args[1]["timeout"] == 5.0

    def test_passes_env(self) -> None:
        """run_tool() should forward env dict to run_command()."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        env = {"DISPLAY": ":99", "HOME": "/tmp"}
        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            run_tool(["echo"], env=env)

            assert mock_run.call_args[1]["env"] == env

    def test_passes_check_true(self) -> None:
        """run_tool() must always call run_command with check=True."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            run_tool(["echo"])

            assert mock_run.call_args[1]["check"] is True

    def test_propagates_runtime_error(self) -> None:
        """RuntimeError from run_command should propagate to caller."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with (
            patch(
                "qt_ai_dev_tools.run.run_command",
                side_effect=RuntimeError("Command failed: exit 1"),
            ),
            pytest.raises(RuntimeError, match="Command failed"),
        ):
            run_tool(["false"])

    def test_default_timeout_is_30(self) -> None:
        """Default timeout should be 30 seconds when not specified."""
        from qt_ai_dev_tools.subsystems._subprocess import run_tool

        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            run_tool(["echo"])

            assert mock_run.call_args[1]["timeout"] == 30.0
