"""CLI interface for qt-ai-dev-tools."""

from __future__ import annotations

import json
import os
import shlex
import sys
import time
import typing
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from qt_ai_dev_tools._atspi import AtspiNode
    from qt_ai_dev_tools.pilot import QtPilot

_CONTEXT: dict[str, list[str]] = {"help_option_names": ["-h", "--help"]}

app = typer.Typer(
    name="qt-ai-dev-tools",
    help="AI agent tools for Qt/PySide app interaction via AT-SPI. [beta]",
    no_args_is_help=True,
    context_settings=_CONTEXT,
    epilog="Status: beta (subsystem commands are alpha). "
    "Skills: qt-dev-tools-setup, qt-app-interaction, qt-form-and-input, "
    "qt-desktop-integration, qt-runtime-eval. "
    "Install: npx -y skills add quick-brown-foxxx/qt-ai-dev-tools",
)


@app.callback()
def main_callback(
    verbose: typing.Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Increase verbosity (-v for commands, -vv for full output).",
        ),
    ] = 0,
    dry_run: typing.Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show commands that would be run without executing them.",
        ),
    ] = False,
    silent: typing.Annotated[
        bool,
        typer.Option(
            "--silent",
            help="Suppress command output (vagrant commands print by default).",
        ),
    ] = False,
) -> None:
    """AI agent tools for Qt/PySide app interaction via AT-SPI."""
    import logging

    from qt_ai_dev_tools.logging import setup_file_logging, setup_stderr_logging
    from qt_ai_dev_tools.run import set_dry_run, set_silent

    # File logging is always on
    log_dir = Path("~/.local/state/qt-ai-dev-tools/logs").expanduser()
    setup_file_logging(log_dir=log_dir, app_name="qt-ai-dev-tools")

    # --dry-run without -v would silently show nothing; auto-enable verbose
    if dry_run and verbose == 0:
        verbose = 1

    # Stderr logging only when -v/-vv is given
    if verbose >= 2:
        setup_stderr_logging(level=logging.DEBUG)
    elif verbose >= 1:
        setup_stderr_logging(level=logging.INFO)

    if dry_run:
        set_dry_run(enabled=True)

    if silent:
        set_silent(enabled=True)


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
    from qt_ai_dev_tools.pilot import is_visible

    try:
        ext = widget.get_extents()
        extents_dict: dict[str, int] = {"x": ext.x, "y": ext.y, "width": ext.width, "height": ext.height}
    except (RuntimeError, OSError):
        extents_dict = {"x": 0, "y": 0, "width": 0, "height": 0}

    d: dict[str, object] = {
        "role": widget.role_name,
        "name": widget.name,
        "text": widget.get_text(),
        "extents": extents_dict,
        "visible": is_visible(widget),
    }
    if widget.has_value_iface:
        d["value"] = widget.get_value()
        d["min_value"] = widget.get_minimum_value()
        d["max_value"] = widget.get_maximum_value()
    return d


def _is_in_vm() -> bool:
    """Check if we're running inside the Vagrant VM."""
    return os.environ.get("QT_AI_DEV_TOOLS_VM") == "1"


def _proxy_to_vm(workspace: Path | None = None) -> None:
    """If running on host, re-execute this command inside the VM and exit.

    Reconstructs the full CLI invocation from sys.argv and runs it
    via vm_run(). Relays stdout/stderr and exit code.
    """
    if _is_in_vm():
        return

    from qt_ai_dev_tools.vagrant.vm import vm_run

    cmd = "qt-ai-dev-tools " + " ".join(shlex.quote(a) for a in sys.argv[1:])
    result = vm_run(cmd, workspace)
    if result.stdout:
        typer.echo(result.stdout, nl=False)
    if result.stderr:
        typer.echo(result.stderr, err=True, nl=False)
    raise typer.Exit(code=result.returncode)


def _proxy_screenshot(output: str, workspace: Path | None = None) -> None:
    """Proxy screenshot command: run scrot in VM, transfer file back via base64.

    Unlike _proxy_to_vm, this needs special handling because the screenshot
    file is created inside the VM and must be transferred to the host.
    Uses base64 encoding over vagrant ssh to avoid SCP connection issues.
    """
    if _is_in_vm():
        return

    import base64

    from qt_ai_dev_tools.vagrant.vm import find_workspace, vm_run

    ws = find_workspace(workspace)

    # Take screenshot in VM to a temp path
    remote_path = "/tmp/qt-ai-dev-tools-screenshot.png"  # noqa: S108
    result = vm_run(f"qt-ai-dev-tools screenshot -o {remote_path}", ws)
    if result.returncode != 0:
        if result.stderr:
            typer.echo(result.stderr, err=True, nl=False)
        raise typer.Exit(code=result.returncode)

    # Transfer via base64 encoding (avoids SCP connection issues)
    b64_result = vm_run(f"base64 -w 0 {remote_path}", ws)
    if b64_result.returncode != 0:
        typer.echo(f"Failed to read screenshot from VM: {b64_result.stderr}", err=True)
        raise typer.Exit(code=1)

    # Decode and save locally
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    raw = base64.b64decode(b64_result.stdout.strip())
    Path(output).write_bytes(raw)

    size = len(raw)
    typer.echo(f"Screenshot: {output} ({size} bytes)")
    raise typer.Exit(code=0)


# ── Init / Self-update commands ────────────────────────────────────


@app.command(name="install-and-own")
def install_and_own_command(
    path: typing.Annotated[Path, typer.Argument(help="Target directory")] = Path("./qt-ai-dev-tools"),
    memory: typing.Annotated[int, typer.Option(help="VM memory MB")] = 4096,
    cpus: typing.Annotated[int, typer.Option(help="VM CPUs")] = 4,
    yes_i_will_maintain_it: typing.Annotated[
        bool, typer.Option("--yes-I-will-maintain-it", help="Confirm you will own and maintain the copied code")
    ] = False,
) -> None:
    """Copy qt-ai-dev-tools source into your project. You own the copy."""
    if not yes_i_will_maintain_it:
        typer.echo(
            "This command copies the full qt-ai-dev-tools source into your project.\n"
            "You become the maintainer of that copy — no upstream updates.\n"
            "\n"
            "Pass --yes-I-will-maintain-it to confirm.",
            err=True,
        )
        raise typer.Exit(code=1)

    from qt_ai_dev_tools.installer import install_and_own

    target = path.resolve()
    try:
        created = install_and_own(target, memory=memory, cpus=cpus)
    except OSError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for entry in created:
        typer.echo(f"  {entry}")
    typer.echo(f"Toolkit installed to {target}")
    typer.echo(f"  -> Run: cd {target} && uv sync")
    typer.echo("  -> Run: qt-ai-dev-tools workspace init")
    typer.echo("  -> Load the qt-dev-tools-setup skill for full setup guidance.")


@app.command(name="self-update")
def self_update_command(
    path: typing.Annotated[Path, typer.Argument(help="Existing toolkit directory")] = Path("./qt-ai-dev-tools"),
) -> None:
    """Update an existing qt-ai-dev-tools installation, preserving config and notes."""
    from qt_ai_dev_tools.installer import self_update

    target = path.resolve()
    try:
        updated = self_update(target)
    except (OSError, FileNotFoundError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for entry in updated:
        typer.echo(f"  {entry}")
    typer.echo(f"Toolkit updated at {target}")


# ── Commands ────────────────────────────────────────────────────────


@app.command()
def tree(
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring to connect to")] = None,
    role: typing.Annotated[str | None, typer.Option("--role", help="Filter by widget role")] = None,
    max_depth: typing.Annotated[int, typer.Option("--depth", help="Maximum tree depth")] = 8,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = False,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
) -> None:
    """Print the widget tree of a running Qt app."""
    _proxy_to_vm()
    pilot = _get_pilot(app_name)

    # Hint about other apps when no --app given
    if app_name is None and pilot.app is not None:
        from qt_ai_dev_tools._atspi import AtspiNode as _AtspiNode

        desktop = _AtspiNode.desktop()
        all_apps = [c.name for c in desktop.children if c.name]
        if len(all_apps) > 1:
            current = pilot.app.name
            others = [a for a in all_apps if a != current]
            typer.echo(f"# Showing: {current} (also on bus: {', '.join(others)})", err=True)
            typer.echo("# Use --app to select a different app", err=True)

    if role:
        widgets = pilot.find(role=role, visible=visible, exact=exact)
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
    visible: typing.Annotated[
        bool, typer.Option("--visible/--no-visible", help="Filter to visible widgets only.")
    ] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[int | None, typer.Option("--index", help="Select Nth match (0-based)")] = None,
) -> None:
    """Find widgets by role and/or name."""
    _proxy_to_vm()
    if not role and not name:
        typer.echo("Error: specify at least --role or --name", err=True)
        raise typer.Exit(code=1)
    pilot = _get_pilot(app_name)
    widgets = pilot.find(role=role, name=name, visible=visible, exact=exact)
    if not widgets:
        typer.echo("No widgets found.", err=True)
        return
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
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[int | None, typer.Option("--index", help="Select Nth match (0-based)")] = None,
) -> None:
    """Click a widget by role and optional name."""
    _proxy_to_vm()
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name, visible=visible, exact=exact, index=index)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    info = _widget_line(widget)  # Cache BEFORE click (ISSUE-003)
    pilot.click(widget)
    typer.echo(f"Clicked {info}")


@app.command(name="type")
def type_cmd(
    text: typing.Annotated[str, typer.Argument(help="Text to type")],
) -> None:
    """Type text into the currently focused widget."""
    _proxy_to_vm()
    from qt_ai_dev_tools.interact import type_text

    type_text(text)
    typer.echo(f"Typed: {text}")


@app.command()
def key(
    key_name: typing.Annotated[str, typer.Argument(help="Key to press (e.g. Return, Tab, ctrl+a)")],
) -> None:
    """Press a key via xdotool."""
    _proxy_to_vm()
    from qt_ai_dev_tools.interact import press_key

    press_key(key_name)
    typer.echo(f"Pressed: {key_name}")


@app.command()
def focus(
    role: typing.Annotated[str, typer.Option("--role", help="Widget role")],
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[int | None, typer.Option("--index", help="Select Nth match (0-based)")] = None,
) -> None:
    """Focus a widget by role and optional name."""
    _proxy_to_vm()
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name, visible=visible, exact=exact, index=index)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    info = _widget_line(widget)  # Cache BEFORE focus (ISSUE-003)
    pilot.focus(widget)
    typer.echo(f"Focused {info}")


@app.command()
def state(
    role: typing.Annotated[str, typer.Option("--role", help="Widget role")],
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[int | None, typer.Option("--index", help="Select Nth match (0-based)")] = None,
) -> None:
    """Read state of a widget (name, text, extents)."""
    _proxy_to_vm()
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name, visible=visible, exact=exact, index=index)
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
        if widget.has_value_iface:
            val = widget.get_value()
            min_val = widget.get_minimum_value()
            max_val = widget.get_maximum_value()
            typer.echo(f"  Value: {val} (range: {min_val} - {max_val})")


@app.command()
def text(
    role: typing.Annotated[str, typer.Option("--role", help="Widget role")],
    name: typing.Annotated[str | None, typer.Option("--name", help="Widget name substring")] = None,
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[int | None, typer.Option("--index", help="Select Nth match (0-based)")] = None,
) -> None:
    """Get text content of a widget."""
    _proxy_to_vm()
    pilot = _get_pilot(app_name)
    try:
        widget = pilot.find_one(role=role, name=name, visible=visible, exact=exact, index=index)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(widget.get_text())


@app.command()
def screenshot(
    output: typing.Annotated[str, typer.Option("--output", "-o", help="Output path")] = "/tmp/screenshot.png",  # noqa: S108
) -> None:
    """Take a screenshot of the Xvfb display."""
    _proxy_screenshot(output)
    from qt_ai_dev_tools.screenshot import take_screenshot

    path = take_screenshot(output)
    typer.echo(path)


@app.command()
def apps(
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List all AT-SPI accessible applications on the bus."""
    _proxy_to_vm()
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
    _proxy_to_vm()
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
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[int | None, typer.Option("--index", help="Select Nth match (0-based)")] = None,
) -> None:
    """Focus a text widget, clear it, and type a value (compound action)."""
    _proxy_to_vm()
    try:
        pilot = _get_pilot(app_name)
        pilot.fill(
            role=role,
            name=name,
            value=value,
            clear_first=not no_clear,
            visible=visible,
            exact=exact,
            index=index,
        )
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
    visible: typing.Annotated[bool, typer.Option("--visible/--no-visible", help="Only match visible widgets")] = True,
    exact: typing.Annotated[bool, typer.Option("--exact", help="Match name exactly instead of substring")] = False,
    index: typing.Annotated[
        int | None,
        typer.Option("--index", help="Select Nth matching widget (0-based)."),
    ] = None,
) -> None:
    """Perform a compound action (click + optional verify/screenshot).

    Examples:
        qt-ai-dev-tools do click "Save"
        qt-ai-dev-tools do click "Save" --verify "label:status contains Saved"
        qt-ai-dev-tools do click "Add" --screenshot
    """
    _proxy_to_vm()
    try:
        pilot = _get_pilot(app_name)

        if action == "click":
            widget = pilot.find_one(role=role, name=target, visible=visible, exact=exact, index=index)
            info = f"'{role}' ({target})"  # Cache BEFORE click (ISSUE-003)
            pilot.click(widget)
            typer.echo(f"Clicked {info}")
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

workspace_app = typer.Typer(
    help="Manage qt-ai-dev-tools workspaces.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-dev-tools-setup",
)
app.add_typer(workspace_app, name="workspace")


@workspace_app.command(name="init")
def workspace_init(
    box: typing.Annotated[str, typer.Option(help="Vagrant box")] = "bento/ubuntu-24.04",
    provider: typing.Annotated[str, typer.Option(help="Vagrant provider")] = "libvirt",
    memory: typing.Annotated[int, typer.Option(help="VM memory in MB")] = 4096,
    cpus: typing.Annotated[int, typer.Option(help="VM CPUs")] = 4,
    hostname: typing.Annotated[str, typer.Option(help="VM hostname")] = "qt-dev",
    display: typing.Annotated[str, typer.Option(help="X display")] = ":99",
    resolution: typing.Annotated[str, typer.Option(help="Display resolution")] = "1920x1080x24",
    static_ip: typing.Annotated[str, typer.Option("--static-ip", help="Static IP for VM (e.g. 192.168.121.100)")] = "",
    management_network_name: typing.Annotated[str, typer.Option(help="Libvirt management network name")] = "default",
    management_network_address: typing.Annotated[
        str, typer.Option(help="Libvirt management network subnet (CIDR)")
    ] = "192.168.122.0/24",
) -> None:
    """Initialize a workspace in .qt-ai-dev-tools/ with Vagrantfile, provision.sh, and scripts."""
    from qt_ai_dev_tools.vagrant.workspace import WorkspaceConfig, render_workspace

    if provider == "virtualbox":
        typer.echo("WARNING: VirtualBox provider is NOT TESTED. Only libvirt has been verified.", err=True)

    target = Path(".qt-ai-dev-tools")
    config = WorkspaceConfig(
        box=box,
        provider=provider,
        memory=memory,
        cpus=cpus,
        hostname=hostname,
        management_network_name=management_network_name,
        management_network_address=management_network_address,
        static_ip=static_ip,
        display=display,
        resolution=resolution,
    )
    created = render_workspace(target, config)
    for f in created:
        typer.echo(f"  Created: {f}")
    typer.echo("")
    typer.echo("Workspace initialized in .qt-ai-dev-tools/")
    typer.echo("→ Review Vagrantfile for your network setup (static IP, DHCP range).")
    typer.echo("→ Add .qt-ai-dev-tools/ to .gitignore if this is a personal/local setup.")
    typer.echo("→ Run: qt-ai-dev-tools vm up")


# ── VM commands ─────────────────────────────────────────────────────

vm_app = typer.Typer(
    help="Manage Vagrant VM lifecycle.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-dev-tools-setup",
)
app.add_typer(vm_app, name="vm")


@vm_app.command(name="up")
def vm_up_cmd(
    workspace: typing.Annotated[Path | None, typer.Option("--workspace", "-w", help="Workspace path")] = None,
    provider: typing.Annotated[str, typer.Option("--provider", help="Vagrant provider")] = "libvirt",
) -> None:
    """Start the VM."""
    from qt_ai_dev_tools.run import is_silent
    from qt_ai_dev_tools.vagrant.vm import vm_up

    if provider == "virtualbox":
        typer.echo("WARNING: VirtualBox provider is NOT TESTED. Only libvirt has been verified.", err=True)

    result = vm_up(workspace, provider=provider, stream=not is_silent())
    if is_silent() and result.stdout:
        typer.echo(result.stdout)
    if result.returncode != 0:
        if is_silent() and result.stderr:
            typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)


@vm_app.command(name="status")
def vm_status_cmd(
    workspace: typing.Annotated[Path | None, typer.Option("--workspace", "-w", help="Workspace path")] = None,
) -> None:
    """Check VM status."""
    from qt_ai_dev_tools.run import is_silent
    from qt_ai_dev_tools.vagrant.vm import vm_status

    result = vm_status(workspace, stream=not is_silent())
    if is_silent() and result.stdout:
        typer.echo(result.stdout)


@vm_app.command(name="ssh")
def vm_ssh_cmd(
    workspace: typing.Annotated[Path | None, typer.Option("--workspace", "-w", help="Workspace path")] = None,
) -> None:
    """SSH into the VM."""
    from qt_ai_dev_tools.vagrant.vm import vm_ssh

    vm_ssh(workspace)


@vm_app.command(name="destroy")
def vm_destroy_cmd(
    workspace: typing.Annotated[Path | None, typer.Option("--workspace", "-w", help="Workspace path")] = None,
) -> None:
    """Destroy the VM."""
    from qt_ai_dev_tools.run import is_silent
    from qt_ai_dev_tools.vagrant.vm import vm_destroy

    result = vm_destroy(workspace, stream=not is_silent())
    if is_silent() and result.stdout:
        typer.echo(result.stdout)
    if result.returncode != 0:
        if is_silent() and result.stderr:
            typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)


@vm_app.command(name="sync")
def vm_sync_cmd(
    workspace: typing.Annotated[Path | None, typer.Option("--workspace", "-w", help="Workspace path")] = None,
) -> None:
    """Sync files to VM."""
    from qt_ai_dev_tools.run import is_silent
    from qt_ai_dev_tools.vagrant.vm import vm_sync

    result = vm_sync(workspace, stream=not is_silent())
    if is_silent():
        typer.echo(result.stdout or "Synced.")
    if result.returncode != 0:
        if is_silent() and result.stderr:
            typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)


@vm_app.command(name="sync-auto")
def vm_sync_auto_cmd(
    workspace: typing.Annotated[Path | None, typer.Option("--workspace", "-w", help="Workspace path")] = None,
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
    workspace: typing.Annotated[Path | None, typer.Option("--workspace", "-w", help="Workspace path")] = None,
) -> None:
    """Run a command inside the VM."""
    from qt_ai_dev_tools.run import is_silent
    from qt_ai_dev_tools.vagrant.vm import vm_run

    result = vm_run(command, workspace, stream=not is_silent())
    if is_silent() and result.stdout:
        typer.echo(result.stdout)
    if result.returncode != 0:
        if is_silent() and result.stderr:
            typer.echo(result.stderr, err=True)
        raise typer.Exit(code=result.returncode)


# ── Bridge commands ────────────────────────────────────────────────


def _no_bridge_error(pid: int | None) -> typing.NoReturn:
    """Print helpful error when no bridge is found and exit."""
    if pid is not None:
        typer.echo(f"Error: No bridge found for PID {pid}.", err=True)
    else:
        typer.echo("Error: No bridge found.", err=True)
    typer.echo("", err=True)
    typer.echo("Start a bridge by adding to your app:", err=True)
    typer.echo("  from qt_ai_dev_tools.bridge import start; start()", err=True)
    typer.echo("", err=True)
    typer.echo("Or set QT_AI_DEV_TOOLS_BRIDGE=1 if bridge.start() is already in the code.", err=True)
    raise typer.Exit(code=1)


@app.command(name="eval")
def eval_cmd(
    code: typing.Annotated[str | None, typer.Argument(help="Python code to execute")] = None,
    file: typing.Annotated[
        str | None, typer.Option("--file", "-f", help="Execute code from file (use - for stdin)")
    ] = None,
    pid: typing.Annotated[int | None, typer.Option("--pid", help="Target process PID")] = None,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    timeout: typing.Annotated[float, typer.Option("--timeout", help="Execution timeout in seconds")] = 30.0,
) -> None:
    """Execute Python code inside a running Qt app via bridge.

    Requires an active bridge. Start one by adding to your app:
      from qt_ai_dev_tools.bridge import start; start()

    Or inject into a running Python 3.14+ app:
      qt-ai-dev-tools bridge inject --pid <PID>

    More info in skill: qt-runtime-eval
    """
    _proxy_to_vm()

    # Resolve code from argument, file, or stdin
    if code is None and file is None:
        typer.echo("Error: provide code argument or --file", err=True)
        raise typer.Exit(code=1)

    if file is not None:
        if file == "-":
            actual_code = sys.stdin.read()
        else:
            f = Path(file)
            if not f.exists():
                typer.echo(f"Error: file not found: {file}", err=True)
                raise typer.Exit(code=1)
            actual_code = f.read_text()
    else:
        assert code is not None  # narrowed above
        actual_code = code

    from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

    # Find bridge socket
    try:
        sock = find_bridge_socket(pid)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if sock is None:
        _no_bridge_error(pid)

    response = eval_code(sock, actual_code, timeout=timeout)

    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps(asdict(response), indent=2, ensure_ascii=False))
    else:
        if response.ok:
            if response.stdout:
                typer.echo(response.stdout, nl=False)
            if response.result is not None and response.result != "None":
                typer.echo(response.result)
        else:
            typer.echo(f"Error: {response.error}", err=True)
            if response.traceback_str:
                typer.echo(response.traceback_str, err=True)
            raise typer.Exit(code=1)


bridge_app = typer.Typer(
    help="Manage bridge lifecycle.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-runtime-eval",
)
app.add_typer(bridge_app, name="bridge")


@bridge_app.command(name="status")
def bridge_status_cmd(
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List active bridge connections."""
    _proxy_to_vm()
    from qt_ai_dev_tools.bridge._client import bridge_status

    bridges = bridge_status()
    if not bridges:
        typer.echo("No active bridges found.")
        return

    if output_json:
        typer.echo(json.dumps(bridges, indent=2, ensure_ascii=False))
    else:
        for b in bridges:
            status = b.get("alive", "unknown")
            typer.echo(f"  PID {b['pid']}: {b['socket_path']} ({status})")


@bridge_app.command(name="inject")
def bridge_inject_cmd(
    pid: typing.Annotated[int | None, typer.Option("--pid", help="Target process PID")] = None,
) -> None:
    """Inject bridge into a running Python 3.14+ process."""
    _proxy_to_vm()
    from qt_ai_dev_tools.bridge._bootstrap import inject_bridge

    try:
        bridge_socket_path = inject_bridge(pid)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Bridge injected. Socket: {bridge_socket_path}")


# ── Clipboard commands ────────────────────────────────────────────

clipboard_app = typer.Typer(
    help="Clipboard operations. [alpha]",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-form-and-input",
)
app.add_typer(clipboard_app, name="clipboard")


@clipboard_app.command(name="write")
def clipboard_write_cmd(
    text: typing.Annotated[str, typer.Argument(help="Text to write to clipboard")],
) -> None:
    """Write text to the system clipboard."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("clipboard write")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import clipboard as clipboard_mod

    try:
        clipboard_mod.write(text)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Clipboard written.")


@clipboard_app.command(name="read")
def clipboard_read_cmd() -> None:
    """Read text from the system clipboard."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("clipboard read")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import clipboard as clipboard_mod

    try:
        content = clipboard_mod.read()
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(content)


# ── File dialog commands ──────────────────────────────────────────

file_dialog_app = typer.Typer(
    help="File dialog automation. [alpha]",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-form-and-input",
)
app.add_typer(file_dialog_app, name="file-dialog")


@file_dialog_app.command(name="detect")
def file_dialog_detect_cmd(
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Detect an open file dialog in the application."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("file-dialog detect")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import file_dialog as fd_mod

    pilot = _get_pilot(app_name)
    try:
        info = fd_mod.detect(pilot)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps(asdict(info), indent=2, ensure_ascii=False))
    else:
        typer.echo(f"Dialog type: {info.dialog_type}")
        if info.current_path:
            typer.echo(f"Current path: {info.current_path}")


@file_dialog_app.command(name="fill")
def file_dialog_fill_cmd(
    path: typing.Annotated[str, typer.Argument(help="File path to enter")],
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
) -> None:
    """Type a file path into the dialog's filename field."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("file-dialog fill")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import file_dialog as fd_mod

    pilot = _get_pilot(app_name)
    try:
        fd_mod.fill(pilot, path)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Filled path: {path}")


@file_dialog_app.command(name="accept")
def file_dialog_accept_cmd(
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
) -> None:
    """Click the accept button (Open/Save/OK) in the file dialog."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("file-dialog accept")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import file_dialog as fd_mod

    pilot = _get_pilot(app_name)
    try:
        result = fd_mod.accept(pilot)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Dialog accepted: {result.accepted}")


@file_dialog_app.command(name="cancel")
def file_dialog_cancel_cmd(
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
) -> None:
    """Click the Cancel button in the file dialog."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("file-dialog cancel")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import file_dialog as fd_mod

    pilot = _get_pilot(app_name)
    try:
        fd_mod.cancel(pilot)
    except LookupError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Dialog cancelled.")


# ── System tray commands ──────────────────────────────────────────

tray_app_cli = typer.Typer(
    help="System tray interaction. [alpha]",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-desktop-integration",
)
app.add_typer(tray_app_cli, name="tray")


@tray_app_cli.command(name="list")
def tray_list_cmd(
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List system tray items."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("tray list")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import tray as tray_mod

    try:
        items = tray_mod.list_items()
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not items:
        typer.echo("No tray items found.")
        return

    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps([asdict(i) for i in items], indent=2, ensure_ascii=False))
    else:
        for item in items:
            typer.echo(f"  {item.name} ({item.bus_name}) @ {item.object_path}")


@tray_app_cli.command(name="click")
def tray_click_cmd(
    app_name: typing.Annotated[str, typer.Argument(help="App name substring to match")],
    button: typing.Annotated[
        str, typer.Option("--button", "-b", help="'left' (D-Bus Activate) or 'right' (xdotool context menu)")
    ] = "left",
) -> None:
    """Click a tray item (left=activate, right=context menu)."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("tray click")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import tray as tray_mod

    if button not in ("left", "right"):
        typer.echo(f"Error: --button must be 'left' or 'right', got '{button}'", err=True)
        raise typer.Exit(code=1)

    try:
        tray_mod.click(app_name, button=button)
    except (LookupError, RuntimeError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    action = "Activated" if button == "left" else "Right-clicked"
    typer.echo(f"{action} tray item: {app_name}")


@tray_app_cli.command(name="menu")
def tray_menu_cmd(
    app_name: typing.Annotated[str, typer.Argument(help="App name substring")],
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show context menu entries for a tray item."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("tray menu")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import tray as tray_mod

    try:
        entries = tray_mod.menu(app_name)
    except (LookupError, RuntimeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not entries:
        typer.echo("No menu entries found.")
        return

    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps([asdict(e) for e in entries], indent=2, ensure_ascii=False))
    else:
        for entry in entries:
            status = "" if entry.enabled else " (disabled)"
            typer.echo(f"  [{entry.index}] {entry.label}{status}")


@tray_app_cli.command(name="select")
def tray_select_cmd(
    app_name: typing.Annotated[str, typer.Argument(help="App name substring")],
    item_label: typing.Annotated[str, typer.Argument(help="Menu item label to click")],
) -> None:
    """Click a menu item in a tray icon's context menu."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("tray select")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import tray as tray_mod

    try:
        tray_mod.select(app_name, item_label)
    except (LookupError, RuntimeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Selected '{item_label}' from tray menu of {app_name}")


# ── Notification commands ─────────────────────────────────────────

notify_app_cli = typer.Typer(
    help="Desktop notification interaction. [alpha]",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-desktop-integration",
)
app.add_typer(notify_app_cli, name="notify")


@notify_app_cli.command(name="listen")
def notify_listen_cmd(
    timeout: typing.Annotated[float, typer.Option("--timeout", "-t", help="Seconds to listen")] = 5.0,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Listen for desktop notifications."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("notify listen")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import notify as notify_mod

    try:
        notifications = notify_mod.listen(timeout=timeout)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not notifications:
        typer.echo("No notifications captured.")
        return

    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps([asdict(n) for n in notifications], indent=2, ensure_ascii=False))
    else:
        for n in notifications:
            typer.echo(f"  [{n.id}] {n.app_name}: {n.summary}")
            if n.body:
                typer.echo(f"    {n.body}")
            for a in n.actions:
                typer.echo(f"    Action: {a.key} ({a.label})")


@notify_app_cli.command(name="dismiss")
def notify_dismiss_cmd(
    notification_id: typing.Annotated[int, typer.Argument(help="Notification ID to dismiss")],
) -> None:
    """Dismiss a notification by ID."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("notify dismiss")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import notify as notify_mod

    try:
        notify_mod.dismiss(notification_id)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Dismissed notification {notification_id}")


@notify_app_cli.command(name="action")
def notify_action_cmd(
    notification_id: typing.Annotated[int, typer.Argument(help="Notification ID")],
    action_key: typing.Annotated[str, typer.Argument(help="Action key to invoke")],
) -> None:
    """Invoke an action on a notification."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("notify action")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import notify as notify_mod

    try:
        notify_mod.action(notification_id, action_key)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Invoked action '{action_key}' on notification {notification_id}")


# ── Audio commands ────────────────────────────────────────────────

audio_app_cli = typer.Typer(
    help="PipeWire audio interaction. [alpha]",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-desktop-integration",
)
app.add_typer(audio_app_cli, name="audio")

# Virtual mic sub-group
vmic_app = typer.Typer(
    help="Virtual microphone management. [alpha]",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-desktop-integration",
)
audio_app_cli.add_typer(vmic_app, name="virtual-mic")


@vmic_app.command(name="start")
def audio_vmic_start_cmd(
    node_name: typing.Annotated[str, typer.Option("--name", "-n", help="Node name")] = "virtual-mic",
) -> None:
    """Start a virtual microphone via pw-loopback."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("audio virtual-mic start")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import audio as audio_mod

    try:
        info = audio_mod.virtual_mic_start(node_name)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Virtual mic started: {info.node_name} (PID {info.pid})")


@vmic_app.command(name="stop")
def audio_vmic_stop_cmd() -> None:
    """Stop the virtual microphone."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("audio virtual-mic stop")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import audio as audio_mod

    try:
        audio_mod.virtual_mic_stop()
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Virtual mic stopped.")


@vmic_app.command(name="play")
def audio_vmic_play_cmd(
    path: typing.Annotated[str, typer.Argument(help="Audio file path")],
    node_name: typing.Annotated[str, typer.Option("--name", "-n", help="Target node name")] = "virtual-mic",
) -> None:
    """Play audio into the virtual microphone."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("audio virtual-mic play")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import audio as audio_mod

    try:
        audio_mod.virtual_mic_play(Path(path), node_name)
    except (RuntimeError, FileNotFoundError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Played {path} into {node_name}")


@audio_app_cli.command(name="record")
def audio_record_cmd(
    duration: typing.Annotated[float, typer.Option("--duration", "-d", help="Recording duration in seconds")] = 5.0,
    output: typing.Annotated[str, typer.Option("--output", "-o", help="Output file path")] = "/tmp/recording.wav",  # noqa: S108
    loopback: typing.Annotated[bool, typer.Option("--loopback", help="Record from loopback source")] = False,
) -> None:
    """Record audio from PipeWire."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("audio record")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import audio as audio_mod

    try:
        result = audio_mod.record(duration, Path(output), loopback=loopback)
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Recorded to {result}")


@audio_app_cli.command(name="sources")
def audio_sources_cmd(
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List PipeWire audio sources."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("audio sources")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import audio as audio_mod

    try:
        src_list = audio_mod.sources()
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not src_list:
        typer.echo("No audio sources found.")
        return

    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps([asdict(s) for s in src_list], indent=2, ensure_ascii=False))
    else:
        for s in src_list:
            typer.echo(f"  [{s.id}] {s.name} - {s.description}")


@audio_app_cli.command(name="status")
def audio_status_cmd(
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """List active PipeWire audio streams."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("audio status")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import audio as audio_mod

    try:
        streams = audio_mod.status()
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not streams:
        typer.echo("No active audio streams.")
        return

    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps([asdict(s) for s in streams], indent=2, ensure_ascii=False))
    else:
        for s in streams:
            typer.echo(f"  [{s.id}] {s.node_name} ({s.state})")


@audio_app_cli.command(name="verify")
def audio_verify_cmd(
    path: typing.Annotated[str, typer.Argument(help="Audio file path to verify")],
    threshold: typing.Annotated[float, typer.Option("--threshold", help="RMS amplitude threshold")] = 0.001,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Verify an audio file is not silence."""
    from qt_ai_dev_tools._stability import warn_if_alpha

    warn_if_alpha("audio verify")
    _proxy_to_vm()
    from qt_ai_dev_tools.subsystems import audio as audio_mod

    try:
        result = audio_mod.verify_not_silence(Path(path), threshold=threshold)
    except (RuntimeError, FileNotFoundError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if output_json:
        from dataclasses import asdict

        typer.echo(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    else:
        status_text = "SILENT" if result.is_silent else "NOT SILENT"
        typer.echo(f"  Status: {status_text}")
        typer.echo(f"  Max amplitude: {result.max_amplitude:.6f}")
        typer.echo(f"  RMS amplitude: {result.rms_amplitude:.6f}")
        typer.echo(f"  Duration: {result.duration_seconds:.2f}s")

    if result.is_silent:
        raise typer.Exit(code=1)


# ── Snapshot commands ────────────────────────────────────────────

snapshot_app = typer.Typer(
    help="Widget tree snapshot and diff.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-app-interaction",
)
app.add_typer(snapshot_app, name="snapshot")


@snapshot_app.command(name="save")
def snapshot_save_cmd(
    name: typing.Annotated[str, typer.Argument(help="Snapshot name")],
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    max_depth: typing.Annotated[int, typer.Option("--depth", help="Maximum tree depth")] = 8,
) -> None:
    """Capture the current widget tree and save to a snapshot file."""
    _proxy_to_vm()
    from qt_ai_dev_tools.snapshot import capture_tree, save_snapshot

    pilot = _get_pilot(app_name)
    if pilot.app is None:
        typer.echo("Error: no app connected", err=True)
        raise typer.Exit(code=1)

    entries = capture_tree(pilot.app, max_depth=max_depth)
    out_path = Path("snapshots") / f"{name}.json"
    save_snapshot(entries, out_path)
    typer.echo(f"Saved snapshot '{name}' ({len(entries)} widgets) to {out_path}")


@snapshot_app.command(name="diff")
def snapshot_diff_cmd(
    name: typing.Annotated[str, typer.Argument(help="Snapshot name to compare against")],
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    max_depth: typing.Annotated[int, typer.Option("--depth", help="Maximum tree depth")] = 8,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Compare the current widget tree against a saved snapshot."""
    _proxy_to_vm()
    from qt_ai_dev_tools.snapshot import capture_tree, diff_snapshots, format_diff, load_snapshot

    snap_path = Path("snapshots") / f"{name}.json"
    try:
        old_entries = load_snapshot(snap_path)
    except FileNotFoundError:
        typer.echo(f"Error: snapshot '{name}' not found at {snap_path}", err=True)
        raise typer.Exit(code=1) from None

    pilot = _get_pilot(app_name)
    if pilot.app is None:
        typer.echo("Error: no app connected", err=True)
        raise typer.Exit(code=1)

    new_entries = capture_tree(pilot.app, max_depth=max_depth)
    diff = diff_snapshots(old_entries, new_entries)

    if output_json:
        diff_data: dict[str, object] = {
            "added": [e.to_dict() for e in diff.added],
            "removed": [e.to_dict() for e in diff.removed],
            "changed": [{"old": old_e.to_dict(), "new": new_e.to_dict()} for old_e, new_e in diff.changed],
        }
        typer.echo(json.dumps(diff_data, indent=2, ensure_ascii=False))
    else:
        typer.echo(format_diff(diff))
