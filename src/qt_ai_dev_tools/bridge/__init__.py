"""Bridge: runtime code execution inside Qt apps.

Start the bridge in your Qt app::

    from qt_ai_dev_tools.bridge import start
    start()  # requires QT_AI_DEV_TOOLS_BRIDGE=1 env var

Or with force=True to bypass the env var check::

    start(force=True)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path as _Path

from qt_ai_dev_tools._env import BRIDGE, get_bool

logger = logging.getLogger(__name__)


def start(*, force: bool = False) -> None:
    """Start the bridge server if QT_AI_DEV_TOOLS_BRIDGE=1 (or force=True).

    Call this after QApplication is created. The bridge runs on a daemon
    thread and accepts eval requests via Unix socket.
    """
    if not force and not get_bool(BRIDGE):
        return

    import atexit

    import qt_ai_dev_tools.bridge._server as server_mod
    from qt_ai_dev_tools.bridge._server import BridgeExecutor, BridgeServer

    if server_mod.active_server is not None and server_mod.active_server.is_running:
        logger.warning("Bridge already running on %s", server_mod.active_server.socket_path)
        return

    executor = BridgeExecutor()
    server = BridgeServer(executor)
    socket_path = server.start()
    server_mod.active_server = server

    atexit.register(server.stop)

    logger.info("qt-ai-dev-tools bridge active on %s", socket_path)


def stop() -> None:
    """Stop the bridge server and clean up socket."""
    import qt_ai_dev_tools.bridge._server as server_mod

    if server_mod.active_server is not None:
        server_mod.active_server.stop()
        server_mod.active_server = None


def socket_path(pid: int | None = None) -> _Path:
    """Return the socket path for given PID (default: current process)."""
    from qt_ai_dev_tools.bridge._protocol import socket_path_for_pid

    return _Path(socket_path_for_pid(pid if pid is not None else os.getpid()))
