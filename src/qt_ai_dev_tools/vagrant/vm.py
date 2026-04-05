"""VM management -- Vagrant lifecycle and remote execution."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def find_workspace(workspace: Path | None = None) -> Path:
    """Find workspace directory containing Vagrantfile.

    If workspace is given, use it. Otherwise walk up from cwd looking for
    a directory containing Vagrantfile.
    """
    if workspace is not None:
        vf = workspace / "Vagrantfile"
        if not vf.exists():
            msg = f"No Vagrantfile found in {workspace}"
            raise FileNotFoundError(msg)
        return workspace

    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "Vagrantfile").exists():
            return parent
    msg = "No Vagrantfile found in current directory or parents"
    raise FileNotFoundError(msg)


def _vagrant(args: list[str], workspace: Path, *, stream: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a vagrant command in the workspace directory."""
    from qt_ai_dev_tools.run import run_command

    return run_command(["vagrant", *args], cwd=workspace, stream=stream)


def vm_up(
    workspace: Path | None = None, provider: str = "libvirt", *, stream: bool = False
) -> subprocess.CompletedProcess[str]:
    """Start the VM (vagrant up)."""
    ws = find_workspace(workspace)
    return _vagrant(["up", f"--provider={provider}"], ws, stream=stream)


def vm_status(workspace: Path | None = None, *, stream: bool = False) -> subprocess.CompletedProcess[str]:
    """Check VM status."""
    ws = find_workspace(workspace)
    return _vagrant(["status"], ws, stream=stream)


def vm_ssh(workspace: Path | None = None) -> None:
    """SSH into the VM (interactive)."""
    ws = find_workspace(workspace)
    logger.info("$ vagrant ssh (interactive)")
    proc = subprocess.Popen(["vagrant", "ssh"], cwd=ws)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def vm_destroy(workspace: Path | None = None, *, stream: bool = False) -> subprocess.CompletedProcess[str]:
    """Destroy the VM."""
    ws = find_workspace(workspace)
    return _vagrant(["destroy", "-f"], ws, stream=stream)


def vm_sync(workspace: Path | None = None, *, stream: bool = False) -> subprocess.CompletedProcess[str]:
    """Sync files to VM via rsync."""
    ws = find_workspace(workspace)
    return _vagrant(["rsync"], ws, stream=stream)


def vm_sync_auto(workspace: Path | None = None) -> subprocess.Popen[str]:
    """Start background rsync-auto to keep VM files in sync.

    Returns the Popen handle so caller can stop it later.
    """
    ws = find_workspace(workspace)
    logger.info("$ vagrant rsync-auto (background)")
    return subprocess.Popen(
        ["vagrant", "rsync-auto"],
        cwd=ws,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def vm_run(
    command: str, workspace: Path | None = None, display: str = ":99", *, stream: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run a command inside the VM with proper Qt/AT-SPI environment."""
    if not re.fullmatch(r":\d+(\.\d+)?", display):
        msg = f"Invalid display format: {display!r} (expected ':N' or ':N.M')"
        raise ValueError(msg)
    ws = find_workspace(workspace)
    env_prefix = (
        f"export DISPLAY={display} QT_QPA_PLATFORM=xcb QT_ACCESSIBILITY=1"
        " QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1"
        " QT_AI_DEV_TOOLS_VM=1"
        " UV_PROJECT_ENVIRONMENT=$HOME/.venv-qt-ai-dev-tools"
        " PATH=$HOME/.venv-qt-ai-dev-tools/bin:$PATH"
        ' DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus";'
    )
    return _vagrant(["ssh", "-c", f"{env_prefix} {command}"], ws, stream=stream)
