"""Integration test fixtures: start sample Qt app for CLI tests."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest

_MAIN_APP_PATH = Path(__file__).parent.parent.parent / "app" / "main.py"

_APP_STARTUP_TIMEOUT = 25.0
_APP_POLL_INTERVAL = 0.5


def _wait_for_app_on_atspi(
    proc: subprocess.Popen[str],
    search_term: str,
    timeout: float = _APP_STARTUP_TIMEOUT,
) -> None:
    """Wait until the app appears on the AT-SPI desktop."""
    deadline = time.monotonic() + timeout
    term_lower = search_term.lower()
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stdout = proc.stdout.read() if proc.stdout else ""
            stderr = proc.stderr.read() if proc.stderr else ""
            pytest.fail(f"App exited early (code {proc.returncode}).\nstdout: {stdout}\nstderr: {stderr}")

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

        time.sleep(_APP_POLL_INTERVAL)

    proc.kill()
    proc.wait(timeout=5)
    pytest.fail(f"App '{search_term}' did not appear on AT-SPI within {timeout}s")


@pytest.fixture(scope="session", autouse=True)
def sample_app() -> Generator[subprocess.Popen[str] | None, None, None]:
    """Start the sample Qt app for integration CLI tests.

    Session-scoped and autouse so it is available for all integration tests.
    Skips app startup when DISPLAY is not set (tests will be skipped anyway).
    """
    if not os.environ.get("DISPLAY"):
        yield None
        return

    env = dict(os.environ)
    env.setdefault("DISPLAY", ":99")
    env.setdefault("QT_QPA_PLATFORM", "xcb")
    env.setdefault("QT_ACCESSIBILITY", "1")
    env.setdefault("QT_LINUX_ACCESSIBILITY_ALWAYS_ON", "1")

    proc = subprocess.Popen(
        ["python3", str(_MAIN_APP_PATH)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    _wait_for_app_on_atspi(proc, "main.py")

    yield proc

    if proc.poll() is None:
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=5)
