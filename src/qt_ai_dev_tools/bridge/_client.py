"""Bridge client: connect to bridge server and execute code."""

from __future__ import annotations

import glob
import logging
import socket
from pathlib import Path

from qt_ai_dev_tools.bridge._protocol import (
    EvalMode,
    EvalRequest,
    EvalResponse,
    decode_response,
    encode_request,
    socket_path_for_pid,
)

logger = logging.getLogger(__name__)

_RECV_BUFSIZE: int = 65536
_MAX_MESSAGE_SIZE: int = 1_048_576  # 1MB


def find_bridge_socket(pid: int | None = None) -> Path | None:
    """Find an active bridge socket.

    If pid is given, check that specific socket. Otherwise scan for any
    active bridge socket in /tmp/.

    Returns the socket path, or None if no bridge found.
    Raises RuntimeError if multiple bridges found (agent must specify --pid).
    """
    if pid is not None:
        sock_path = Path(socket_path_for_pid(pid))
        if sock_path.exists():
            return sock_path
        return None

    # Scan for any bridge sockets
    pattern = "/tmp/qt-ai-dev-tools-bridge-*.sock"  # noqa: S108
    sockets = sorted(glob.glob(pattern))

    if len(sockets) == 0:
        return None
    if len(sockets) == 1:
        return Path(sockets[0])

    # Multiple bridges found
    pids = [_extract_pid(s) for s in sockets]
    msg = f"Multiple bridges found (PIDs: {', '.join(pids)}). Specify --pid to choose one."
    raise RuntimeError(msg)


def _extract_pid(socket_path: str) -> str:
    """Extract PID from socket path like /tmp/qt-ai-dev-tools-bridge-1234.sock."""
    name = Path(socket_path).stem  # qt-ai-dev-tools-bridge-1234
    return name.rsplit("-", 1)[-1]


def eval_code(socket_path: Path, code: str, mode: EvalMode = "auto", timeout: float = 30.0) -> EvalResponse:
    """Send code to bridge server and return the response.

    Args:
        socket_path: Path to the bridge Unix socket.
        code: Python code to execute.
        mode: Execution mode ("auto", "eval", "exec").
        timeout: Socket timeout in seconds.

    Returns:
        EvalResponse with execution results.
    """
    request = EvalRequest(code=code, mode=mode)
    request_bytes = encode_request(request)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(socket_path))
        sock.sendall(request_bytes)

        # Read response (newline-delimited)
        data = b""
        while b"\n" not in data:
            if len(data) > _MAX_MESSAGE_SIZE:
                return EvalResponse(ok=False, error="Response too large")
            chunk = sock.recv(_RECV_BUFSIZE)
            if not chunk:
                return EvalResponse(ok=False, error="Bridge closed connection without response")
            data += chunk

        return decode_response(data.split(b"\n", 1)[0])
    except TimeoutError:
        return EvalResponse(ok=False, error=f"Bridge timeout ({timeout}s). App may be frozen.")
    except ConnectionRefusedError:
        return EvalResponse(ok=False, error=f"Bridge at {socket_path} refused connection (stale socket?).")
    except OSError as exc:
        return EvalResponse(ok=False, error=f"Bridge connection error: {exc}")
    finally:
        sock.close()


def bridge_status() -> list[dict[str, str]]:
    """List all active bridge sockets with PID info.

    Returns list of dicts with 'pid', 'socket_path', and 'alive' keys.
    """
    pattern = "/tmp/qt-ai-dev-tools-bridge-*.sock"  # noqa: S108
    sockets = sorted(glob.glob(pattern))

    result: list[dict[str, str]] = []
    for sock_path in sockets:
        pid = _extract_pid(sock_path)
        alive = _is_socket_alive(sock_path)
        result.append(
            {
                "pid": pid,
                "socket_path": sock_path,
                "alive": "yes" if alive else "stale",
            }
        )
    return result


def _is_socket_alive(socket_path: str) -> bool:
    """Check if a bridge socket is responsive by attempting connection."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        sock.connect(socket_path)
        return True
    except OSError:
        return False
    finally:
        sock.close()
