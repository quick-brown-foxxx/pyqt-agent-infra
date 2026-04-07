"""Tests for screenshot capture via scrot."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestTakeScreenshot:
    """Test take_screenshot() scrot invocation and file handling."""

    def test_calls_scrot_with_overwrite_flag(self, tmp_path: Path) -> None:
        """scrot must be called with --overwrite and the target path."""
        from qt_ai_dev_tools.screenshot import take_screenshot

        out = str(tmp_path) + "/shot.png"
        with (
            patch("qt_ai_dev_tools.screenshot.run_command") as mock_run,
            patch("qt_ai_dev_tools.screenshot.os.path.getsize", return_value=15000),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            take_screenshot(out)

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["scrot", "--overwrite", out]

    def test_sets_display_env_default(self, tmp_path: Path) -> None:
        """DISPLAY=:99 should be set when no DISPLAY is in environ."""
        from qt_ai_dev_tools.screenshot import take_screenshot

        out = str(tmp_path) + "/shot.png"
        with (
            patch("qt_ai_dev_tools.screenshot.run_command") as mock_run,
            patch("qt_ai_dev_tools.screenshot.os.path.getsize", return_value=15000),
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            take_screenshot(out)

            env_arg = mock_run.call_args[1]["env"]
            assert env_arg["DISPLAY"] == ":99"

    def test_preserves_existing_display(self, tmp_path: Path) -> None:
        """Existing DISPLAY value should be preserved (setdefault behavior)."""
        from qt_ai_dev_tools.screenshot import take_screenshot

        out = str(tmp_path) + "/shot.png"
        with (
            patch("qt_ai_dev_tools.screenshot.run_command") as mock_run,
            patch("qt_ai_dev_tools.screenshot.os.path.getsize", return_value=15000),
            patch.dict("os.environ", {"DISPLAY": ":0"}, clear=True),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            take_screenshot(out)

            env_arg = mock_run.call_args[1]["env"]
            assert env_arg["DISPLAY"] == ":0"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Parent directory should be created if it doesn't exist."""
        from qt_ai_dev_tools.screenshot import take_screenshot

        out = str(tmp_path) + "/nested/dir/shot.png"
        with (
            patch("qt_ai_dev_tools.screenshot.run_command") as mock_run,
            patch("qt_ai_dev_tools.screenshot.os.path.getsize", return_value=15000),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            take_screenshot(out)

        import os

        assert os.path.isdir(str(tmp_path) + "/nested/dir")

    def test_returns_path(self, tmp_path: Path) -> None:
        """take_screenshot() should return the path to the screenshot."""
        from qt_ai_dev_tools.screenshot import take_screenshot

        out = str(tmp_path) + "/shot.png"
        with (
            patch("qt_ai_dev_tools.screenshot.run_command") as mock_run,
            patch("qt_ai_dev_tools.screenshot.os.path.getsize", return_value=15000),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = take_screenshot(out)

        assert result == out

    def test_propagates_runtime_error_on_scrot_failure(self, tmp_path: Path) -> None:
        """RuntimeError from run_command (check=True) should propagate."""
        from qt_ai_dev_tools.screenshot import take_screenshot

        out = str(tmp_path) + "/shot.png"
        with (
            patch(
                "qt_ai_dev_tools.screenshot.run_command",
                side_effect=RuntimeError("Command failed: scrot"),
            ),
            pytest.raises(RuntimeError, match="Command failed"),
        ):
            take_screenshot(out)

    def test_passes_check_true(self, tmp_path: Path) -> None:
        """run_command must be called with check=True."""
        from qt_ai_dev_tools.screenshot import take_screenshot

        out = str(tmp_path) + "/shot.png"
        with (
            patch("qt_ai_dev_tools.screenshot.run_command") as mock_run,
            patch("qt_ai_dev_tools.screenshot.os.path.getsize", return_value=15000),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            take_screenshot(out)

            assert mock_run.call_args[1]["check"] is True
