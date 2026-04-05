"""E2E test fixtures: real Qt app with bridge running."""

from __future__ import annotations

import glob as glob_mod
import importlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Skip entire directory if not in VM (no DISPLAY means no Xvfb)
pytestmark = pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
)


@pytest.fixture(scope="session", autouse=True)
def _ensure_real_atspi() -> None:
    """Reload _atspi module to clear any mocks leaked from unit tests.

    Unit tests in ``tests/unit/test_atspi.py`` inject mock ``gi`` modules at
    module level via ``sys.modules.setdefault``.  If unit tests run before e2e
    tests in the same pytest process, the ``qt_ai_dev_tools._atspi`` module
    holds a reference to the mocked ``Atspi`` forever.  This fixture detects
    that contamination and forces a reload with the real ``gi`` bindings.
    """
    import qt_ai_dev_tools._atspi as _atspi_mod

    if isinstance(getattr(_atspi_mod, "Atspi", None), MagicMock):
        # Remove mock gi modules so the real ones get imported on reload
        for mod_name in ["gi", "gi.repository", "gi.repository.Atspi"]:
            if mod_name in sys.modules and isinstance(sys.modules[mod_name], MagicMock):
                del sys.modules[mod_name]
        importlib.reload(_atspi_mod)


_SOCKET_GLOB = "/tmp/qt-ai-dev-tools-bridge-*.sock"
_APPS_DIR = Path(__file__).parent.parent / "apps"
_MAIN_APP_PATH = Path(__file__).parent.parent.parent / "app" / "main.py"

# How long to wait for an app to become visible on AT-SPI
_APP_STARTUP_TIMEOUT = 25.0
_APP_POLL_INTERVAL = 0.5


def _clean_stale_sockets() -> None:
    """Remove any leftover bridge sockets."""
    for sock in glob_mod.glob(_SOCKET_GLOB):
        Path(sock).unlink(missing_ok=True)


def _start_app(
    app_path: Path,
    *,
    bridge: bool = False,
) -> subprocess.Popen[str]:
    """Start a PySide6 test app as a subprocess.

    Args:
        app_path: Path to the Python app file.
        bridge: Whether to enable the bridge env var.

    Returns:
        The started Popen process.
    """
    env = dict(os.environ)
    # Ensure DISPLAY is set for Xvfb (critical for AT-SPI visibility)
    env.setdefault("DISPLAY", ":99")
    env.setdefault("QT_QPA_PLATFORM", "xcb")
    env.setdefault("QT_ACCESSIBILITY", "1")
    env.setdefault("QT_LINUX_ACCESSIBILITY_ALWAYS_ON", "1")
    if bridge:
        env["QT_AI_DEV_TOOLS_BRIDGE"] = "1"

    return subprocess.Popen(
        ["python3", str(app_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_for_app_window(
    proc: subprocess.Popen[str],
    search_term: str,
    timeout: float = _APP_STARTUP_TIMEOUT,
) -> None:
    """Wait until an app window appears on the AT-SPI desktop.

    Searches both AT-SPI application names (e.g. script filenames like
    ``file_dialog_app.py``) and the widget tree output (which contains
    window titles).

    Args:
        proc: The app subprocess.
        search_term: Substring to match against AT-SPI app names **or**
            window titles in the widget tree.
        timeout: Maximum seconds to wait.

    Raises:
        pytest.fail: If the app exits early or the window never appears.
    """
    deadline = time.monotonic() + timeout
    term_lower = search_term.lower()
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stdout = proc.stdout.read() if proc.stdout else ""
            stderr = proc.stderr.read() if proc.stderr else ""
            pytest.fail(f"App exited early (code {proc.returncode}).\nstdout: {stdout}\nstderr: {stderr}")

        # Strategy 1: check AT-SPI app names (matches script filenames)
        apps_result = subprocess.run(
            ["python3", "-m", "qt_ai_dev_tools", "apps"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if term_lower in apps_result.stdout.lower():
            time.sleep(0.5)
            return

        # Strategy 2: check the widget tree for window titles
        tree_result = subprocess.run(
            ["python3", "-m", "qt_ai_dev_tools", "tree"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if term_lower in tree_result.stdout.lower():
            time.sleep(0.5)
            return

        time.sleep(_APP_POLL_INTERVAL)

    proc.kill()
    proc.wait(timeout=5)
    pytest.fail(f"Window '{search_term}' did not appear within {timeout}s")


def _kill_app(proc: subprocess.Popen[str]) -> None:
    """Kill an app subprocess and wait for it to exit."""
    if proc.poll() is None:
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=5)


@pytest.fixture(scope="module")
def bridge_app() -> Generator[subprocess.Popen[str], None, None]:
    """Start the sample app with bridge enabled, yield process, then kill.

    Module-scoped: the app is started once per test module, shared across tests.
    """
    _clean_stale_sockets()

    proc = _start_app(_MAIN_APP_PATH, bridge=True)

    # Wait for bridge socket to appear
    socket_found = False
    deadline = time.monotonic() + _APP_STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        sockets = glob_mod.glob(_SOCKET_GLOB)
        if sockets:
            socket_found = True
            break
        # Check if process died early
        if proc.poll() is not None:
            stdout = proc.stdout.read() if proc.stdout else ""
            stderr = proc.stderr.read() if proc.stderr else ""
            pytest.fail(f"App exited early (code {proc.returncode}).\nstdout: {stdout}\nstderr: {stderr}")
        time.sleep(_APP_POLL_INTERVAL)

    if not socket_found:
        proc.kill()
        stdout = proc.stdout.read() if proc.stdout else ""
        stderr = proc.stderr.read() if proc.stderr else ""
        proc.wait(timeout=5)
        pytest.fail(f"Bridge socket did not appear within {_APP_STARTUP_TIMEOUT}s.\nstdout: {stdout}\nstderr: {stderr}")

    yield proc

    _kill_app(proc)
    _clean_stale_sockets()


@pytest.fixture(scope="module")
def file_dialog_app() -> Generator[subprocess.Popen[str], None, None]:
    """Start the file dialog test app, yield process, then kill."""
    app_path = _APPS_DIR / "file_dialog_app.py"
    proc = _start_app(app_path, bridge=True)
    _wait_for_app_window(proc, "file_dialog_app.py")  # AT-SPI app name, not window title
    yield proc
    _kill_app(proc)


def _is_process_running(name: str) -> bool:
    """Check if a process with the given name is running."""
    result = subprocess.run(["pgrep", name], capture_output=True, check=False)
    return result.returncode == 0


def _wait_for_process(name: str, timeout: float = 5.0) -> None:
    """Wait until a process with the given name is running."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_process_running(name):
            return
        time.sleep(0.3)
    pytest.fail(f"Process '{name}' did not start within {timeout}s")


def _wait_for_tray_embedding(app_name: str, timeout: float = 10.0) -> None:
    """Wait until a tray icon for app_name appears embedded in stalonetray.

    Polls xwininfo -tree on the stalonetray window until a child window
    with a WM_CLASS matching app_name appears. This confirms that
    snixembed has proxied the SNI icon into the XEmbed tray.

    Args:
        app_name: Application name to match in WM_CLASS (case-insensitive).
        timeout: Maximum seconds to wait.

    Raises:
        pytest.fail: If the icon never appears.
    """
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":99")}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # Find stalonetray window ID
        result = subprocess.run(
            ["xdotool", "search", "--class", "stalonetray"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        wid = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        if not wid:
            time.sleep(0.5)
            continue

        # Check xwininfo tree for the embedded icon
        tree_result = subprocess.run(
            ["xwininfo", "-tree", "-id", wid],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if app_name.lower() in tree_result.stdout.lower():
            return

        time.sleep(0.5)

    pytest.fail(f"Tray icon for '{app_name}' not embedded in stalonetray within {timeout}s")


@pytest.fixture(scope="module")
def clean_sni_watcher() -> Generator[None, None, None]:
    """Ensure stalonetray is running and restart snixembed to clear stale SNI entries.

    stalonetray provides the XEmbed tray window (needed for xdotool icon clicks).
    It is stable from the desktop-session service and does not need restarting.
    Only snixembed (the SNI D-Bus watcher) needs restart to clear stale entries.

    If stalonetray is not running (e.g. killed during manual testing), it is
    started fresh. snixembed is always killed and restarted.
    """
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":99")}

    # Ensure stalonetray is running (don't kill it — avoid XEmbed timing issues)
    if not _is_process_running("stalonetray"):
        subprocess.Popen(
            ["stalonetray", "--kludges=force_icons_size", "-i", "24", "--grow-gravity=NE"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        _wait_for_process("stalonetray")

    # Always restart snixembed to clear stale SNI entries
    subprocess.run(["killall", "snixembed"], capture_output=True, check=False)
    time.sleep(0.5)
    subprocess.Popen(
        ["snixembed", "--fork"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    time.sleep(1.0)  # wait for D-Bus registration
    yield
    # Kill any leftover test app processes that might leave stale SNI entries
    subprocess.run(["pkill", "-f", "tray_app.py"], capture_output=True, check=False)
    time.sleep(0.3)


@pytest.fixture(scope="module")
def tray_app(clean_sni_watcher: None) -> Generator[subprocess.Popen[str], None, None]:
    """Start the tray test app, yield process, then kill."""
    app_path = _APPS_DIR / "tray_app.py"
    proc = _start_app(app_path, bridge=True)
    _wait_for_app_window(proc, "tray_app.py")  # AT-SPI app name, not window title
    # Wait for snixembed to proxy the icon into stalonetray (XEmbed embedding)
    # Without this, xdotool right-click on the icon fails because the icon
    # isn't yet a child window of stalonetray.
    _wait_for_tray_embedding("tray_app")
    yield proc
    _kill_app(proc)


@pytest.fixture(scope="module")
def audio_app() -> Generator[subprocess.Popen[str], None, None]:
    """Start the audio test app, yield process, then kill."""
    app_path = _APPS_DIR / "audio_app.py"
    proc = _start_app(app_path, bridge=True)
    _wait_for_app_window(proc, "audio_app.py")  # AT-SPI app name, not window title
    yield proc
    _kill_app(proc)


@pytest.fixture(scope="module")
def stt_app() -> Generator[subprocess.Popen[str], None, None]:
    """Start the STT test app, yield process, then kill."""
    app_path = _APPS_DIR / "stt_app.py"
    proc = _start_app(app_path, bridge=True)
    _wait_for_app_window(proc, "stt_app.py")  # AT-SPI app name, not window title
    yield proc
    _kill_app(proc)
