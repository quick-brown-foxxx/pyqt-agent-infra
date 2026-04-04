"""VM management -- Vagrant lifecycle and remote execution."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _find_workspace(workspace: Path | None = None) -> Path:
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


def _vagrant(args: list[str], workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run a vagrant command in the workspace directory."""
    return subprocess.run(
        ["vagrant", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def vm_up(workspace: Path | None = None, provider: str = "libvirt") -> subprocess.CompletedProcess[str]:
    """Start the VM (vagrant up)."""
    ws = _find_workspace(workspace)
    return _vagrant(["up", f"--provider={provider}"], ws)


def vm_status(workspace: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Check VM status."""
    ws = _find_workspace(workspace)
    return _vagrant(["status"], ws)


def vm_ssh(workspace: Path | None = None) -> None:
    """SSH into the VM (interactive)."""
    ws = _find_workspace(workspace)
    subprocess.run(["vagrant", "ssh"], cwd=ws, check=False)


def vm_destroy(workspace: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Destroy the VM."""
    ws = _find_workspace(workspace)
    return _vagrant(["destroy", "-f"], ws)


def vm_sync(workspace: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Sync files to VM via rsync."""
    ws = _find_workspace(workspace)
    return _vagrant(["rsync"], ws)


def vm_run(command: str, workspace: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command inside the VM with proper Qt/AT-SPI environment.

    Uses the vm-run.sh script if present, otherwise uses vagrant ssh -c.
    """
    ws = _find_workspace(workspace)
    vm_run_script = ws / "scripts" / "vm-run.sh"

    if vm_run_script.exists():
        return subprocess.run(
            [str(vm_run_script), command],
            cwd=ws,
            capture_output=True,
            text=True,
            check=False,
        )

    # Fallback: vagrant ssh with env vars
    env_prefix = (
        'export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_ACCESSIBILITY=1'
        ' QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1'
        ' DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus";'
    )
    return _vagrant(["ssh", "-c", f"{env_prefix} {command}"], ws)
