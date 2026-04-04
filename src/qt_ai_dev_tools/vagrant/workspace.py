"""Workspace initialization — render Vagrant templates into a target directory."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path

from jinja2 import BaseLoader, Environment

_TEMPLATE_DIR = "qt_ai_dev_tools.vagrant.templates"

_TEMPLATES: dict[str, str] = {
    "Vagrantfile.j2": "Vagrantfile",
    "provision.sh.j2": "provision.sh",
    "vm-run.sh.j2": "scripts/vm-run.sh",
    "screenshot.sh.j2": "scripts/screenshot.sh",
}

_SHELL_SCRIPTS: set[str] = {"provision.sh", "scripts/vm-run.sh", "scripts/screenshot.sh"}


@dataclass(slots=True)
class WorkspaceConfig:
    """Configuration for workspace template rendering."""

    # Vagrantfile
    box: str = "bento/ubuntu-24.04"
    hostname: str = "qt-dev"
    provider: str = "libvirt"
    memory: int = 4096
    cpus: int = 4
    mac_address: str = "52:54:00:AB:CD:EF"
    static_ip: str = ""
    shared_folder: str = "."
    rsync_excludes: list[str] = field(default_factory=lambda: [".git/", ".vagrant/"])
    # provision.sh
    display: str = ":99"
    resolution: str = "1920x1080x24"
    extra_packages: list[str] = field(default_factory=list)
    python_packages: list[str] = field(
        default_factory=lambda: ["PySide6", "pytest", "pytest-qt", "python-dbusmock"]
    )


def default_config() -> WorkspaceConfig:
    """Return a WorkspaceConfig with default values."""
    return WorkspaceConfig()


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
