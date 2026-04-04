"""Tests for clipboard subsystem."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestClipboardWrite:
    def test_write_calls_xclip_with_correct_args(self) -> None:
        """write() should invoke xclip with selection clipboard and pass text on stdin."""
        from qt_ai_dev_tools.subsystems.clipboard import write

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool") as mock_check,
            patch("qt_ai_dev_tools.subsystems.clipboard.run_tool") as mock_run,
        ):
            mock_check.return_value = "/usr/bin/xclip"
            write("hello world")

            mock_check.assert_called_once_with("xclip")
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["xclip", "-selection", "clipboard"]
            assert args[1]["input_data"] == "hello world"

    def test_write_raises_on_missing_tool(self) -> None:
        """write() should raise RuntimeError when xclip is not installed."""
        from qt_ai_dev_tools.subsystems.clipboard import write

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool", side_effect=RuntimeError("not found")),
            pytest.raises(RuntimeError, match="not found"),
        ):
            write("test")


class TestClipboardRead:
    def test_read_returns_clipboard_content(self) -> None:
        """read() should return text from xclip stdout."""
        from qt_ai_dev_tools.subsystems.clipboard import read

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool") as mock_check,
            patch("qt_ai_dev_tools.subsystems.clipboard.run_tool", return_value="clipboard text") as mock_run,
        ):
            mock_check.return_value = "/usr/bin/xclip"
            result = read()

            assert result == "clipboard text"
            mock_check.assert_called_once_with("xclip")
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["xclip", "-selection", "clipboard", "-o"]

    def test_read_raises_on_missing_tool(self) -> None:
        """read() should raise RuntimeError when xclip is not installed."""
        from qt_ai_dev_tools.subsystems.clipboard import read

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool", side_effect=RuntimeError("not found")),
            pytest.raises(RuntimeError, match="not found"),
        ):
            read()


class TestClipboardEnv:
    def test_env_sets_display_default(self) -> None:
        """_clipboard_env() should set DISPLAY=:99 by default."""
        from qt_ai_dev_tools.subsystems.clipboard import _clipboard_env

        with patch.dict("os.environ", {}, clear=True):
            env = _clipboard_env()
            assert env["DISPLAY"] == ":99"

    def test_env_preserves_existing_display(self) -> None:
        """_clipboard_env() should use existing DISPLAY if set."""
        from qt_ai_dev_tools.subsystems.clipboard import _clipboard_env

        with patch.dict("os.environ", {"DISPLAY": ":0"}, clear=True):
            env = _clipboard_env()
            assert env["DISPLAY"] == ":0"
