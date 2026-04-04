"""E2E tests for bridge CLI via transparent VM proxy.

These run ON THE HOST and verify that bridge commands auto-proxy to the VM.
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
    """Run qt-ai-dev-tools on the host (will auto-proxy to VM)."""
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

    # Kill any existing app instances and stale sockets
    _vm_run("pkill -f 'python3 app/main.py' 2>/dev/null || true")
    time.sleep(1)
    _vm_run("rm -f /tmp/qt-ai-dev-tools-bridge-*.sock")

    # Start the app with bridge enabled (use Popen — vm run with & hangs over SSH)
    subprocess.Popen(
        [
            "uv",
            "run",
            "qt-ai-dev-tools",
            "vm",
            "run",
            "cd /vagrant && QT_AI_DEV_TOOLS_BRIDGE=1 nohup python3 app/main.py > /tmp/app-test.log 2>&1 &",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for bridge socket to appear
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        check = _vm_run("ls /tmp/qt-ai-dev-tools-bridge-*.sock 2>/dev/null")
        if check.returncode == 0 and check.stdout.strip():
            return
        time.sleep(0.5)

    # Get debug info on failure
    log = _vm_run("cat /tmp/app-test.log 2>/dev/null")
    pytest.fail(f"Bridge socket did not appear within 15s.\nApp log: {log.stdout}")


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
