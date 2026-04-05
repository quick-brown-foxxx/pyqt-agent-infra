"""Tests for VM management functions."""

from __future__ import annotations

import subprocess as _subprocess
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import pytest

from qt_ai_dev_tools.vagrant.vm import (
    _vagrant,
    find_workspace,
    vm_destroy,
    vm_run,
    vm_status,
    vm_sync,
    vm_sync_auto,
    vm_up,
)

pytestmark = pytest.mark.unit


class TestFindWorkspace:
    def test_explicit_path_with_vagrantfile(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        result = find_workspace(tmp_path)
        assert result == tmp_path

    def test_explicit_path_without_vagrantfile_raises(self, tmp_path: Path) -> None:
        import pytest

        with pytest.raises(FileNotFoundError, match="No Vagrantfile found in"):
            find_workspace(tmp_path)

    def test_walks_up_to_find_vagrantfile(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        nested = tmp_path / "sub" / "deep"
        nested.mkdir(parents=True)
        with patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=nested):
            result = find_workspace()
        assert result == tmp_path

    def test_no_vagrantfile_anywhere_raises(self, tmp_path: Path) -> None:
        import pytest

        nested = tmp_path / "empty" / "dir"
        nested.mkdir(parents=True)
        with (
            patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=nested),
            pytest.raises(FileNotFoundError, match="No Vagrantfile found in current directory or parents"),
        ):
            find_workspace()


class TestVagrant:
    def test_vagrant_helper_calls_subprocess(self, tmp_path: Path) -> None:
        with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=["vagrant", "status"], returncode=0, stdout="", stderr=""
            )
            _vagrant(["status"], tmp_path)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["vagrant", "status"]
            assert call_args[1]["cwd"] == tmp_path


class TestVmUp:
    def test_calls_vagrant_up_with_provider(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=["vagrant", "up", "--provider=libvirt"], returncode=0, stdout="", stderr=""
            )
            vm_up(tmp_path)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["vagrant", "up", "--provider=libvirt"]
            assert call_args[1]["cwd"] == tmp_path


class TestVmStatus:
    def test_calls_vagrant_status(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=["vagrant", "status"], returncode=0, stdout="", stderr=""
            )
            vm_status(tmp_path)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["vagrant", "status"]
            assert call_args[1]["cwd"] == tmp_path


class TestVmDestroy:
    def test_calls_vagrant_destroy_force(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=["vagrant", "destroy", "-f"], returncode=0, stdout="", stderr=""
            )
            vm_destroy(tmp_path)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["vagrant", "destroy", "-f"]
            assert call_args[1]["cwd"] == tmp_path


class TestVmSync:
    def test_calls_vagrant_rsync(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=["vagrant", "rsync"], returncode=0, stdout="", stderr=""
            )
            vm_sync(tmp_path)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["vagrant", "rsync"]
            assert call_args[1]["cwd"] == tmp_path


class TestVmRun:
    def test_vagrant_ssh_with_env_prefix(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()

        with patch("qt_ai_dev_tools.run.subprocess.run") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=["vagrant", "ssh", "-c", "..."], returncode=0, stdout="output", stderr=""
            )
            vm_run("echo hello", tmp_path)
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "vagrant"
            assert cmd[1] == "ssh"
            assert cmd[2] == "-c"
            assert "DISPLAY=:99" in cmd[3]
            assert "QT_AI_DEV_TOOLS_VM=1" in cmd[3]
            assert "echo hello" in cmd[3]


class TestVmSyncAuto:
    def test_starts_rsync_auto_process(self, tmp_path: Path) -> None:
        vagrantfile = tmp_path / "Vagrantfile"
        vagrantfile.touch()
        with mock.patch("qt_ai_dev_tools.vagrant.vm.subprocess.Popen") as mock_popen:
            vm_sync_auto(tmp_path)
            mock_popen.assert_called_once()
            args = mock_popen.call_args
            assert args[0][0] == ["vagrant", "rsync-auto"]
            assert args[1]["cwd"] == tmp_path
