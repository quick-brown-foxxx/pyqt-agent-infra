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
        typer.echo(pilot.dump_tree(max_depth=max_depth))


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


# ── Compound commands ──────────────────────────────────────────────


@app.command()
def fill(
    value: typing.Annotated[str, typer.Argument(help="Text to type into the widget")],
    role: typing.Annotated[str, typer.Option("--role", "-r", help="Widget role")] = "text",
    name: typing.Annotated[str | None, typer.Option("--name", "-n", help="Widget name")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name")] = None,
    no_clear: typing.Annotated[bool, typer.Option("--no-clear", help="Don't clear field first")] = False,
) -> None:
    """Focus a text widget, clear it, and type a value (compound action)."""
    try:
        pilot = _get_pilot(app_name)
        pilot.fill(role=role, name=name, value=value, clear_first=not no_clear)
        name_suffix = f" ({name})" if name else ""
        typer.echo(f"Filled '{role}'{name_suffix} with: {value}")
    except (RuntimeError, LookupError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command(name="do")
def do_action(
    action: typing.Annotated[str, typer.Argument(help="Action to perform: click")],
    target: typing.Annotated[str, typer.Argument(help="Widget name or role to act on")],
    role: typing.Annotated[str, typer.Option("--role", "-r", help="Widget role")] = "push button",
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name")] = None,
    verify: typing.Annotated[
        str | None, typer.Option("--verify", help="Verify condition after action (e.g. 'label:status contains Saved')")
    ] = None,
    screenshot_after: typing.Annotated[bool, typer.Option("--screenshot", help="Take screenshot after action")] = False,
) -> None:
    """Perform a compound action (click + optional verify/screenshot).

    Examples:
        qt-ai-dev-tools do click "Save"
        qt-ai-dev-tools do click "Save" --verify "label:status contains Saved"
        qt-ai-dev-tools do click "Add" --screenshot
    """
    try:
        pilot = _get_pilot(app_name)

        if action == "click":
            widget = pilot.find_one(role=role, name=target)
            pilot.click(widget)
            typer.echo(f"Clicked '{role}' ({target})")
        else:
            typer.echo(f"Unknown action: {action}", err=True)
            raise typer.Exit(code=1)

        if screenshot_after:
            path = pilot.screenshot()
            typer.echo(f"Screenshot: {path}")

        if verify:
            _verify_condition(pilot, verify)

    except (RuntimeError, LookupError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _verify_condition(pilot: QtPilot, condition: str) -> None:
    """Parse and check a verify condition string.

    Format: "role:name contains text" or "role contains text"
    Examples:
        "label:status contains Saved"
        "label contains Items: 1"
    """
    if " contains " not in condition:
        typer.echo(f"Invalid verify format: {condition} (expected 'role:name contains text')", err=True)
        raise typer.Exit(code=1)

    selector, expected_text = condition.split(" contains ", 1)

    if ":" in selector:
        verify_role, verify_name = selector.split(":", 1)
    else:
        verify_role = selector
        verify_name = None

    try:
        widgets = pilot.find(
            role=verify_role.strip(),
            name=verify_name.strip() if verify_name else None,
        )
        if not widgets:
            typer.echo(f"Verify FAILED: no widget matching '{selector}'", err=True)
            raise typer.Exit(code=1)

        for w in widgets:
            widget_text = pilot.get_name(w)
            widget_actual_text = pilot.get_text(w)
            combined = f"{widget_text} {widget_actual_text}"
            if expected_text.strip() in combined:
                typer.echo(f"Verify OK: '{selector}' contains '{expected_text.strip()}'")
                return

        typer.echo(f"Verify FAILED: '{selector}' does not contain '{expected_text.strip()}'", err=True)
        raise typer.Exit(code=1)

    except LookupError as exc:
        typer.echo(f"Verify FAILED: {exc}", err=True)
        raise typer.Exit(code=1) from exc


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
    static_ip: typing.Annotated[str, typer.Option("--static-ip", help="Static IP for VM (e.g. 192.168.121.100)")] = "",
) -> None:
    """Initialize a workspace with Vagrantfile, provision.sh, and scripts."""
    from qt_ai_dev_tools.vagrant.workspace import WorkspaceConfig, render_workspace

    config = WorkspaceConfig(
        box=box,
        provider=provider,
        memory=memory,
        cpus=cpus,
        hostname=hostname,
        static_ip=static_ip,
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


@vm_app.command(name="sync-auto")
def vm_sync_auto_cmd(
    workspace: typing.Annotated[
        Path | None, typer.Option("--workspace", "-w", help="Workspace path")
    ] = None,
) -> None:
    """Start background rsync-auto to keep VM files in sync."""
    from qt_ai_dev_tools.vagrant.vm import vm_sync_auto

    process = vm_sync_auto(workspace)
    typer.echo(f"rsync-auto started (PID {process.pid}). Files will sync automatically.")
    typer.echo("Press Ctrl+C to stop.")
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        typer.echo("\nrsync-auto stopped.")


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
