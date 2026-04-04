"""CLI interface for qt-ai-dev-tools."""

from __future__ import annotations

import json
import time
import typing
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
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


def _widget_line(widget: object) -> str:
    """Format a single widget as a display line."""
    from qt_ai_dev_tools.state import get_extents, get_name, get_role

    ext = get_extents(widget)
    return f'[{get_role(widget)}] "{get_name(widget)}" @({ext.x},{ext.y} {ext.width}x{ext.height})'


def _widget_dict(widget: object) -> dict[str, object]:
    """Convert a widget to a JSON-serializable dict."""
    from qt_ai_dev_tools.state import get_extents, get_name, get_role, get_text

    ext = get_extents(widget)
    return {
        "role": get_role(widget),
        "name": get_name(widget),
        "text": get_text(widget),
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
        from qt_ai_dev_tools.state import get_extents, get_name, get_role, get_text

        ext = get_extents(widget)
        typer.echo(f'[{get_role(widget)}] "{get_name(widget)}"')
        typer.echo(f"  text: {get_text(widget)}")
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
    from qt_ai_dev_tools.state import get_text

    typer.echo(get_text(widget))


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
    import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection

    gi.require_version("Atspi", "2.0")  # type: ignore[reportUnknownMemberType]  # rationale: gi has no stubs
    from gi.repository import Atspi  # type: ignore[import-untyped]  # rationale: system AT-SPI bindings

    desktop: object = Atspi.get_desktop(0)  # type: ignore[reportUnknownMemberType]  # rationale: gi has no stubs
    app_list: list[str] = []
    for i in range(desktop.get_child_count()):  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        child: object = desktop.get_child_at_index(i)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
        if child:
            app_list.append(child.get_name() or "(unnamed)")  # type: ignore[union-attr, reportUnknownMemberType, reportUnknownArgumentType]  # rationale: AT-SPI Accessible has no stubs
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
    import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection

    gi.require_version("Atspi", "2.0")  # type: ignore[reportUnknownMemberType]  # rationale: gi has no stubs
    from gi.repository import Atspi  # type: ignore[import-untyped]  # rationale: system AT-SPI bindings

    start = time.time()
    while time.time() - start < timeout:
        desktop: object = Atspi.get_desktop(0)  # type: ignore[reportUnknownMemberType]  # rationale: gi has no stubs
        for i in range(desktop.get_child_count()):  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
            child: object = desktop.get_child_at_index(i)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
            if child:
                child_name: str = child.get_name() or ""  # type: ignore[union-attr]  # rationale: AT-SPI Accessible
                if app_name in child_name:
                    typer.echo(f"Found: {child_name}")
                    return
        time.sleep(0.5)
    typer.echo(f"Timeout: '{app_name}' not found after {timeout}s", err=True)
    raise typer.Exit(code=1)
