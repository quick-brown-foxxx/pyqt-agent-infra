"""Integration tests for the qt-ai-dev-tools CLI.

These tests require a running Qt app with AT-SPI available (DISPLAY set).
Run inside the Vagrant VM with `make test-full`.
"""

import json
import os
import shutil
import subprocess
import typing

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="DISPLAY not set — CLI tests require AT-SPI",
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


class TestCLIHelp:
    """CLI help renders without errors (no AT-SPI needed)."""

    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = []  # Override module-level skipif

    def test_main_help(self) -> None:
        result = run_cli("--help")
        assert result.returncode == 0
        assert "tree" in result.stdout
        assert "click" in result.stdout

    def test_tree_help(self) -> None:
        result = run_cli("tree", "--help")
        assert result.returncode == 0
        assert "--role" in result.stdout
        assert "--json" in result.stdout

    def test_click_help(self) -> None:
        result = run_cli("click", "--help")
        assert result.returncode == 0
        assert "--role" in result.stdout

    def test_screenshot_help(self) -> None:
        result = run_cli("screenshot", "--help")
        assert result.returncode == 0
        assert "--output" in result.stdout


class TestCLIApps:
    def test_apps_lists_something(self) -> None:
        result = run_cli("apps")
        assert result.returncode == 0

    def test_apps_json(self) -> None:
        result = run_cli("apps", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)


class TestCLITree:
    def test_tree_default(self) -> None:
        result = run_cli("tree")
        assert result.returncode == 0
        assert "[" in result.stdout  # role markers like [frame]

    def test_tree_with_role_filter(self) -> None:
        result = run_cli("tree", "--role", "push button")
        assert result.returncode == 0

    def test_tree_with_role_json(self) -> None:
        result = run_cli("tree", "--role", "push button", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)


class TestCLIFind:
    def test_find_by_role(self) -> None:
        result = run_cli("find", "--role", "push button", "--app", "main.py")
        assert result.returncode == 0
        assert "push button" in result.stdout

    def test_find_no_args_fails(self) -> None:
        result = run_cli("find")
        assert result.returncode != 0

    def test_find_json(self) -> None:
        result = run_cli("find", "--role", "label", "--json", "--app", "main.py")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "role" in data[0]


class TestCLIScreenshot:
    def test_screenshot_default(self) -> None:
        result = run_cli("screenshot")
        assert result.returncode == 0
        assert ".png" in result.stdout
