"""Tests for Vagrant workspace template rendering."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from qt_ai_dev_tools.vagrant.workspace import (
    WorkspaceConfig,
    default_config,
    derive_vm_name,
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
        assert config.mac_address == ""
        assert config.static_ip == ""
        assert config.shared_folder == "../"
        assert config.rsync_excludes == [".git/", ".vagrant/", ".venv/"]
        assert config.display == ":99"
        assert config.resolution == "1920x1080x24"
        assert config.extra_packages == []
        assert config.python_packages == ["basedpyright"]
        assert config.vm_name == ""


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
        assert "basedpyright" in content

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

    def test_vm_name_auto_derived_from_target(self, tmp_path: Path) -> None:
        workspace = tmp_path / "my-cool-project" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        render_workspace(workspace)
        content = (workspace / "Vagrantfile").read_text()
        assert 'v.default_prefix = "qt-dev-my-cool-project"' in content
        assert 'v.name = "qt-dev-my-cool-project"' in content

    def test_vm_name_explicit_override(self, tmp_path: Path) -> None:
        config = WorkspaceConfig(vm_name="my-custom-vm")
        render_workspace(tmp_path, config=config)
        content = (tmp_path / "Vagrantfile").read_text()
        assert 'v.default_prefix = "my-custom-vm"' in content
        assert 'v.name = "my-custom-vm"' in content

    def test_vm_name_in_both_providers(self, tmp_path: Path) -> None:
        config = WorkspaceConfig(vm_name="test-vm")
        render_workspace(tmp_path, config=config)
        content = (tmp_path / "Vagrantfile").read_text()
        # libvirt uses default_prefix
        assert 'v.default_prefix = "test-vm"' in content
        # virtualbox uses v.name
        assert 'v.name = "test-vm"' in content

    def test_provision_contains_pinned_version(self, tmp_path: Path) -> None:
        from qt_ai_dev_tools.__version__ import __version__

        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert f"qt-ai-dev-tools=={__version__}" in content

    def test_provision_does_not_contain_uv_sync(self, tmp_path: Path) -> None:
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "uv sync" not in content


class TestDeriveVmName:
    def test_simple_directory_name(self, tmp_path: Path) -> None:
        workspace = tmp_path / "my-project" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-my-project"

    def test_directory_with_special_chars(self, tmp_path: Path) -> None:
        workspace = tmp_path / "My Cool_Project!" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-my-cool-project"

    def test_directory_with_dots(self, tmp_path: Path) -> None:
        workspace = tmp_path / "project.v2.0" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-project-v2-0"

    def test_directory_with_unicode(self, tmp_path: Path) -> None:
        workspace = tmp_path / "projet-café" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-projet-caf"

    def test_empty_after_sanitize_falls_back_to_default(self, tmp_path: Path) -> None:
        workspace = tmp_path / "..." / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-default"

    def test_uppercase_lowercased(self, tmp_path: Path) -> None:
        workspace = tmp_path / "MyProject" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-myproject"

    def test_consecutive_special_chars_collapsed(self, tmp_path: Path) -> None:
        workspace = tmp_path / "a---b___c" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-a-b-c"

    def test_leading_trailing_special_chars_stripped(self, tmp_path: Path) -> None:
        workspace = tmp_path / "--project--" / ".qt-ai-dev-tools"
        workspace.mkdir(parents=True)
        assert derive_vm_name(workspace) == "qt-dev-project"


class TestProvisionUvToolInstall:
    """Tests for uv tool install provisioning (replaces uv sync)."""

    def test_provision_does_not_contain_uv_sync(self, tmp_path: Path) -> None:
        """provision.sh must not contain 'uv sync'."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "uv sync" not in content

    def test_provision_contains_uv_tool_install_pypi(self, tmp_path: Path) -> None:
        """provision.sh must contain pinned 'uv tool install qt-ai-dev-tools==<version>' for PyPI path."""
        from qt_ai_dev_tools.__version__ import __version__

        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert f"uv tool install 'qt-ai-dev-tools=={__version__}'" in content

    def test_provision_contains_install_and_own_detection(self, tmp_path: Path) -> None:
        """provision.sh must detect local install-and-own copy."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "/vagrant/.qt-ai-dev-tools/src/qt_ai_dev_tools" in content

    def test_provision_contains_uv_tool_install_local(self, tmp_path: Path) -> None:
        """provision.sh must use 'uv tool install --force' for local copy."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "uv tool install --force" in content

    def test_provision_gi_linking_uses_tool_venv(self, tmp_path: Path) -> None:
        """gi/pygobject linking must target the uv tool venv, not project venv."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert ".local/share/uv/tools/qt-ai-dev-tools" in content
        assert ".venv-qt-ai-dev-tools" not in content

    def test_provision_bashrc_no_uv_project_environment(self, tmp_path: Path) -> None:
        """provision.sh .bashrc block must not export UV_PROJECT_ENVIRONMENT."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert "UV_PROJECT_ENVIRONMENT" not in content

    def test_provision_bashrc_has_local_bin_in_path(self, tmp_path: Path) -> None:
        """provision.sh .bashrc block must add ~/.local/bin to PATH."""
        render_workspace(tmp_path)
        content = (tmp_path / "provision.sh").read_text()
        assert ".local/bin" in content
