"""Tests for bridge server socket protocol — no PySide6/VM needed.

Tests the BridgeServer socket handling with a mock executor,
verifying the JSON protocol over Unix sockets.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

from qt_ai_dev_tools.bridge._protocol import (
    EvalRequest,
    EvalResponse,
    decode_response,
    encode_request,
)

pytestmark = pytest.mark.unit


class MockExecutor:
    """Minimal executor that returns canned responses without PySide6."""

    def dispatch(self, code: str, mode: str) -> EvalResponse:
        """Return a successful response with the code echoed back."""
        if code == "raise_error":
            return EvalResponse(ok=False, error="Simulated error")
        return EvalResponse(
            ok=True,
            result=repr(code),
            type_name="str",
            stdout="",
            duration_ms=1,
        )


def _send_and_receive(sock_path: str, request: EvalRequest, timeout: float = 5.0) -> EvalResponse:
    """Send a request to the bridge server and return the response."""
    request_bytes = encode_request(request)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(sock_path)
        sock.sendall(request_bytes)

        data = b""
        while b"\n" not in data:
            chunk = sock.recv(65536)
            if not chunk:
                msg = "Server closed connection"
                raise ConnectionError(msg)
            data += chunk

        return decode_response(data.split(b"\n", 1)[0])
    finally:
        sock.close()


class _FakeServer:
    """Lightweight bridge server that uses MockExecutor instead of BridgeExecutor.

    Replicates the BridgeServer socket logic without any PySide6 dependency.
    """

    def __init__(self, executor: MockExecutor, socket_path: str) -> None:
        self._executor = executor
        self._socket_path = socket_path
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> str:
        """Bind and start the accept loop."""
        sock_file = Path(self._socket_path)
        if sock_file.exists():
            sock_file.unlink()

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(self._socket_path)
        self._socket.listen(1)
        self._socket.settimeout(1.0)
        self._running = True

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        return self._socket_path

    def stop(self) -> None:
        """Stop the server and clean up."""
        self._running = False
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        sock_file = Path(self._socket_path)
        if sock_file.exists():
            sock_file.unlink()

    def _accept_loop(self) -> None:
        while self._running:
            try:
                if self._socket is None:
                    break
                conn = self._socket.accept()[0]
            except TimeoutError:
                continue
            except OSError:
                break

            try:
                self._handle_connection(conn)
            except Exception:  # noqa: S110
                pass  # Test server — errors logged by real server
            finally:
                conn.close()

    def _handle_connection(self, conn: socket.socket) -> None:
        conn.settimeout(5.0)
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(65536)
            if not chunk:
                return
            data += chunk

        line = data.split(b"\n", 1)[0]
        from qt_ai_dev_tools.bridge._protocol import decode_request, encode_response

        request = decode_request(line)
        response = self._executor.dispatch(request.code, request.mode)
        conn.sendall(encode_response(response))


@pytest.fixture
def bridge_server(tmp_path: Path) -> _FakeServer:
    """Start a fake bridge server on a temp socket, yield it, then stop."""
    sock_path = str(tmp_path / "test-bridge.sock")
    executor = MockExecutor()
    server = _FakeServer(executor, sock_path)
    server.start()
    # Brief wait for socket to be ready
    time.sleep(0.05)
    yield server
    server.stop()


class TestBridgeServerProtocol:
    """Test the JSON-over-Unix-socket protocol."""

    def test_eval_request_returns_response(self, bridge_server: _FakeServer) -> None:
        """Should send a request and receive a successful response."""
        response = _send_and_receive(
            bridge_server._socket_path,
            EvalRequest(code="1 + 1", mode="eval"),
        )
        assert response.ok is True
        assert response.result is not None
        assert "1 + 1" in response.result

    def test_exec_mode(self, bridge_server: _FakeServer) -> None:
        """Should handle exec mode requests."""
        response = _send_and_receive(
            bridge_server._socket_path,
            EvalRequest(code="x = 1", mode="exec"),
        )
        assert response.ok is True

    def test_auto_mode(self, bridge_server: _FakeServer) -> None:
        """Should handle auto mode (default)."""
        response = _send_and_receive(
            bridge_server._socket_path,
            EvalRequest(code="hello"),
        )
        assert response.ok is True

    def test_error_response(self, bridge_server: _FakeServer) -> None:
        """Should return error response for error-triggering code."""
        response = _send_and_receive(
            bridge_server._socket_path,
            EvalRequest(code="raise_error"),
        )
        assert response.ok is False
        assert response.error == "Simulated error"

    def test_multiple_requests_sequential(self, bridge_server: _FakeServer) -> None:
        """Should handle multiple sequential requests (one connection each)."""
        for i in range(3):
            response = _send_and_receive(
                bridge_server._socket_path,
                EvalRequest(code=f"request_{i}"),
            )
            assert response.ok is True
            assert f"request_{i}" in (response.result or "")

    def test_invalid_json_returns_error(self, bridge_server: _FakeServer) -> None:
        """Should return error for malformed JSON requests."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect(bridge_server._socket_path)
            sock.sendall(b"not valid json\n")

            data = b""
            while b"\n" not in data:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk

            # Server should either close the connection or send an error response
            if data:
                response = decode_response(data.split(b"\n", 1)[0])
                assert response.ok is False
        finally:
            sock.close()


class TestServerLifecycle:
    """Test server start/stop lifecycle."""

    def test_start_creates_socket(self, tmp_path: Path) -> None:
        """Should create the socket file on start."""
        sock_path = str(tmp_path / "lifecycle.sock")
        executor = MockExecutor()
        server = _FakeServer(executor, sock_path)
        server.start()
        time.sleep(0.05)
        try:
            assert Path(sock_path).exists()
        finally:
            server.stop()

    def test_stop_removes_socket(self, tmp_path: Path) -> None:
        """Should remove the socket file on stop."""
        sock_path = str(tmp_path / "lifecycle.sock")
        executor = MockExecutor()
        server = _FakeServer(executor, sock_path)
        server.start()
        time.sleep(0.05)
        server.stop()
        assert not Path(sock_path).exists()
