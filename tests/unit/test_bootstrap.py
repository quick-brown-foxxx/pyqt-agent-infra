"""Tests for bridge bootstrap module (sys.remote_exec injection)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qt_ai_dev_tools.bridge._bootstrap import (
    _BOOTSTRAP_TEMPLATE,
    _discover_qt_process,
    _find_package_path,
    _write_bootstrap_script,
    can_remote_exec,
    detect_python_version,
    wait_for_socket,
)

pytestmark = pytest.mark.unit


class TestCanRemoteExec:
    """Test Python version and capability checks."""

    def test_returns_false_on_pre_314(self) -> None:
        """Should return False on Python < 3.14."""
        with patch.object(sys, "version_info", (3, 12, 0)):
            assert can_remote_exec() is False

    def test_returns_false_when_no_attr(self) -> None:
        """Should return False if sys.remote_exec doesn't exist."""
        with patch.object(sys, "version_info", (3, 14, 0)):
            # Ensure sys.remote_exec doesn't exist
            if hasattr(sys, "remote_exec"):
                with patch.object(sys, "remote_exec", create=False):
                    delattr(sys, "remote_exec")
                    assert can_remote_exec() is False
            else:
                assert can_remote_exec() is False


class TestDetectPythonVersion:
    """Test Python version detection from /proc/<pid>/exe."""

    def test_nonexistent_pid(self, tmp_path: Path) -> None:
        """Should raise RuntimeError for a nonexistent PID."""
        with pytest.raises(RuntimeError, match="not found"):
            detect_python_version(999999999)

    def test_parse_version_output(self) -> None:
        """Should parse 'Python X.Y.Z' from --version output."""
        import subprocess

        mock_result = subprocess.CompletedProcess(
            args=["python3.14", "--version"],
            returncode=0,
            stdout="Python 3.14.1",
            stderr="",
        )

        with (
            patch("qt_ai_dev_tools.bridge._bootstrap.Path") as mock_path_cls,
            patch("qt_ai_dev_tools.bridge._bootstrap.run_command", return_value=mock_result),
        ):
            mock_exe_link = MagicMock()
            mock_exe_link.exists.return_value = True
            mock_exe_link.resolve.return_value = Path("/usr/bin/python3.14")
            mock_path_cls.return_value = mock_exe_link

            major, minor = detect_python_version(12345)
            assert major == 3
            assert minor == 14

    def test_not_python_process(self) -> None:
        """Should raise RuntimeError if exe is not Python."""
        import subprocess

        mock_result = subprocess.CompletedProcess(
            args=["/usr/bin/bash", "--version"],
            returncode=0,
            stdout="bash 5.2.0",
            stderr="",
        )

        with (
            patch("qt_ai_dev_tools.bridge._bootstrap.Path") as mock_path_cls,
            patch("qt_ai_dev_tools.bridge._bootstrap.run_command", return_value=mock_result),
        ):
            mock_exe_link = MagicMock()
            mock_exe_link.exists.return_value = True
            mock_exe_link.resolve.return_value = Path("/usr/bin/bash")
            mock_path_cls.return_value = mock_exe_link

            with pytest.raises(RuntimeError, match="Not a Python process"):
                detect_python_version(12345)


class TestFindPackagePath:
    """Test package path discovery for bootstrap injection."""

    def test_returns_parent_of_package(self) -> None:
        """Should return the parent directory of qt_ai_dev_tools package."""
        pkg_path = _find_package_path()
        assert Path(pkg_path).is_dir()
        # The path should be the parent of the qt_ai_dev_tools package
        assert (Path(pkg_path) / "qt_ai_dev_tools").is_dir()


class TestWriteBootstrapScript:
    """Test bootstrap script generation."""

    def test_writes_valid_script(self, tmp_path: Path) -> None:
        """Should write a bootstrap script with correct package path."""
        with patch("qt_ai_dev_tools.bridge._bootstrap.tempfile.gettempdir", return_value=str(tmp_path)):
            script_path = _write_bootstrap_script(1234)

        assert script_path.exists()
        content = script_path.read_text()
        assert "sys.path.insert(0," in content
        assert "from qt_ai_dev_tools.bridge._server import" in content
        assert "server.start()" in content

        # Clean up
        script_path.unlink()

    def test_script_filename_contains_pid(self, tmp_path: Path) -> None:
        """Script filename should include the target PID."""
        with patch("qt_ai_dev_tools.bridge._bootstrap.tempfile.gettempdir", return_value=str(tmp_path)):
            script_path = _write_bootstrap_script(5678)

        assert "5678" in script_path.name
        script_path.unlink()


class TestBootstrapTemplate:
    """Test the bootstrap template string."""

    def test_template_has_placeholder(self) -> None:
        """Template should contain package_path placeholder."""
        assert "{package_path!r}" in _BOOTSTRAP_TEMPLATE

    def test_template_formats_correctly(self) -> None:
        """Template should format with a package path."""
        result = _BOOTSTRAP_TEMPLATE.format(package_path="/some/path")
        assert "'/some/path'" in result
        assert "sys.path.insert(0," in result


class TestWaitForSocket:
    """Test socket polling logic."""

    def test_returns_immediately_if_socket_exists(self, tmp_path: Path) -> None:
        """Should return path immediately if socket file exists."""
        sock_file = tmp_path / "test.sock"
        sock_file.touch()

        with patch(
            "qt_ai_dev_tools.bridge._bootstrap.socket_path_for_pid",
            return_value=str(sock_file),
        ):
            result = wait_for_socket(1234, timeout=1.0)
            assert result == sock_file

    def test_raises_on_timeout(self, tmp_path: Path) -> None:
        """Should raise RuntimeError if socket doesn't appear in time."""
        with (
            patch(
                "qt_ai_dev_tools.bridge._bootstrap.socket_path_for_pid",
                return_value=str(tmp_path / "nonexistent.sock"),
            ),
            pytest.raises(RuntimeError, match="did not appear"),
        ):
            wait_for_socket(1234, timeout=0.2, poll_interval=0.05)


class TestDiscoverQtProcess:
    """Test Qt process auto-discovery."""

    def test_raises_when_no_sockets(self) -> None:
        """Should raise RuntimeError when no bridge sockets exist."""
        with (
            patch("qt_ai_dev_tools.bridge._bootstrap.glob_mod.glob", return_value=[]),
            pytest.raises(RuntimeError, match="Cannot auto-discover"),
        ):
            _discover_qt_process()

    def test_returns_pid_from_live_socket(self) -> None:
        """Should return PID from a socket whose process is still alive."""
        with (
            patch(
                "qt_ai_dev_tools.bridge._bootstrap.glob_mod.glob",
                return_value=["/tmp/qt-ai-dev-tools-bridge-1234.sock"],
            ),
            patch("qt_ai_dev_tools.bridge._bootstrap.os.kill"),
        ):
            pid = _discover_qt_process()
            assert pid == 1234

    def test_skips_dead_processes(self) -> None:
        """Should skip sockets whose PIDs are no longer alive."""
        with (
            patch(
                "qt_ai_dev_tools.bridge._bootstrap.glob_mod.glob",
                return_value=["/tmp/qt-ai-dev-tools-bridge-9999.sock"],
            ),
            patch(
                "qt_ai_dev_tools.bridge._bootstrap.os.kill",
                side_effect=ProcessLookupError,
            ),
            pytest.raises(RuntimeError, match="Cannot auto-discover"),
        ):
            _discover_qt_process()
