"""Tests for bridge client."""

from __future__ import annotations

import socket
import threading
from pathlib import Path

from qt_ai_dev_tools.bridge._client import (
    _extract_pid,
    eval_code,
    find_bridge_socket,
)
from qt_ai_dev_tools.bridge._protocol import EvalResponse, encode_response


class TestExtractPid:
    def test_normal_path(self) -> None:
        assert _extract_pid("/tmp/qt-ai-dev-tools-bridge-1234.sock") == "1234"

    def test_large_pid(self) -> None:
        assert _extract_pid("/tmp/qt-ai-dev-tools-bridge-99999.sock") == "99999"


class TestFindBridgeSocket:
    def test_no_socket_for_specific_pid_returns_none(self) -> None:
        """When no socket file exists for the given PID, return None."""
        result = find_bridge_socket(pid=999999)
        assert result is None

    def test_specific_pid_found(self, tmp_path: Path) -> None:
        """When socket file exists for the given PID, return its path."""
        sock_path = tmp_path / "qt-ai-dev-tools-bridge-12345.sock"
        sock_path.touch()

        from unittest.mock import patch

        import qt_ai_dev_tools.bridge._client as client_mod

        with patch.object(client_mod, "socket_path_for_pid", return_value=str(sock_path)):
            result = find_bridge_socket(pid=12345)
        assert result == sock_path


class TestEvalCode:
    def test_eval_success(self, tmp_path: Path) -> None:
        """Test eval_code against a mock Unix socket server."""
        sock_path = tmp_path / "test-bridge.sock"

        response = EvalResponse(ok=True, result="42", type_name="int", duration_ms=1)
        response_bytes = encode_response(response)

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(str(sock_path))
        server_sock.listen(1)

        def mock_server() -> None:
            conn, _ = server_sock.accept()
            conn.recv(65536)  # read request
            conn.sendall(response_bytes)
            conn.close()
            server_sock.close()

        thread = threading.Thread(target=mock_server, daemon=True)
        thread.start()

        result = eval_code(sock_path, "1+1")
        assert result.ok is True
        assert result.result == "42"
        assert result.type_name == "int"
        thread.join(timeout=2)

    def test_eval_connection_error_nonexistent_socket(self, tmp_path: Path) -> None:
        """Connecting to nonexistent socket returns error response."""
        sock_path = tmp_path / "nonexistent.sock"
        result = eval_code(sock_path, "1+1")
        assert result.ok is False
        assert result.error is not None

    def test_eval_timeout(self, tmp_path: Path) -> None:
        """Slow server triggers timeout."""
        sock_path = tmp_path / "slow-bridge.sock"

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(str(sock_path))
        server_sock.listen(1)

        def slow_server() -> None:
            conn, _ = server_sock.accept()
            import time

            time.sleep(5)
            conn.close()
            server_sock.close()

        thread = threading.Thread(target=slow_server, daemon=True)
        thread.start()

        result = eval_code(sock_path, "1+1", timeout=0.5)
        assert result.ok is False
        assert result.error is not None
        assert "timeout" in result.error.lower()
        thread.join(timeout=1)

    def test_eval_server_closes_without_response(self, tmp_path: Path) -> None:
        """Server closes connection immediately without sending data."""
        sock_path = tmp_path / "close-bridge.sock"

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(str(sock_path))
        server_sock.listen(1)

        def close_server() -> None:
            conn, _ = server_sock.accept()
            conn.recv(65536)
            conn.close()
            server_sock.close()

        thread = threading.Thread(target=close_server, daemon=True)
        thread.start()

        result = eval_code(sock_path, "1+1")
        assert result.ok is False
        assert result.error is not None
        assert "closed connection" in result.error.lower()
        thread.join(timeout=2)
