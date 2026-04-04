"""Tests for Vagrant workspace template rendering."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from qt_ai_dev_tools.vagrant.workspace import (
    WorkspaceConfig,
    default_config,
    render_workspace,
)

pytestmark = pytest.mark.unit


class TestDefaultConfig:
    def test_returns_expected_defaults(self) -> None:
        config = default_config()
        assert config.box == "bento/ubuntu-24.04"
        assert config.hostname == "qt-dev"
        assert config.provider == "libvirt"
        assert config.memory == 4096
        assert config.cpus == 4
        assert config.mac_address == "52:54:00:AB:CD:EF"
        assert config.static_ip == ""
        assert config.shared_folder == "."
        assert config.rsync_excludes == [".git/", ".vagrant/"]
        assert config.display == ":99"
        assert config.resolution == "1920x1080x24"
        assert config.extra_packages == []
        assert config.python_packages == ["PySide6", "pytest", "pytest-qt", "python-dbusmock"]


class TestRenderWorkspace:
    def test_creates_all_files(self, tmp_path: Path) -> None:
        created = render_workspace(tmp_path)
        assert len(created) == 2
        assert (tmp_path / "Vagrantfile").is_file()
        assert (tmp_path / "provision.sh").is_file()

    def test_vagrantfile_contains_defaults(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "Vagrantfile").read_text()
        assert '"bento/ubuntu-24.04"' in content
        assert "v.memory = 4096" in content
        assert "v.cpus = 4" in content
        assert 'config.vm.hostname = "qt-dev"' in content

    def test_provision_contains_defaults(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "DISPLAY=:99" in content
        assert "1920x1080x24" in content
        assert "PySide6" in content

    def test_shell_scripts_are_executable(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        mode = (tmp_path / "provision.sh").stat().st_mode
        assert mode & stat.S_IXUSR, "provision.sh should be user-executable"
        assert mode & stat.S_IXGRP, "provision.sh should be group-executable"
        assert mode & stat.S_IXOTH, "provision.sh should be other-executable"

    def test_vagrantfile_not_executable(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        mode = (tmp_path / "Vagrantfile").stat().st_mode
        assert not (mode & stat.S_IXUSR), "Vagrantfile should not be executable"

    def test_custom_config_memory(self, tmp_path: Path) -> None:
        config = WorkspaceConfig(memory=8192)
        render_workspace(tmp_path, config=config)
        content = (tmp_path / "Vagrantfile").read_text()
        assert "v.memory = 8192" in content

    def test_custom_config_extra_packages(self, tmp_path: Path) -> None:
        config = WorkspaceConfig(extra_packages=["vim", "htop"])
        render_workspace(tmp_path, config=config)
        content = (tmp_path / "provision.sh").read_text()
        assert "vim" in content
        assert "htop" in content

    def test_custom_display(self, tmp_path: Path) -> None:
        config = WorkspaceConfig(display=":42")
        render_workspace(tmp_path, config=config)
        provision = (tmp_path / "provision.sh").read_text()
        assert "DISPLAY=:42" in provision

    def test_returns_created_paths(self, tmp_path: Path) -> None:
        created = render_workspace(tmp_path)
        expected = {
            tmp_path / "Vagrantfile",
            tmp_path / "provision.sh",
        }
        assert set(created) == expected

    def test_vagrantfile_contains_virtualbox_provider(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "Vagrantfile").read_text()
        assert 'config.vm.provider "virtualbox"' in content
        assert "v.gui = false" in content
        assert '--audio", "none"' in content

    def test_vagrantfile_contains_libvirt_provider(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "Vagrantfile").read_text()
        assert 'config.vm.provider "libvirt"' in content

    def test_static_ip_present_when_set(self, tmp_path: Path) -> None:
        config = WorkspaceConfig(static_ip="192.168.121.100")
        render_workspace(tmp_path, config=config)
        content = (tmp_path / "Vagrantfile").read_text()
        assert 'config.vm.network "private_network", ip: "192.168.121.100"' in content

    def test_static_ip_absent_when_empty(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "Vagrantfile").read_text()
        assert "private_network" not in content
