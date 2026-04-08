"""Workspace initialization — render Vagrant templates into a target directory."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path

from jinja2 import BaseLoader, Environment

_TEMPLATE_DIR = "qt_ai_dev_tools.vagrant.templates"

_TEMPLATES: dict[str, str] = {
    "Vagrantfile.j2": "Vagrantfile",
    "provision.sh.j2": "provision.sh",
}

_SHELL_SCRIPTS: set[str] = {"provision.sh"}


@dataclass(slots=True)
class WorkspaceConfig:
    """Configuration for workspace template rendering."""

    # Vagrantfile
    box: str = "bento/ubuntu-24.04"
    hostname: str = "qt-dev"
    provider: str = "libvirt"
    memory: int = 4096
    cpus: int = 4
    mac_address: str = ""
    management_network_name: str = "default"
    management_network_address: str = "192.168.122.0/24"
    static_ip: str = ""
    shared_folder: str = "../"
    rsync_excludes: list[str] = field(default_factory=lambda: [".git/", ".vagrant/", ".venv/"])
    # provision.sh
    display: str = ":99"
    resolution: str = "1920x1080x24"
    extra_packages: list[str] = field(default_factory=list)
    python_packages: list[str] = field(default_factory=lambda: ["basedpyright"])
    # VM naming (empty = auto-derive from project directory)
    vm_name: str = ""


def default_config() -> WorkspaceConfig:
    """Return a WorkspaceConfig with default values."""
    return WorkspaceConfig()


def derive_vm_name(workspace_path: Path) -> str:
    """Derive a VM name from the project directory containing the workspace.

    Uses the parent directory of the workspace (the project root).
    Sanitizes to lowercase alphanumeric + hyphens, prefixed with 'qt-dev-'.

    Args:
        workspace_path: Path to the workspace directory (e.g. <project>/.qt-ai-dev-tools).

    Returns:
        A sanitized VM name like 'qt-dev-my-project'.
    """
    project_dir = workspace_path.resolve().parent.name
    sanitized = re.sub(r"[^a-z0-9]+", "-", project_dir.lower()).strip("-")
    if not sanitized:
        sanitized = "default"
    return f"qt-dev-{sanitized}"


def _load_template(name: str) -> str:
    """Load a template file from the package resources."""
    templates_pkg = importlib_resources.files(_TEMPLATE_DIR)
    template_file = templates_pkg.joinpath(name)
    return template_file.read_text(encoding="utf-8")


def render_workspace(target: Path, config: WorkspaceConfig | None = None) -> list[Path]:
    """Render all Vagrant templates into the target directory.

    Creates the target directory and a scripts/ subdirectory as needed.
    Shell scripts (.sh) are made executable (mode 0o755).

    Args:
        target: Directory to write rendered files into.
        config: Workspace configuration. Uses defaults if None.

    Returns:
        List of paths to created files.
    """
    if config is None:
        config = default_config()

    env = Environment(loader=BaseLoader(), keep_trailing_newline=True)  # noqa: S701 — generating shell scripts, not HTML
    context = asdict(config)
    if not context["vm_name"]:
        context["vm_name"] = derive_vm_name(target)

    created: list[Path] = []

    for template_name, output_rel in _TEMPLATES.items():
        template_str = _load_template(template_name)
        template = env.from_string(template_str)
        rendered = template.render(context)

        output_path = target / output_rel
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")

        if output_rel in _SHELL_SCRIPTS:
            output_path.chmod(0o755)

        created.append(output_path)

    return created
