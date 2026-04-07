"""Tests for VM management functions.

Tests focus on real logic: filesystem workspace discovery and env string
construction. Tautological tests (assert subprocess was called with args)
have been removed.
"""

from __future__ import annotations

import subprocess as _subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from qt_ai_dev_tools.vagrant.vm import (
    find_workspace,
    vm_run,
)

pytestmark = pytest.mark.unit


class TestFindWorkspace:
    def test_explicit_path_with_vagrantfile(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        result = find_workspace(tmp_path)
        assert result == tmp_path

    def test_explicit_path_without_vagrantfile_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No Vagrantfile found in"):
            find_workspace(tmp_path)

    def test_walks_up_to_find_vagrantfile(self, tmp_path: Path) -> None:
        ws_dir = tmp_path / ".qt-ai-dev-tools"
        ws_dir.mkdir()
        (ws_dir / "Vagrantfile").touch()
        nested = tmp_path / "sub" / "deep"
        nested.mkdir(parents=True)
        with patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=nested):
            result = find_workspace()
        assert result == ws_dir

    def test_no_vagrantfile_anywhere_raises(self, tmp_path: Path) -> None:
        nested = tmp_path / "empty" / "dir"
        nested.mkdir(parents=True)
        with (
            patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=nested),
            pytest.raises(FileNotFoundError, match=r"No \.qt-ai-dev-tools/Vagrantfile found"),
        ):
            find_workspace()

    def test_finds_vagrantfile_in_parent_not_grandparent(self, tmp_path: Path) -> None:
        """Vagrantfile in parent/.qt-ai-dev-tools/ should be found from parent/child/."""
        parent = tmp_path / "parent"
        parent.mkdir()
        ws_dir = parent / ".qt-ai-dev-tools"
        ws_dir.mkdir()
        (ws_dir / "Vagrantfile").touch()
        child = parent / "child"
        child.mkdir()

        # Should find .qt-ai-dev-tools/Vagrantfile in parent/, not grandparent
        with patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=child):
            result = find_workspace()
        assert result == ws_dir


class TestVmRunEnvConstruction:
    """Tests that vm_run builds the correct env-prefix + command string.

    These test real string-building logic, not subprocess invocation.
    """

    def _get_ssh_command(self, command: str, **kwargs: object) -> str:
        """Run vm_run with mocked subprocess and return the SSH -c argument."""
        tmp_path = kwargs.pop("workspace", None)
        if tmp_path is None:
            msg = "workspace is required"
            raise ValueError(msg)

        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=["vagrant", "ssh", "-c", "..."],
                returncode=0,
                stdout="",
                stderr="",
            )
            vm_run(command, tmp_path, **kwargs)  # type: ignore[arg-type]  # rationale: test helper passes dynamic kwargs
            return mock_run.call_args[0][0][3]  # type: ignore[no-any-return]  # rationale: mock call_args is untyped

    def test_env_contains_required_variables(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        ssh_cmd = self._get_ssh_command("echo hello", workspace=tmp_path)

        assert "DISPLAY=:99" in ssh_cmd
        assert "QT_QPA_PLATFORM=xcb" in ssh_cmd
        assert "QT_ACCESSIBILITY=1" in ssh_cmd
        assert "QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1" in ssh_cmd
        assert "QT_AI_DEV_TOOLS_VM=1" in ssh_cmd
        assert "UV_PROJECT_ENVIRONMENT=$HOME/.venv-qt-ai-dev-tools" in ssh_cmd
        assert "DBUS_SESSION_BUS_ADDRESS=" in ssh_cmd

    def test_custom_display_parameter(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        ssh_cmd = self._get_ssh_command("echo hello", workspace=tmp_path, display=":42")

        assert "DISPLAY=:42" in ssh_cmd
        assert "DISPLAY=:99" not in ssh_cmd

    def test_preserves_user_command_intact(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        complex_cmd = 'cd /vagrant && uv run pytest tests/ -v -k "test_foo"'
        ssh_cmd = self._get_ssh_command(complex_cmd, workspace=tmp_path)

        assert ssh_cmd.endswith(complex_cmd)

    def test_invalid_display_raises_value_error(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        with pytest.raises(ValueError, match="Invalid display format"):
            vm_run("echo hello", tmp_path, display="bad")
