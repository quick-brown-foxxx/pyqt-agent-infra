# qt-ai-dev-tools

Infrastructure for AI agents to interact with Qt/PySide apps on Linux -- inspect widgets, click buttons, type text, take screenshots, read state. AT-SPI + xdotool + scrot as a Chrome DevTools equivalent for Qt.

## Quick start

```bash
pip install -e .               # or: uv sync
make workspace-init            # generate Vagrantfile, provision.sh, scripts from templates
make up                        # start VM (~10 min first time)
make test                      # fast offscreen pytest-qt tests
make screenshot                # screenshot current VM display
```

## CLI usage

All commands are available via the `qt-ai-dev-tools` CLI. Run inside the VM (via `make ssh` or `make run`):

```bash
# Widget inspection
qt-ai-dev-tools tree                          # full accessibility tree
qt-ai-dev-tools tree --role "push button"     # filter by role
qt-ai-dev-tools find --role "label" --json    # find widgets, JSON output
qt-ai-dev-tools apps                          # list AT-SPI applications

# Interaction
qt-ai-dev-tools click --role "push button" --name "Save"
qt-ai-dev-tools type "hello world"
qt-ai-dev-tools key Return

# Screenshots
qt-ai-dev-tools screenshot -o /tmp/shot.png

# Workspace management (generate Vagrant infra from templates)
qt-ai-dev-tools workspace init --path .
qt-ai-dev-tools workspace init --memory 8192 --cpus 8

# VM lifecycle
qt-ai-dev-tools vm up
qt-ai-dev-tools vm status
qt-ai-dev-tools vm ssh
qt-ai-dev-tools vm sync
qt-ai-dev-tools vm run "pytest /vagrant/tests/"
qt-ai-dev-tools vm destroy
```

## Architecture

- **AT-SPI** provides the widget tree -- roles, names, coordinates, text content. All raw AT-SPI access is confined to `_atspi.py` behind a typed `AtspiNode` wrapper.
- **xdotool** handles interaction -- clicks by coordinate, text input, key presses. AT-SPI's own text insertion does not work with Qt's internal model.
- **scrot** captures screenshots from the virtual display.
- **Vagrant VM** (Ubuntu 24.04, libvirt) provides full OS isolation with Xvfb, openbox, D-Bus, and AT-SPI. This is the primary environment -- no container or host assumptions.
- **Jinja2 templates** generate Vagrantfile, provision.sh, and shell scripts via `workspace init`.

## Development

```bash
make lint          # ruff check + basedpyright (strict)
make lint-fix      # auto-fix lint issues
make test          # fast offscreen tests
make test-full     # all tests including AT-SPI and CLI
make test-cli      # CLI integration tests only
make status        # check Xvfb, openbox, AT-SPI in VM
```

### Project structure

```
src/qt_ai_dev_tools/
  _atspi.py        # AtspiNode wrapper (all raw AT-SPI access confined here)
  pilot.py         # QtPilot: connect, find, click, type, read
  cli.py           # Typer CLI entry point
  interact.py      # xdotool click/type/key, AT-SPI actions
  state.py         # read widget name, role, extents, text
  screenshot.py    # screenshot via scrot
  models.py        # Extents, WidgetInfo data types
  vagrant/
    workspace.py   # WorkspaceConfig + template rendering
    vm.py          # VM lifecycle commands
    templates/     # Jinja2 templates for Vagrantfile, provision.sh, scripts
app/main.py        # sample PySide6 todo app (test subject)
tests/             # pytest-qt + AT-SPI + CLI integration tests
```

## Documentation

- [Roadmap](docs/ROADMAP.md)
- [Results (Phase 0 PoC)](RESULTS.md)
