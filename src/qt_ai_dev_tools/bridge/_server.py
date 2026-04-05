"""Bridge server: Unix socket server dispatching eval to Qt main thread.

This module is a PySide6 boundary — all PySide6 imports are confined here
(same pattern as _atspi.py for AT-SPI, _qt_namespace.py for bridge namespace).
"""

from __future__ import annotations

import contextlib
import logging
import os
import socket
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal  # type: ignore[import-not-found]  # rationale: PySide6 is a system dep

from qt_ai_dev_tools.bridge._eval import build_qt_namespace, execute
from qt_ai_dev_tools.bridge._protocol import (
    EvalMode,
    EvalResponse,
    decode_request,
    encode_response,
    socket_path_for_pid,
)

logger = logging.getLogger(__name__)

_RECV_BUFSIZE: int = 65536
_MAX_MESSAGE_SIZE: int = 1_048_576  # 1MB


class BridgeExecutor(QObject):  # type: ignore[reportGeneralClassIssue]  # rationale: QObject base from PySide6 not in venv
    """Executes eval requests on the Qt main thread.

    Lives on the main thread. The server thread emits ``_eval_requested``
    with a BlockingQueuedConnection, which blocks the server thread until
    the slot completes on the main thread. This is the standard PySide6
    pattern for cross-thread synchronous dispatch.
    """

    _eval_requested = Signal(str, str)  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 Signal descriptor not in venv

    def __init__(self) -> None:
        super().__init__()  # type: ignore[reportUnknownMemberType]  # rationale: QObject.__init__ not in venv
        self._namespace: dict[str, object] = build_qt_namespace()
        self._result: EvalResponse | None = None
        self._lock = threading.Lock()
        # Connect with BlockingQueuedConnection: emit from server thread blocks
        # until _on_eval finishes on the main thread.
        self._eval_requested.connect(  # type: ignore[reportUnknownMemberType]  # rationale: PySide6 Signal not in venv
            self._on_eval,
            Qt.ConnectionType.BlockingQueuedConnection,  # type: ignore[reportAttributeAccessIssue]  # rationale: PySide6 enum not in venv
        )

    def _on_eval(self, code: str, mode: EvalMode) -> None:
        """Execute code on the main thread. Connected via BlockingQueuedConnection."""
        self._refresh_widgets()
        self._result = execute(code, self._namespace, mode)

    def dispatch(self, code: str, mode: EvalMode) -> EvalResponse:
        """Dispatch an eval request to the main thread (called from server thread).

        Thread-safe: serialized via lock. Emits _eval_requested which blocks
        until _on_eval completes on the main thread.
        """
        with self._lock:
            self._eval_requested.emit(code, mode)  # type: ignore[reportUnknownMemberType]  # rationale: PySide6 Signal not in venv
            if self._result is None:
                return EvalResponse(ok=False, error="No result available")
            return self._result

    def _refresh_widgets(self) -> None:
        """Rebuild the widgets dict to reflect current app state."""
        from PySide6.QtWidgets import (  # type: ignore[import-not-found]  # rationale: PySide6 is a system dep
            QApplication,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        )

        qapp = QApplication.instance()  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]  # rationale: PySide6 not in venv
        if qapp is not None:
            widgets: dict[str, object] = {}
            for w in qapp.allWidgets():  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]  # rationale: PySide6 not in venv
                obj_name: str = w.objectName()  # type: ignore[reportUnknownMemberType]  # rationale: PySide6 not in venv
                if obj_name:
                    widgets[obj_name] = w
            self._namespace["widgets"] = widgets


class BridgeServer:
    """Unix socket server for bridge eval requests.

    Accepts connections on a Unix socket, reads newline-terminated JSON
    eval requests, dispatches them to the Qt main thread via BridgeExecutor,
    and sends back JSON responses.
    """

    def __init__(self, executor: BridgeExecutor) -> None:
        self._executor = executor
        self._socket: socket.socket | None = None
        self._socket_path: str = ""
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self, socket_path: str | None = None) -> str:
        """Start accepting connections. Returns the socket path.

        Binds to the given path (or the default PID-based path), starts
        a daemon thread running the accept loop.
        """
        if socket_path is None:
            socket_path = socket_path_for_pid(os.getpid())
        self._socket_path = socket_path

        # Clean up stale socket file
        sock_file = Path(socket_path)
        if sock_file.exists():
            sock_file.unlink()

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(socket_path)
        os.chmod(socket_path, 0o600)
        self._socket.listen(1)
        self._socket.settimeout(1.0)  # periodic check of _running flag
        self._running = True

        self._thread = threading.Thread(target=self._accept_loop, daemon=True, name="bridge-server")
        self._thread.start()

        logger.info("Bridge server listening on %s", socket_path)
        return socket_path

    def stop(self) -> None:
        """Stop the server, close socket, clean up socket file."""
        self._running = False
        if self._socket is not None:
            with contextlib.suppress(OSError):
                self._socket.close()
            self._socket = None
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        sock_file = Path(self._socket_path)
        if sock_file.exists():
            with contextlib.suppress(OSError):
                sock_file.unlink()
        logger.info("Bridge server stopped")

    def _accept_loop(self) -> None:
        """Accept connections in a loop until stopped."""
        while self._running:
            try:
                if self._socket is None:
                    break
                conn = self._socket.accept()[0]
            except TimeoutError:
                continue  # check _running flag
            except OSError:
                break  # socket closed

            try:
                self._handle_connection(conn)
            except Exception:
                logger.exception("Error handling bridge connection")
            finally:
                conn.close()

    def _handle_connection(self, conn: socket.socket) -> None:
        """Handle a single connection: read request, dispatch eval, send response."""
        conn.settimeout(30.0)
        data = b""
        while b"\n" not in data:
            if len(data) > _MAX_MESSAGE_SIZE:
                error_resp = EvalResponse(ok=False, error=f"Request too large (>{_MAX_MESSAGE_SIZE} bytes)")
                conn.sendall(encode_response(error_resp))
                return
            chunk = conn.recv(_RECV_BUFSIZE)
            if not chunk:
                return
            data += chunk

        line = data.split(b"\n", 1)[0]

        try:
            request = decode_request(line)
        except (TypeError, KeyError, ValueError) as exc:
            error_resp = EvalResponse(ok=False, error=f"Invalid request: {exc}")
            conn.sendall(encode_response(error_resp))
            return

        response = self._executor.dispatch(request.code, request.mode)
        conn.sendall(encode_response(response))

    @property
    def socket_path(self) -> str:
        """Return the active socket path."""
        return self._socket_path

    @property
    def is_running(self) -> bool:
        """Check if server accept loop is active."""
        return self._running


# Module-level singleton for the active server.
# Accessed by bridge/__init__.py (same package) — not truly "external" usage.
active_server: BridgeServer | None = None
