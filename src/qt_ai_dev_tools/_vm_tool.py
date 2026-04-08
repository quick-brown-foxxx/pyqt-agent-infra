"""VM tool readiness check — ensures qt-ai-dev-tools in the VM is current.

Two install modes:
- PYPI: tool installed from PyPI, checked by version string comparison
- LOCAL: tool installed from local install-and-own copy, checked by source hash
"""

from __future__ import annotations

import enum
import hashlib
import logging
import subprocess
from pathlib import Path

from qt_ai_dev_tools.__version__ import __version__
from qt_ai_dev_tools._env import ALLOW_VERSION_MISMATCH, VM, get_bool

logger = logging.getLogger(__name__)

_HASH_MARKER = "/home/vagrant/.local/state/qt-ai-dev-tools/source-hash"


class InstallMode(enum.Enum):
    """How qt-ai-dev-tools was installed in the VM."""

    PYPI = "pypi"
    LOCAL = "local"


class ToolVersionMismatchError(Exception):
    """Raised when host and VM tool versions don't match."""


def _detect_install_mode(project_root: Path) -> InstallMode:
    """Detect whether the project uses a local install-and-own copy or PyPI."""
    local_src = project_root / ".qt-ai-dev-tools" / "src" / "qt_ai_dev_tools"
    if local_src.is_dir():
        return InstallMode.LOCAL
    return InstallMode.PYPI


def _get_vm_tool_version(workspace: Path) -> str | None:
    """Query the VM for qt-ai-dev-tools version.

    Returns the version string (e.g. "0.6.2") or None on failure.
    """
    from qt_ai_dev_tools.vagrant.vm import vm_run

    try:
        result = vm_run("qt-ai-dev-tools --version", workspace)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None

    stdout = result.stdout.strip()
    if not stdout.startswith("qt-ai-dev-tools "):
        return None
    return stdout.removeprefix("qt-ai-dev-tools ").strip() or None


def _compute_source_hash(toolkit_dir: Path) -> str:
    """SHA-256 hash of all ``*.py`` files under ``toolkit_dir/src/qt_ai_dev_tools``.

    Returns empty string if the directory doesn't exist.
    """
    src_dir = toolkit_dir / "src" / "qt_ai_dev_tools"
    if not src_dir.is_dir():
        return ""

    py_files = sorted(src_dir.rglob("*.py"))
    if not py_files:
        return ""

    hasher = hashlib.sha256()
    for py_file in py_files:
        # Include relative path so renames change the hash
        rel = py_file.relative_to(src_dir)
        hasher.update(str(rel).encode())
        hasher.update(py_file.read_bytes())
    return hasher.hexdigest()


def _check_pypi_mode(workspace: Path) -> None:
    """Verify VM tool version matches host version (PyPI install)."""
    vm_version = _get_vm_tool_version(workspace)
    if vm_version is None:
        msg = "qt-ai-dev-tools is not installed in the VM"
        raise ToolVersionMismatchError(msg)

    if vm_version == __version__:
        logger.debug("VM tool version %s matches host", vm_version)
        return

    if get_bool(ALLOW_VERSION_MISMATCH):
        logger.warning(
            "VM tool version %s != host version %s (mismatch allowed)",
            vm_version,
            __version__,
        )
        return

    msg = f"VM tool version {vm_version} != host version {__version__}"
    raise ToolVersionMismatchError(msg)


def _check_local_mode(project_root: Path, workspace: Path) -> None:
    """Verify local install-and-own copy is up to date in the VM."""
    from qt_ai_dev_tools.vagrant.vm import vm_run

    toolkit_dir = project_root / ".qt-ai-dev-tools"
    current_hash = _compute_source_hash(toolkit_dir)

    # Read stored hash from VM
    try:
        result = vm_run(f"cat {_HASH_MARKER}", workspace)
        stored_hash = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        stored_hash = ""

    if stored_hash == current_hash and current_hash:
        logger.debug("Local toolkit hash matches VM — up to date")
        return

    logger.info("Local toolkit changed — rebuilding in VM")
    vm_run("uv tool install --force /vagrant/.qt-ai-dev-tools/", workspace)

    # Write new hash marker
    marker_dir = str(Path(_HASH_MARKER).parent)
    vm_run(f"mkdir -p {marker_dir} && echo '{current_hash}' | tee {_HASH_MARKER}", workspace)
    logger.info("VM tool updated, hash marker written")


def ensure_tool_ready(project_root: Path, workspace: Path | None = None) -> None:
    """Ensure the VM has a current qt-ai-dev-tools installation.

    Skips entirely when running inside the VM. Otherwise detects install
    mode and checks version/hash accordingly.
    """
    if get_bool(VM):
        return

    from qt_ai_dev_tools.vagrant.vm import find_workspace

    ws = find_workspace(workspace)
    mode = _detect_install_mode(project_root)

    if mode is InstallMode.PYPI:
        _check_pypi_mode(ws)
    else:
        _check_local_mode(project_root, ws)
