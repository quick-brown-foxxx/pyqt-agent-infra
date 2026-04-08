"""Tests for VM tool readiness check module."""

from __future__ import annotations

import subprocess
import typing
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qt_ai_dev_tools._vm_tool import (
    InstallMode,
    ToolVersionMismatchError,
    _check_local_mode,
    _check_pypi_mode,
    _compute_source_hash,
    _detect_install_mode,
    _get_vm_tool_version,
    ensure_tool_ready,
)

pytestmark = pytest.mark.unit


class TestDetectInstallMode:
    def test_local_when_dir_exists(self, tmp_path: Path) -> None:
        toolkit_dir = tmp_path / ".qt-ai-dev-tools" / "src" / "qt_ai_dev_tools"
        toolkit_dir.mkdir(parents=True)
        assert _detect_install_mode(tmp_path) == InstallMode.LOCAL

    def test_pypi_when_dir_missing(self, tmp_path: Path) -> None:
        assert _detect_install_mode(tmp_path) == InstallMode.PYPI

    def test_pypi_when_partial_path(self, tmp_path: Path) -> None:
        # Only .qt-ai-dev-tools exists, not the full src path
        (tmp_path / ".qt-ai-dev-tools").mkdir()
        assert _detect_install_mode(tmp_path) == InstallMode.PYPI


class TestGetVmToolVersion:
    def test_parses_valid_output(self, tmp_path: Path) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.stdout = "qt-ai-dev-tools 0.6.2\n"
        mock_result.returncode = 0
        with patch("qt_ai_dev_tools.vagrant.vm.vm_run", return_value=mock_result):
            assert _get_vm_tool_version(tmp_path) == "0.6.2"

    def test_returns_none_on_failure(self, tmp_path: Path) -> None:
        with patch("qt_ai_dev_tools.vagrant.vm.vm_run", side_effect=subprocess.CalledProcessError(1, "cmd")):
            assert _get_vm_tool_version(tmp_path) is None

    def test_returns_none_on_garbage(self, tmp_path: Path) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.stdout = "some random output\n"
        mock_result.returncode = 0
        with patch("qt_ai_dev_tools.vagrant.vm.vm_run", return_value=mock_result):
            assert _get_vm_tool_version(tmp_path) is None

    def test_returns_none_on_empty_output(self, tmp_path: Path) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.stdout = ""
        mock_result.returncode = 0
        with patch("qt_ai_dev_tools.vagrant.vm.vm_run", return_value=mock_result):
            assert _get_vm_tool_version(tmp_path) is None


class TestComputeSourceHash:
    def test_consistent_for_same_content(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src" / "qt_ai_dev_tools"
        src_dir.mkdir(parents=True)
        (src_dir / "a.py").write_text("print('hello')")
        (src_dir / "b.py").write_text("print('world')")

        hash1 = _compute_source_hash(tmp_path)
        hash2 = _compute_source_hash(tmp_path)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_different_for_changed_content(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src" / "qt_ai_dev_tools"
        src_dir.mkdir(parents=True)
        (src_dir / "a.py").write_text("print('hello')")

        hash1 = _compute_source_hash(tmp_path)

        (src_dir / "a.py").write_text("print('changed')")
        hash2 = _compute_source_hash(tmp_path)

        assert hash1 != hash2

    def test_empty_string_for_missing_dir(self, tmp_path: Path) -> None:
        assert _compute_source_hash(tmp_path / "nonexistent") == ""

    def test_includes_nested_files(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src" / "qt_ai_dev_tools"
        sub_dir = src_dir / "sub"
        sub_dir.mkdir(parents=True)
        (src_dir / "a.py").write_text("top")
        (sub_dir / "b.py").write_text("nested")

        h = _compute_source_hash(tmp_path)
        assert h != ""
        assert len(h) == 64

    def test_ignores_non_py_files(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src" / "qt_ai_dev_tools"
        src_dir.mkdir(parents=True)
        (src_dir / "a.py").write_text("code")

        hash_before = _compute_source_hash(tmp_path)

        (src_dir / "readme.txt").write_text("docs")
        hash_after = _compute_source_hash(tmp_path)

        assert hash_before == hash_after


class TestCheckPypiMode:
    def test_matching_versions_succeeds(self, tmp_path: Path) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.stdout = "qt-ai-dev-tools 0.6.2\n"
        mock_result.returncode = 0
        with (
            patch("qt_ai_dev_tools.vagrant.vm.vm_run", return_value=mock_result),
            patch("qt_ai_dev_tools._vm_tool.__version__", "0.6.2"),  # type: ignore[attr-defined]  # rationale: patching module-level version string for testing
        ):
            _check_pypi_mode(tmp_path)  # should not raise

    def test_mismatch_raises(self, tmp_path: Path) -> None:
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.stdout = "qt-ai-dev-tools 0.5.0\n"
        mock_result.returncode = 0
        with (
            patch("qt_ai_dev_tools.vagrant.vm.vm_run", return_value=mock_result),
            patch("qt_ai_dev_tools._vm_tool.__version__", "0.6.2"),  # type: ignore[attr-defined]  # rationale: patching module-level version string for testing
            pytest.raises(ToolVersionMismatchError, match=r"0\.5\.0.*0\.6\.2"),
        ):
            _check_pypi_mode(tmp_path)

    def test_mismatch_warns_when_allowed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_ALLOW_VERSION_MISMATCH", "1")
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.stdout = "qt-ai-dev-tools 0.5.0\n"
        mock_result.returncode = 0
        with (
            patch("qt_ai_dev_tools.vagrant.vm.vm_run", return_value=mock_result),
            patch("qt_ai_dev_tools._vm_tool.__version__", "0.6.2"),  # type: ignore[attr-defined]  # rationale: patching module-level version string for testing
        ):
            _check_pypi_mode(tmp_path)  # should not raise

    def test_not_installed_raises(self, tmp_path: Path) -> None:
        with (
            patch(
                "qt_ai_dev_tools.vagrant.vm.vm_run",
                side_effect=subprocess.CalledProcessError(1, "cmd"),
            ),
            pytest.raises(ToolVersionMismatchError, match="not installed"),
        ):
            _check_pypi_mode(tmp_path)


class TestCheckLocalMode:
    def test_rebuilds_when_stale(self, tmp_path: Path) -> None:
        # Set up local toolkit dir
        src_dir = tmp_path / ".qt-ai-dev-tools" / "src" / "qt_ai_dev_tools"
        src_dir.mkdir(parents=True)
        (src_dir / "main.py").write_text("print('hello')")

        current_hash = _compute_source_hash(tmp_path / ".qt-ai-dev-tools")

        # VM has a different hash
        stale_result = MagicMock(spec=subprocess.CompletedProcess)
        stale_result.stdout = "old-hash-value\n"
        stale_result.returncode = 0

        install_result = MagicMock(spec=subprocess.CompletedProcess)
        install_result.returncode = 0

        write_result = MagicMock(spec=subprocess.CompletedProcess)
        write_result.returncode = 0

        call_count = 0
        call_args_log: list[str] = []

        def mock_vm_run(command: str, workspace: Path | None = None, **_kw: object) -> MagicMock:
            nonlocal call_count
            call_args_log.append(command)
            call_count += 1
            if "cat " in command:
                return stale_result
            if "uv tool install" in command:
                return install_result
            if "mkdir" in command or "tee" in command:
                return write_result
            return stale_result

        with patch("qt_ai_dev_tools.vagrant.vm.vm_run", side_effect=mock_vm_run):
            _check_local_mode(tmp_path, tmp_path / ".qt-ai-dev-tools")

        # Should have called uv tool install
        assert any("uv tool install" in cmd for cmd in call_args_log)
        # Should have written the new hash
        assert any(current_hash in cmd for cmd in call_args_log)

    def test_skips_rebuild_when_current(self, tmp_path: Path) -> None:
        src_dir = tmp_path / ".qt-ai-dev-tools" / "src" / "qt_ai_dev_tools"
        src_dir.mkdir(parents=True)
        (src_dir / "main.py").write_text("print('hello')")

        current_hash = _compute_source_hash(tmp_path / ".qt-ai-dev-tools")

        hash_result = MagicMock(spec=subprocess.CompletedProcess)
        hash_result.stdout = current_hash + "\n"
        hash_result.returncode = 0

        call_args_log: list[str] = []

        def mock_vm_run(command: str, workspace: Path | None = None, **_kw: object) -> MagicMock:
            call_args_log.append(command)
            return hash_result

        with patch("qt_ai_dev_tools.vagrant.vm.vm_run", side_effect=mock_vm_run):
            _check_local_mode(tmp_path, tmp_path / ".qt-ai-dev-tools")

        # Should NOT have called uv tool install
        assert not any("uv tool install" in cmd for cmd in call_args_log)


class TestEnsureToolReady:
    pytestmark: typing.ClassVar[list[pytest.MarkDecorator]] = [pytest.mark.unit]

    def test_skips_when_inside_vm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "1")
        # Should return immediately without calling anything
        ensure_tool_ready(Path("/nonexistent"))  # no error

    def test_pypi_mode_dispatches(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("QT_AI_DEV_TOOLS_VM", raising=False)
        ws = tmp_path / ".qt-ai-dev-tools"
        ws.mkdir()
        (ws / "Vagrantfile").touch()

        with (
            patch("qt_ai_dev_tools.vagrant.vm.find_workspace", return_value=ws),
            patch("qt_ai_dev_tools._vm_tool._check_pypi_mode") as mock_check,
        ):
            ensure_tool_ready(tmp_path, ws)
            mock_check.assert_called_once_with(ws)

    def test_local_mode_dispatches(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("QT_AI_DEV_TOOLS_VM", raising=False)
        ws = tmp_path / ".qt-ai-dev-tools"
        ws.mkdir()
        (ws / "Vagrantfile").touch()
        # Create local toolkit dir to trigger LOCAL mode
        (tmp_path / ".qt-ai-dev-tools" / "src" / "qt_ai_dev_tools").mkdir(parents=True)

        with (
            patch("qt_ai_dev_tools.vagrant.vm.find_workspace", return_value=ws),
            patch("qt_ai_dev_tools._vm_tool._check_local_mode") as mock_check,
        ):
            ensure_tool_ready(tmp_path, ws)
            mock_check.assert_called_once_with(tmp_path, ws)
