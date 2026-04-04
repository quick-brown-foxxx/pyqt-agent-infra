"""Tests for Vagrant workspace template rendering."""

from __future__ import annotations

import stat
from pathlib import Path

from qt_ai_dev_tools.vagrant.workspace import (
    WorkspaceConfig,
    default_config,
    render_workspace,
)


class TestDefaultConfig:
    def test_returns_expected_defaults(self) -> None:
        config = default_config()
        assert config.box == "bento/ubuntu-24.04"
        assert config.hostname == "qt-dev"
        assert config.provider == "libvirt"
        assert config.memory == 4096
        assert config.cpus == 4
        assert config.mac_address == "52:54:00:AB:CD:EF"
        assert config.shared_folder == "."
        assert config.rsync_excludes == [".git/", ".vagrant/"]
        assert config.display == ":99"
        assert config.resolution == "1920x1080x24"
        assert config.extra_packages == []
        assert config.python_packages == ["PySide6", "pytest", "pytest-qt", "python-dbusmock"]


class TestRenderWorkspace:
    def test_creates_all_four_files(self, tmp_path: Path) -> None:
        created = render_workspace(tmp_path)
        assert len(created) == 4
        assert (tmp_path / "Vagrantfile").is_file()
        assert (tmp_path / "provision.sh").is_file()
        assert (tmp_path / "scripts" / "vm-run.sh").is_file()
        assert (tmp_path / "scripts" / "screenshot.sh").is_file()

    def test_scripts_subdirectory_created(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        assert (tmp_path / "scripts").is_dir()

    def test_vagrantfile_contains_defaults(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "Vagrantfile").read_text()
        assert '"bento/ubuntu-24.04"' in content
        assert "v.memory = 4096" in content
        assert "v.cpus   = 4" in content
        assert 'config.vm.hostname = "qt-dev"' in content

    def test_provision_contains_defaults(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "DISPLAY=:99" in content
        assert "1920x1080x24" in content
        assert "PySide6" in content

    def test_vm_run_contains_display(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "scripts" / "vm-run.sh").read_text()
        assert "DISPLAY=:99" in content

    def test_screenshot_contains_display(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "scripts" / "screenshot.sh").read_text()
        assert "DISPLAY=:99" in content

    def test_shell_scripts_are_executable(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        for script in ["provision.sh", "scripts/vm-run.sh", "scripts/screenshot.sh"]:
            mode = (tmp_path / script).stat().st_mode
            assert mode & stat.S_IXUSR, f"{script} should be user-executable"
            assert mode & stat.S_IXGRP, f"{script} should be group-executable"
            assert mode & stat.S_IXOTH, f"{script} should be other-executable"

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
        vm_run = (tmp_path / "scripts" / "vm-run.sh").read_text()
        screenshot = (tmp_path / "scripts" / "screenshot.sh").read_text()
        provision = (tmp_path / "provision.sh").read_text()
        assert "DISPLAY=:42" in vm_run
        assert "DISPLAY=:42" in screenshot
        assert "DISPLAY=:42" in provision

    def test_returns_created_paths(self, tmp_path: Path) -> None:
        created = render_workspace(tmp_path)
        expected = {
            tmp_path / "Vagrantfile",
            tmp_path / "provision.sh",
            tmp_path / "scripts" / "vm-run.sh",
            tmp_path / "scripts" / "screenshot.sh",
        }
        assert set(created) == expected
