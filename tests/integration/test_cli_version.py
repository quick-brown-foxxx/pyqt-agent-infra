"""Integration tests for CLI --version flag."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run qt-ai-dev-tools CLI and capture output."""
    cmd = ["qt-ai-dev-tools", *args] if shutil.which("qt-ai-dev-tools") else ["uv", "run", "qt-ai-dev-tools", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
    )


class TestCLIVersion:
    def test_version_exits_zero(self) -> None:
        result = _run_cli("--version")
        assert result.returncode == 0

    def test_version_contains_semver_pattern(self) -> None:
        result = _run_cli("--version")
        assert re.search(r"\d+\.\d+\.\d+ \(", result.stdout), (
            f"Expected version pattern like '0.6.3 (' in stdout: {result.stdout!r}"
        )

    def test_short_flag_exits_zero(self) -> None:
        result = _run_cli("-V")
        assert result.returncode == 0

    def test_short_flag_matches_long_flag(self) -> None:
        long_result = _run_cli("--version")
        short_result = _run_cli("-V")
        assert long_result.stdout == short_result.stdout
