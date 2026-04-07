"""E2E tests for bridge CLI via host-to-VM execution.

These run ON THE HOST and verify that bridge commands execute in the VM.
Requires: VM running, app with bridge started inside VM.

Run via: make test-e2e-proxy (or pytest tests/e2e/test_bridge_proxy.py)
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest


def _vagrant_running() -> bool:
    """Check if Vagrant VM is running for this project."""
    try:
        result = subprocess.run(
            ["vagrant", "status", "--machine-readable"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return "state,running" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _vm_run(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run a command inside the VM."""
    return subprocess.run(
        ["uv", "run", "qt-ai-dev-tools", "vm", "run", command],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _host_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run qt-ai-dev-tools on the host (executes in VM via SSH)."""
    return subprocess.run(
        ["uv", "run", "qt-ai-dev-tools", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


# Skip if VM not running or no Vagrantfile
pytestmark = [
    pytest.mark.skipif(
        not Path("Vagrantfile").exists(),
        reason="No Vagrantfile — run 'qt-ai-dev-tools workspace init' first",
    ),
    pytest.mark.skipif(
        os.environ.get("QT_AI_DEV_TOOLS_VM") == "1",
        reason="Already inside VM — these tests run from the host",
    ),
    pytest.mark.e2e,
]


@pytest.fixture(scope="module")
def vm_bridge_app() -> None:
    """Ensure VM is running with app + bridge.

    Starts the sample app in the VM if not already running.
    Module-scoped: runs once per test module.
    """
    if not _vagrant_running():
        pytest.skip("Vagrant VM is not running")

    # Sync latest code
    subprocess.run(
        ["uv", "run", "qt-ai-dev-tools", "vm", "sync"],
        capture_output=True,
        timeout=30,
        check=False,
    )

    # Check if app is already running with a live bridge
    check = _host_cli("eval", "1+1", timeout=10)
    if check.returncode == 0 and "2" in check.stdout:
        return  # Bridge already running and responsive

    # Stop any existing app service and clean up stale sockets.
    _vm_run("systemctl --user stop test-bridge-app 2>/dev/null || true")
    _vm_run("pkill -9 -f 'python3.*main.py' 2>/dev/null || true")
    time.sleep(1)
    _vm_run("rm -f /tmp/qt-ai-dev-tools-bridge-*.sock")

    # Start the app as a transient systemd user service.
    # This properly daemonizes the process so SSH can exit immediately.
    # Using vagrant ssh -c "... &" hangs because SSH keeps the connection
    # open while the background process holds file descriptors.
    start = _vm_run(
        "systemd-run --user --unit=test-bridge-app"
        " --property=Environment=DISPLAY=:99"
        " --property=Environment=QT_AI_DEV_TOOLS_BRIDGE=1"
        " --property=Environment=QT_QPA_PLATFORM=xcb"
        " --property=Environment=QT_ACCESSIBILITY=1"
        " --property=Environment=QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1"
        " --property=Environment=UV_PROJECT_ENVIRONMENT=/home/vagrant/.venv-qt-ai-dev-tools"
        " --property=Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
        " --property=WorkingDirectory=/vagrant"
        " /home/vagrant/.venv-qt-ai-dev-tools/bin/python3 app/main.py",
        timeout=10,
    )
    if start.returncode != 0:
        pytest.fail(f"Failed to start app service: {start.stderr}")

    # Wait for bridge socket to appear
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        check = _vm_run("ls /tmp/qt-ai-dev-tools-bridge-*.sock 2>/dev/null", timeout=5)
        if check.returncode == 0 and check.stdout.strip():
            return
        time.sleep(0.5)

    # Debug info on failure
    log = _vm_run("journalctl --user -u test-bridge-app --no-pager -n 30 2>/dev/null")
    ps = _vm_run("systemctl --user status test-bridge-app 2>/dev/null")
    pytest.fail(f"Bridge socket did not appear within 15s.\nService status: {ps.stdout}\nJournal: {log.stdout}")


class TestBridgeProxy:
    """Test bridge commands via transparent VM proxy (host -> VM)."""

    def test_eval_proxies_to_vm(self, vm_bridge_app: None) -> None:
        """eval command auto-proxies from host to VM."""
        result = _host_cli("eval", "1 + 1")
        assert result.returncode == 0
        assert "2" in result.stdout

    def test_eval_json_proxy(self, vm_bridge_app: None) -> None:
        """eval --json via proxy returns valid JSON."""
        result = _host_cli("eval", "--json", "1 + 1")
        assert result.returncode == 0
        raw: object = json.loads(result.stdout)  # type: ignore[reportAny]  # rationale: json.loads returns Any
        assert isinstance(raw, dict)
        assert raw["ok"] is True
        assert raw["result"] == "2"

    def test_bridge_status_proxy(self, vm_bridge_app: None) -> None:
        """bridge status works from host via proxy."""
        result = _host_cli("bridge", "status")
        assert result.returncode == 0
        # Should show at least one bridge
        output = result.stdout.lower()
        assert "pid" in output or "no active" not in output

    def test_eval_widget_access_proxy(self, vm_bridge_app: None) -> None:
        """eval can access widgets via proxy."""
        result = _host_cli("eval", "list(widgets.keys())")
        assert result.returncode == 0
        assert "MainWindow" in result.stdout
