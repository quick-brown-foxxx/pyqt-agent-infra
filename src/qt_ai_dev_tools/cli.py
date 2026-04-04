"""CLI interface for qt-ai-dev-tools."""

from __future__ import annotations

import json
import time
import typing
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from qt_ai_dev_tools._atspi import AtspiNode
    from qt_ai_dev_tools.pilot import QtPilot

app = typer.Typer(
    name="qt-ai-dev-tools",
    help="AI agent tools for Qt/PySide app interaction via AT-SPI.",
    no_args_is_help=True,
)


def _get_pilot(app_name: str | None = None, retries: int = 5) -> QtPilot:
    """Create a QtPilot instance, handling connection errors."""
    from qt_ai_dev_tools.pilot import QtPilot

    try:
        return QtPilot(app_name=app_name, retries=retries)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _widget_line(widget: AtspiNode) -> str:
    """Format a single widget as a display line.

    Note: AtspiNode is used as a type hint via TYPE_CHECKING.
    At runtime, the widget is an AtspiNode instance passed from pilot/AT-SPI commands.
    """
    ext = widget.get_extents()
    return f'[{widget.role_name}] "{widget.name}" @({ext.x},{ext.y} {ext.width}x{ext.height})'


def _widget_dict(widget: AtspiNode) -> dict[str, object]:
    """Convert a widget to a JSON-serializable dict."""
    ext = widget.get_extents()
    return {
        "role": widget.role_name,
        "name": widget.name,
        "text": widget.get_text(),
        "extents": {"x": ext.x, "y": ext.y, "width": ext.width, "height": ext.height},
    }


# ── Commands ────────────────────────────────────────────────────────


@app.command()
def tree(
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring to connect to")] = None,
    role: typing.Annotated[str | None, typer.Option("--role", help="Filter by widget role")] = None,
    max_depth: typing.Annotated[int, typer.Option("--depth", help="Maximum tree depth")] = 8,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Print the widget tree of a running Qt app."""
    pilot = _get_pilot(app_name)
    if role:
        widgets = pilot.find(role=role)
        if output_json:
            typer.echo(json.dumps([_widget_dict(w) for w in widgets], indent=2, ensure_ascii=False))
        else:
            for w in widgets:
                typer.echo(_widget_line(w))
    else:
        if output_json:
            typer.echo("JSON output for full tree not yet supported. Use --role filter.", err=True)
            raise typer.Exit(code=1)
        pilot.dump_tree(max_depth=max_depth)


@app.command()
def find(
    role: typing.Annotated[str | None, typer.Option("--role", help="Widget role (e.g. 'push button')")] = None,
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Find widgets by role and/or name."""
    if not role and not name:
        typer.echo("Error: specify at least --role or --name", err=True)
        raise typer.Exit(code=1)
    pilot = _get_pilot(app_name)
    widgets = pilot.find(role=role, name=name)
    if not widgets:
        typer.echo("No widgets found.", err=True)
        raise typer.Exit(code=1)
    if output_json:
        typer.echo(json.dumps([_widget_dict(w) for w in widgets], indent=2, ensure_ascii=False))
    else:
        for w in widgets:
            typer.echo(_widget_line(w))


@app.command(name="click")
def click_cmd(
    role: typing.Annotated[str, typer.Option("--role", help="Widget role")],
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
) -> None:
    """Click a widget by role and optional name."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    pilot.click(widget)
    typer.echo(f"Clicked {_widget_line(widget)}")


@app.command(name="type")
def type_cmd(
    text: typing.Annotated[str, typer.Argument(help="Text to type")],
) -> None:
    """Type text into the currently focused widget."""
    from qt_ai_dev_tools.interact import type_text

    type_text(text)
    typer.echo(f"Typed: {text}")


@app.command()
def key(
    key_name: typing.Annotated[str, typer.Argument(help="Key to press (e.g. Return, Tab, ctrl+a)")],
) -> None:
    """Press a key via xdotool."""
    from qt_ai_dev_tools.interact import press_key

    press_key(key_name)
    typer.echo(f"Pressed: {key_name}")


@app.command()
def focus(
    role: typing.Annotated[str, typer.Option("--role", help="Widget role")],
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
) -> None:
    """Focus a widget by role and optional name."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    pilot.focus(widget)
    typer.echo(f"Focused {_widget_line(widget)}")


@app.command()
def state(
    role: typing.Annotated[str, typer.Option("--role", help="Widget role")],
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Read state of a widget (name, text, extents)."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if output_json:
        typer.echo(json.dumps(_widget_dict(widget), indent=2, ensure_ascii=False))
    else:
        ext = widget.get_extents()
        typer.echo(f'[{widget.role_name}] "{widget.name}"')
        typer.echo(f"  text: {widget.get_text()}")
        typer.echo(f"  extents: ({ext.x},{ext.y} {ext.width}x{ext.height})")


@app.command()
def text(
    role: typing.Annotated[str, typer.Option("--role", help="Widget role")],
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
) -> None:
    """Get text content of a widget."""
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(widget.get_text())


@app.command()
def screenshot(
    output: typing.Annotated[str, typer.Option("--output", "-o", help="Output path")] = "/tmp/screenshot.png",  # noqa: S108
) -> None:
    """Take a screenshot of the Xvfb display."""
    from qt_ai_dev_tools.screenshot import take_screenshot

    path = take_screenshot(output)
    typer.echo(path)


@app.command()
def apps(
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List all AT-SPI accessible applications on the bus."""
    from qt_ai_dev_tools._atspi import AtspiNode

    desktop = AtspiNode.desktop()
    app_list = [child.name or "(unnamed)" for child in desktop.children]
    if output_json:
        typer.echo(json.dumps(app_list, ensure_ascii=False))
    else:
        if not app_list:
            typer.echo("No apps found on AT-SPI bus.")
        else:
            for a in app_list:
                typer.echo(a)


@app.command()
def wait(
    app_name: typing.Annotated[str, typer.Option("--app", help="App name substring to wait for")],
    timeout: typing.Annotated[int, typer.Option("--timeout", help="Timeout in seconds")] = 10,
) -> None:
    """Wait for an app to appear on the AT-SPI bus."""
    from qt_ai_dev_tools._atspi import AtspiNode

    start = time.time()
    while time.time() - start < timeout:
        desktop = AtspiNode.desktop()
        for child in desktop.children:
            if app_name in child.name:
                typer.echo(f"Found: {child.name}")
                return
        time.sleep(0.5)
    typer.echo(f"Timeout: '{app_name}' not found after {timeout}s", err=True)
    raise typer.Exit(code=1)


# ── Workspace commands ──────────────────────────────────────────────

workspace_app = typer.Typer(help="Manage qt-ai-dev-tools workspaces.")
app.add_typer(workspace_app, name="workspace")


@workspace_app.command(name="init")
def workspace_init(
    path: typing.Annotated[Path, typer.Option("--path", help="Target directory")] = Path("."),
    box: typing.Annotated[str, typer.Option(help="Vagrant box")] = "bento/ubuntu-24.04",
    provider: typing.Annotated[str, typer.Option(help="Vagrant provider")] = "libvirt",
    memory: typing.Annotated[int, typer.Option(help="VM memory in MB")] = 4096,
    cpus: typing.Annotated[int, typer.Option(help="VM CPUs")] = 4,
    hostname: typing.Annotated[str, typer.Option(help="VM hostname")] = "qt-dev",
    display: typing.Annotated[str, typer.Option(help="X display")] = ":99",
    resolution: typing.Annotated[str, typer.Option(help="Display resolution")] = "1920x1080x24",
) -> None:
    """Initialize a workspace with Vagrantfile, provision.sh, and scripts."""
    from qt_ai_dev_tools.vagrant.workspace import WorkspaceConfig, render_workspace

    config = WorkspaceConfig(
        box=box,
        provider=provider,
        memory=memory,
        cpus=cpus,
        hostname=hostname,
        display=display,
        resolution=resolution,
    )
    created = render_workspace(path, config)
    for f in created:
        typer.echo(f"  Created: {f}")
    typer.echo(f"Workspace initialized in {path}")


# ── VM commands ─────────────────────────────────────────────────────

vm_app = typer.Typer(help="Manage Vagrant VM lifecycle.")
app.add_typer(vm_app, name="vm")


@vm_app.command(name="up")
def vm_up_cmd(
    workspace: typing.Annotated[
        Path | None, typer.Option("--workspace", "-w", help="Workspace path")
    ] = None,
    provider: typing.Annotated[str, typer.Option("--provider", help="Vagrant provider")] = "libvirt",
) -> None:
    """Start the VM."""
    from qt_ai_dev_tools.vagrant.vm import vm_up

    result = vm_up(workspace, provider=provider)
    typer.echo(result.stdout)
    if result.returncode != 0:
        typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)


@vm_app.command(name="status")
def vm_status_cmd(
    workspace: typing.Annotated[
        Path | None, typer.Option("--workspace", "-w", help="Workspace path")
    ] = None,
) -> None:
    """Check VM status."""
    from qt_ai_dev_tools.vagrant.vm import vm_status

    result = vm_status(workspace)
    typer.echo(result.stdout)


@vm_app.command(name="ssh")
def vm_ssh_cmd(
    workspace: typing.Annotated[
        Path | None, typer.Option("--workspace", "-w", help="Workspace path")
    ] = None,
) -> None:
    """SSH into the VM."""
    from qt_ai_dev_tools.vagrant.vm import vm_ssh

    vm_ssh(workspace)


@vm_app.command(name="destroy")
def vm_destroy_cmd(
    workspace: typing.Annotated[
        Path | None, typer.Option("--workspace", "-w", help="Workspace path")
    ] = None,
) -> None:
    """Destroy the VM."""
    from qt_ai_dev_tools.vagrant.vm import vm_destroy

    result = vm_destroy(workspace)
    typer.echo(result.stdout)
    if result.returncode != 0:
        typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)


@vm_app.command(name="sync")
def vm_sync_cmd(
    workspace: typing.Annotated[
        Path | None, typer.Option("--workspace", "-w", help="Workspace path")
    ] = None,
) -> None:
    """Sync files to VM."""
    from qt_ai_dev_tools.vagrant.vm import vm_sync

    result = vm_sync(workspace)
    typer.echo(result.stdout or "Synced.")
    if result.returncode != 0:
        typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)


@vm_app.command(name="run")
def vm_run_cmd(
    command: typing.Annotated[str, typer.Argument(help="Command to run inside VM")],
    workspace: typing.Annotated[
        Path | None, typer.Option("--workspace", "-w", help="Workspace path")
    ] = None,
) -> None:
    """Run a command inside the VM."""
    from qt_ai_dev_tools.vagrant.vm import vm_run

    result = vm_run(command, workspace)
    if result.stdout:
        typer.echo(result.stdout)
    if result.returncode != 0:
        typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)
