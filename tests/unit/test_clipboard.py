"""Tests for clipboard subsystem — xsel and xclip code paths."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestXselWrite:
    """Tests for write() when xsel is available (preferred path)."""

    def test_write_calls_xsel_with_correct_args(self) -> None:
        """write() should invoke xsel --clipboard --input and pass text on stdin."""
        from qt_ai_dev_tools.subsystems.clipboard import write

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=True),
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool") as mock_check,
            patch("qt_ai_dev_tools.subsystems.clipboard.run_tool") as mock_run,
        ):
            write("hello world")

            mock_check.assert_called_once_with("xsel")
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["xsel", "--clipboard", "--input"]
            assert args[1]["input_data"] == "hello world"

    def test_write_passes_env(self) -> None:
        """write() should pass clipboard env to run_tool."""
        from qt_ai_dev_tools.subsystems.clipboard import write

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=True),
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool"),
            patch("qt_ai_dev_tools.subsystems.clipboard.run_tool") as mock_run,
            patch.dict("os.environ", {"DISPLAY": ":0"}, clear=True),
        ):
            write("test")

            env_arg = mock_run.call_args[1]["env"]
            assert env_arg["DISPLAY"] == ":0"


class TestXclipWrite:
    """Tests for write() when xsel is NOT available (xclip fallback)."""

    def test_write_calls_xclip_with_correct_args(self) -> None:
        """write() should invoke xclip with -selection clipboard -l 0."""
        from qt_ai_dev_tools.subsystems.clipboard import write

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=False),
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool") as mock_check,
            patch("qt_ai_dev_tools.subsystems.clipboard.run_tool") as mock_run,
        ):
            write("hello world")

            mock_check.assert_called_once_with("xclip")
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["xclip", "-selection", "clipboard", "-l", "0"]
            assert args[1]["input_data"] == "hello world"
            assert args[1]["timeout"] == 5.0

    def test_write_raises_on_missing_xclip(self) -> None:
        """write() should raise RuntimeError when xclip is not installed."""
        from qt_ai_dev_tools.subsystems.clipboard import write

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=False),
            patch(
                "qt_ai_dev_tools.subsystems.clipboard.check_tool",
                side_effect=RuntimeError("not found"),
            ),
            pytest.raises(RuntimeError, match="not found"),
        ):
            write("test")


class TestXselRead:
    """Tests for read() when xsel is available (preferred path)."""

    def test_read_calls_xsel_with_correct_args(self) -> None:
        """read() should invoke xsel --clipboard --output."""
        from qt_ai_dev_tools.subsystems.clipboard import read

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=True),
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool") as mock_check,
            patch(
                "qt_ai_dev_tools.subsystems.clipboard.run_tool",
                return_value="clipboard text",
            ) as mock_run,
        ):
            result = read()

            assert result == "clipboard text"
            mock_check.assert_called_once_with("xsel")
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["xsel", "--clipboard", "--output"]

    def test_read_passes_env(self) -> None:
        """read() should pass clipboard env to run_tool."""
        from qt_ai_dev_tools.subsystems.clipboard import read

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=True),
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool"),
            patch(
                "qt_ai_dev_tools.subsystems.clipboard.run_tool",
                return_value="text",
            ) as mock_run,
            patch.dict("os.environ", {"DISPLAY": ":0"}, clear=True),
        ):
            read()

            env_arg = mock_run.call_args[1]["env"]
            assert env_arg["DISPLAY"] == ":0"


class TestXclipRead:
    """Tests for read() when xsel is NOT available (xclip fallback)."""

    def test_read_calls_xclip_with_correct_args(self) -> None:
        """read() should invoke xclip -selection clipboard -o."""
        from qt_ai_dev_tools.subsystems.clipboard import read

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=False),
            patch("qt_ai_dev_tools.subsystems.clipboard.check_tool") as mock_check,
            patch(
                "qt_ai_dev_tools.subsystems.clipboard.run_tool",
                return_value="xclip text",
            ) as mock_run,
        ):
            result = read()

            assert result == "xclip text"
            mock_check.assert_called_once_with("xclip")
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["xclip", "-selection", "clipboard", "-o"]

    def test_read_raises_on_missing_xclip(self) -> None:
        """read() should raise RuntimeError when xclip is not installed."""
        from qt_ai_dev_tools.subsystems.clipboard import read

        with (
            patch("qt_ai_dev_tools.subsystems.clipboard._use_xsel", return_value=False),
            patch(
                "qt_ai_dev_tools.subsystems.clipboard.check_tool",
                side_effect=RuntimeError("not found"),
            ),
            pytest.raises(RuntimeError, match="not found"),
        ):
            read()


class TestUseXsel:
    """Tests for _use_xsel() tool detection."""

    def test_returns_true_when_xsel_available(self) -> None:
        """_use_xsel() should return True when shutil.which finds xsel."""
        from qt_ai_dev_tools.subsystems.clipboard import _use_xsel

        with patch("qt_ai_dev_tools.subsystems.clipboard.shutil.which", return_value="/usr/bin/xsel"):
            assert _use_xsel() is True

    def test_returns_false_when_xsel_missing(self) -> None:
        """_use_xsel() should return False when shutil.which returns None."""
        from qt_ai_dev_tools.subsystems.clipboard import _use_xsel

        with patch("qt_ai_dev_tools.subsystems.clipboard.shutil.which", return_value=None):
            assert _use_xsel() is False


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
