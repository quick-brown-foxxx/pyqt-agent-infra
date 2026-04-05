"""CLI failure mode tests.

Verify that CLI commands produce useful error messages and correct exit codes
when inputs are invalid or widgets don't exist. These tests need AT-SPI
running (DISPLAY set) but do NOT need the sample app.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="DISPLAY not set -- CLI error tests require AT-SPI",
    ),
]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run qt-ai-dev-tools CLI and capture output.

    Uses `qt-ai-dev-tools` directly if on PATH (VM with pip install -e .),
    falls back to `uv run qt-ai-dev-tools` on host.
    """
    cmd = ["qt-ai-dev-tools", *args] if shutil.which("qt-ai-dev-tools") else ["uv", "run", "qt-ai-dev-tools", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
    )


class TestClickErrors:
    """Click command failure modes."""

    def test_click_no_matching_widget(self) -> None:
        """Click with a name that matches nothing returns non-zero exit."""
        result = run_cli("click", "--role", "push button", "--name", "nonexistent_btn_xyz")
        assert result.returncode != 0
        # Should have a useful error message
        assert "Error" in result.stderr or "error" in result.stderr.lower()

    def test_click_no_args_fails(self) -> None:
        """Click without specifying a target fails."""
        result = run_cli("click")
        assert result.returncode != 0


class TestFindEdgeCases:
    """Find command edge cases."""

    def test_find_no_matching_widget_returns_zero(self) -> None:
        """Find with no matches returns exit 0 -- finding nothing is not an error."""
        result = run_cli("find", "--role", "push button", "--name", "nonexistent_widget_xyz")
        assert result.returncode == 0


class TestScreenshotErrors:
    """Screenshot command failure modes."""

    def test_screenshot_invalid_path(self) -> None:
        """Screenshot to a path that doesn't exist fails."""
        result = run_cli("screenshot", "--output", "/nonexistent_dir_xyz/screenshot.png")
        assert result.returncode != 0


class TestFillErrors:
    """Fill command failure modes."""

    def test_fill_no_matching_widget(self) -> None:
        """Fill into a widget that doesn't exist returns non-zero exit."""
        result = run_cli("fill", "some text", "--role", "text", "--name", "nonexistent_input_xyz")
        assert result.returncode != 0
        assert "Error" in result.stderr or "error" in result.stderr.lower()
