"""Bootstrap: sys.remote_exec bridge injection for Python 3.14+."""

from __future__ import annotations

import glob as glob_mod
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from qt_ai_dev_tools.bridge._protocol import socket_path_for_pid
from qt_ai_dev_tools.run import run_command

logger = logging.getLogger(__name__)

# Bootstrap script template injected into the target process.
# This runs inside the target app's interpreter via sys.remote_exec (PEP 768).
_BOOTSTRAP_TEMPLATE = """\
# qt-ai-dev-tools bridge bootstrap
# Injected via sys.remote_exec() (Python 3.14+, PEP 768)
import sys
sys.path.insert(0, {package_path!r})
from qt_ai_dev_tools.bridge._server import BridgeExecutor, BridgeServer

executor = BridgeExecutor()
server = BridgeServer(executor)
server.start()
"""


def can_remote_exec() -> bool:
    """Check if the current Python has sys.remote_exec (3.14+)."""
    return sys.version_info >= (3, 14) and hasattr(sys, "remote_exec")


def detect_python_version(pid: int) -> tuple[int, int]:
    """Detect the Python version of a running process.

    Reads /proc/<pid>/exe to find the Python binary, then runs --version.

    Raises:
        RuntimeError: If version cannot be detected.
    """
    exe_link = Path(f"/proc/{pid}/exe")
    if not exe_link.exists():
        msg = f"Process {pid} not found (no /proc/{pid}/exe)"
        raise RuntimeError(msg)

    try:
        exe_path = exe_link.resolve(strict=True)
    except OSError as exc:
        msg = f"Cannot read /proc/{pid}/exe: {exc}"
        raise RuntimeError(msg) from exc

    try:
        result = run_command([str(exe_path), "--version"], timeout=5)
    except RuntimeError as exc:
        msg = f"Cannot determine Python version for PID {pid}: {exc}"
        raise RuntimeError(msg) from exc

    # Parse "Python X.Y.Z" from stdout or stderr
    version_text = result.stdout.strip() or result.stderr.strip()
    if not version_text.startswith("Python "):
        msg = f"Not a Python process (PID {pid}): {version_text}"
        raise RuntimeError(msg)

    parts = version_text.split()[1].split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError) as exc:
        msg = f"Cannot parse Python version from '{version_text}'"
        raise RuntimeError(msg) from exc


def _find_package_path() -> str:
    """Find the qt_ai_dev_tools package path for bootstrap injection."""
    import qt_ai_dev_tools

    pkg_path = Path(qt_ai_dev_tools.__file__).parent.parent
    return str(pkg_path)


def _write_bootstrap_script(pid: int) -> Path:
    """Write the bootstrap script to a temp file.

    Returns the path to the script (caller is responsible for cleanup).
    """
    package_path = _find_package_path()
    script = _BOOTSTRAP_TEMPLATE.format(package_path=package_path)

    # Write to a temp file that the target process can read (mkstemp for safe creation)
    fd, path_str = tempfile.mkstemp(prefix=f"qt-ai-dev-tools-bootstrap-{pid}-", suffix=".py")
    os.fchmod(fd, 0o600)  # restrict to owner (same uid as target process)
    with os.fdopen(fd, "w") as f:
        f.write(script)
    script_path = Path(path_str)
    return script_path


def wait_for_socket(pid: int, timeout: float = 5.0, poll_interval: float = 0.1) -> Path:
    """Poll for the bridge socket file to appear.

    Args:
        pid: Target process PID.
        timeout: Maximum wait time in seconds.
        poll_interval: Time between checks in seconds.

    Returns:
        Path to the socket file.

    Raises:
        RuntimeError: If socket does not appear within timeout.
    """
    sock_path = Path(socket_path_for_pid(pid))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if sock_path.exists():
            return sock_path
        time.sleep(poll_interval)
    msg = f"Bridge socket did not appear within {timeout}s for PID {pid}"
    raise RuntimeError(msg)


def inject_bridge(pid: int | None = None) -> Path:
    """Inject the bridge into a running Python 3.14+ process.

    If pid is None, attempts to auto-discover a Qt application process.

    Returns the socket path on success.

    Raises:
        RuntimeError: If injection fails for any reason.
    """
    if pid is None:
        pid = _discover_qt_process()

    # Check if bridge is already running
    sock_path = Path(socket_path_for_pid(pid))
    if sock_path.exists():
        logger.info("Bridge already active for PID %d", pid)
        return sock_path

    # Check Python version of target process
    major, minor = detect_python_version(pid)
    if (major, minor) < (3, 14):
        msg = (
            f"Target app is Python {major}.{minor} — automatic injection requires Python 3.14+.\n"
            "\n"
            "Add this to your app to enable the bridge:\n"
            "  from qt_ai_dev_tools.bridge import start; start()\n"
            "\n"
            "Or set QT_AI_DEV_TOOLS_BRIDGE=1 if bridge.start() is already in the code."
        )
        raise RuntimeError(msg)

    # Check if current Python supports remote_exec
    if not can_remote_exec():
        msg = (
            "sys.remote_exec not available in current Python. "
            "Run this command from Python 3.14+ to inject into the target process."
        )
        raise RuntimeError(msg)

    # Write and inject bootstrap script
    script_path = _write_bootstrap_script(pid)
    try:
        logger.info("Injecting bridge into PID %d via sys.remote_exec", pid)
        sys.remote_exec(pid, str(script_path))  # type: ignore[attr-defined]  # rationale: sys.remote_exec is Python 3.14+ only, guarded by can_remote_exec()

        # Wait for socket to appear
        return wait_for_socket(pid)
    finally:
        # Clean up bootstrap script
        if script_path.exists():
            script_path.unlink()


def _discover_qt_process() -> int:
    """Auto-discover a running Qt application process.

    Looks for processes with an existing bridge socket whose PID is still alive.

    Raises:
        RuntimeError: If no Qt process found.
    """
    pattern = "/tmp/qt-ai-dev-tools-bridge-*.sock"  # noqa: S108
    sockets = glob_mod.glob(pattern)
    if sockets:
        # Extract PIDs and check which are alive
        for sock in sockets:
            pid_str = Path(sock).stem.rsplit("-", 1)[-1]
            try:
                pid = int(pid_str)
                os.kill(pid, 0)  # check if process exists
                return pid
            except (ValueError, ProcessLookupError, PermissionError):
                continue

    msg = (
        "Cannot auto-discover Qt process. Specify --pid explicitly.\n"
        "\n"
        "To find the PID of your Qt app:\n"
        "  ps aux | grep python"
    )
    raise RuntimeError(msg)
