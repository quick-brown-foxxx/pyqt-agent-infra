"""E2E test fixtures: real Qt app with bridge running."""

from __future__ import annotations

import glob as glob_mod
import os
import signal
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest

# Skip entire directory if not in VM (no DISPLAY means no Xvfb)
pytestmark = pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
)

_SOCKET_GLOB = "/tmp/qt-ai-dev-tools-bridge-*.sock"


def _clean_stale_sockets() -> None:
    """Remove any leftover bridge sockets."""
    for sock in glob_mod.glob(_SOCKET_GLOB):
        Path(sock).unlink(missing_ok=True)


@pytest.fixture(scope="module")
def bridge_app() -> Generator[subprocess.Popen[str], None, None]:
    """Start the sample app with bridge enabled, yield process, then kill.

    Module-scoped: the app is started once per test module, shared across tests.
    """
    _clean_stale_sockets()

    # Start the sample app with bridge enabled
    app_path = Path(__file__).parent.parent.parent / "app" / "main.py"
    env = {**os.environ, "QT_AI_DEV_TOOLS_BRIDGE": "1"}
    proc = subprocess.Popen(
        ["python3", str(app_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for bridge socket to appear
    socket_found = False
    deadline = time.monotonic() + 15.0
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
        time.sleep(0.3)

    if not socket_found:
        proc.kill()
        stdout = proc.stdout.read() if proc.stdout else ""
        stderr = proc.stderr.read() if proc.stderr else ""
        proc.wait(timeout=5)
        pytest.fail(f"Bridge socket did not appear within 15s.\nstdout: {stdout}\nstderr: {stderr}")

    yield proc

    # Teardown: kill the app
    proc.send_signal(signal.SIGKILL)
    proc.wait(timeout=5)
    _clean_stale_sockets()
