"""Tests for shadcn-style installer (install_and_own, self_update)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestInstallAndOwn:
    """Tests for install_and_own() — full install into a target directory."""

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        """install_and_own should create src/, templates/, skills/, notes/ dirs."""
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        assert (tmp_path / "src").is_dir()
        assert (tmp_path / "templates").is_dir()
        assert (tmp_path / "skills").is_dir()
        assert (tmp_path / "notes").is_dir()

    def test_copies_package_source(self, tmp_path: Path) -> None:
        """install_and_own should copy qt_ai_dev_tools package into src/."""
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        pkg_dir = tmp_path / "src" / "qt_ai_dev_tools"
        assert pkg_dir.is_dir()
        # Should contain key modules
        assert (pkg_dir / "__init__.py").exists()
        assert (pkg_dir / "cli.py").exists()

    def test_creates_config_toml(self, tmp_path: Path) -> None:
        """install_and_own should create config.toml with version and settings."""
        from qt_ai_dev_tools.__version__ import __version__
        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path, memory=8192, cpus=8)

        config_path = tmp_path / "config.toml"
        assert config_path.exists()
        content = config_path.read_text()
        assert __version__ in content
        assert "memory = 8192" in content
        assert "cpus = 8" in content

    def test_creates_cli_script(self, tmp_path: Path) -> None:
        """install_and_own should create an executable cli script."""
        import stat

        from qt_ai_dev_tools.installer import install_and_own

        install_and_own(tmp_path)

        cli_path = tmp_path / "cli"
        assert cli_path.exists()
        assert cli_path.stat().st_mode & stat.S_IXUSR

    def test_returns_created_paths(self, tmp_path: Path) -> None:
        """install_and_own should return a list of created/updated path strings."""
        from qt_ai_dev_tools.installer import install_and_own

        created = install_and_own(tmp_path)

        assert isinstance(created, list)
        assert len(created) > 0
        assert "config.toml" in created
        assert "cli" in created
        assert "src/qt_ai_dev_tools/" in created


class TestCopySkills:
    """Tests for _copy_skills() edge cases."""

    def test_returns_silently_when_skills_dir_missing(self, tmp_path: Path) -> None:
        """_copy_skills should not crash when the source skills/ dir doesn't exist."""
        from qt_ai_dev_tools.installer import _copy_skills

        # Patch _PACKAGE_ROOT so project_root / "skills" resolves to a nonexistent path
        fake_pkg_root = tmp_path / "fake" / "pkg" / "root"
        fake_pkg_root.mkdir(parents=True)
        target_skills = tmp_path / "output_skills"

        with patch("qt_ai_dev_tools.installer._PACKAGE_ROOT", fake_pkg_root):
            # Should not raise
            _copy_skills(target_skills)

        # Target should not be created since source doesn't exist
        assert not target_skills.exists()


class TestSelfUpdate:
    """Tests for self_update() — re-install preserving user config."""

    def test_preserves_config_toml(self, tmp_path: Path) -> None:
        """self_update should preserve user-modified config.toml."""
        from qt_ai_dev_tools.installer import install_and_own, self_update

        # Initial install
        install_and_own(tmp_path)

        # User modifies config.toml
        config_path = tmp_path / "config.toml"
        custom_config = "# my custom config\nmemory = 16384\ncpus = 16\n"
        config_path.write_text(custom_config)

        # Run self_update
        self_update(tmp_path)

        # Config should be preserved (not overwritten by init defaults)
        assert config_path.read_text() == custom_config

    def test_preserves_notes_directory(self, tmp_path: Path) -> None:
        """self_update should preserve the notes/ directory."""
        from qt_ai_dev_tools.installer import install_and_own, self_update

        # Initial install
        install_and_own(tmp_path)

        # User adds a note
        notes_dir = tmp_path / "notes"
        note_file = notes_dir / "my_note.txt"
        note_file.write_text("important note")

        # Run self_update
        self_update(tmp_path)

        # Note should be preserved
        assert note_file.exists()
        assert note_file.read_text() == "important note"

    def test_raises_on_nonexistent_target(self, tmp_path: Path) -> None:
        """self_update should raise FileNotFoundError for missing target."""
        from qt_ai_dev_tools.installer import self_update

        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(FileNotFoundError, match="does not exist"):
            self_update(nonexistent)

    def test_returns_updated_paths(self, tmp_path: Path) -> None:
        """self_update should return a list of updated path strings."""
        from qt_ai_dev_tools.installer import install_and_own, self_update

        install_and_own(tmp_path)
        updated = self_update(tmp_path)

        assert isinstance(updated, list)
        assert len(updated) > 0
