# qt-ai-dev-tools

Chrome DevTools for Qt apps -- let AI agents inspect widgets, click buttons, type text, take screenshots, and read state from any Qt/PySide application on Linux, without modifying the target app.

## What it does

- **Inspect the full widget tree** of any running Qt app via AT-SPI accessibility -- roles, names, coordinates, text content, all available without touching the app's source code.
- **Interact with widgets** -- click buttons, type into fields, press keys, focus widgets, fill forms -- using xdotool for input and AT-SPI for widget discovery.
- **Capture screenshots** of the virtual display for visual verification after interactions.
- **Run in a Vagrant VM** with Xvfb, openbox, D-Bus, and AT-SPI pre-configured -- full OS isolation, reproducible environment, no host contamination.

## How it works

```
  AI Agent (Claude Code, etc.)
       |
       |  shell commands (same commands on host or in VM)
       v
  qt-ai-dev-tools CLI
       |
       |  auto-detects host vs VM
       |  (proxies through SSH when on host)
       |
       +---> AT-SPI (widget tree: roles, names, coords, text)
       +---> xdotool (clicks, keystrokes, text input)
       +---> scrot (screenshots)
       |
  [ Vagrant VM: Ubuntu 24.04 + Xvfb :99 + openbox + D-Bus ]
       |
       v
  Target Qt/PySide App (unmodified)
```

AT-SPI provides the accessibility tree -- the same tree screen readers use. xdotool sends X11 input events. scrot captures the framebuffer. The agent never imports or instruments the target app.

**Transparent VM proxy:** UI commands (tree, click, type, screenshot, etc.) auto-detect whether they are running on the host or inside the VM. On the host, they automatically proxy through SSH to the VM. No manual wrapping with `vm run` is needed for qt-ai-dev-tools commands.

## Quick start

### Prerequisites

- Linux host with libvirt (QEMU/KVM) and Vagrant installed
- `vagrant-libvirt` plugin: `vagrant plugin install vagrant-libvirt`
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# Clone and install
git clone https://github.com/quick-brown-foxxx/qt-ai-dev-tools.git
cd qt-ai-dev-tools
uv sync

# Generate workspace files (Vagrantfile, provision.sh)
qt-ai-dev-tools workspace init --path .

# Start the VM (~10 min first boot)
qt-ai-dev-tools vm up

# Verify environment
qt-ai-dev-tools vm status
```

### First interaction

```bash
# Launch the sample app inside the VM (vm run is for arbitrary commands)
qt-ai-dev-tools vm run "python /vagrant/app/main.py &"

# Wait for it to register with AT-SPI (auto-proxies to VM from host)
qt-ai-dev-tools wait --app "main.py" --timeout 10

# Inspect the widget tree (runs directly -- auto-proxies to VM)
qt-ai-dev-tools tree

# Click a button
qt-ai-dev-tools click --role "push button" --name "Add"

# Type text into a field
qt-ai-dev-tools fill --role "text" --value "Buy groceries"

# Take a screenshot
qt-ai-dev-tools screenshot -o /tmp/shot.png
```

UI commands work the same from host or VM -- they auto-detect and proxy transparently. Use `vm run` only for arbitrary non-qt-ai-dev-tools commands (e.g., launching apps, running pytest, systemctl).

## CLI reference

UI commands (tree, click, type, find, screenshot, etc.) auto-detect host vs VM and proxy transparently -- just run them directly. Use `vm run` only for arbitrary non-qt-ai-dev-tools commands.

### Inspection

| Command | Description |
|---------|-------------|
| `tree` | Print the full widget tree of a running Qt app |
| `tree --role "push button"` | Filter tree by widget role |
| `tree --json` | Machine-readable JSON output |
| `find --role "label" --name "status"` | Find specific widgets by role and/or name |
| `find --role "text" --json` | Find widgets with JSON output |
| `apps` | List all AT-SPI accessible applications on the bus |
| `wait --app "main.py" --timeout 10` | Wait for an app to appear on the AT-SPI bus |

### Interaction

| Command | Description |
|---------|-------------|
| `click --role "push button" --name "Save"` | Click a widget by role and optional name |
| `type "hello world"` | Type text into the currently focused widget |
| `key Return` | Press a key (any xdotool key name) |
| `focus --role "text" --name "input"` | Focus a widget by role and optional name |

### Compound commands

| Command | Description |
|---------|-------------|
| `fill --role "text" --name "email" --value "a@b.com"` | Focus + clear + type in one step |
| `do click "Save" --verify "label:status contains Saved"` | Click + verify widget state |
| `do click "Add" --screenshot` | Click + take screenshot |

### State

| Command | Description |
|---------|-------------|
| `state --role "label" --name "status"` | Read widget name, text, and extents |
| `text --role "text"` | Get text content of a widget |
| `screenshot -o /tmp/shot.png` | Capture the Xvfb display |

### Workspace management

| Command | Description |
|---------|-------------|
| `workspace init --path .` | Generate Vagrantfile and provision.sh from templates |
| `workspace init --memory 8192 --cpus 8` | Custom VM resources |
| `workspace init --provider libvirt` | Specify Vagrant provider |
| `workspace init --static-ip 192.168.121.100` | Use static IP (avoids DHCP issues) |

### VM lifecycle

| Command | Description |
|---------|-------------|
| `vm up` | Start the VM |
| `vm status` | Check VM and service status |
| `vm ssh` | SSH into the VM |
| `vm sync` | Rsync files to the VM |
| `vm sync-auto` | Background file sync (watches for changes) |
| `vm run "command"` | Run an arbitrary command inside the VM (not needed for qt-ai-dev-tools commands) |
| `vm destroy` | Destroy the VM |

## AI agent skills

The `skills/` directory contains structured guidance that teaches AI agents how to use qt-ai-dev-tools effectively:

| Skill | What it teaches |
|-------|-----------------|
| `qt-dev-tools-setup` | Install toolkit, configure VM, verify environment -- everything needed before first interaction |
| `qt-app-interaction` | The core inspect→interact→verify workflow loop, with progressive references for widget roles, recipes, and troubleshooting |

Skills are the primary integration point. An agent with the right skill can use even a basic CLI effectively.

## Key technical facts

- **AT-SPI, not pyatspi.** Use `gi.repository.Atspi` -- the `pyatspi` wrapper is broken on Python 3.12+.
- **xdotool, not AT-SPI text insertion.** AT-SPI's `editable_text.insert_text()` updates the accessibility layer but not Qt's internal model. xdotool keystrokes are the only reliable way to type text.
- **Openbox is required.** Without a window manager, xdotool reports incorrect coordinates and `windowactivate` fails.
- **Xvfb display :99.** All tools need `DISPLAY=:99`. The VM provisions this automatically.
- **libvirt only (tested).** The Vagrantfile includes VirtualBox provider blocks, but only libvirt (QEMU/KVM via vagrant-libvirt) has been tested. VirtualBox may require adjustments.
- **Known libvirt DHCP bug.** vagrant-libvirt creates a network with a DHCP range starting at `.1`, colliding with the host bridge IP. Workaround: pre-create the network with a corrected range, or use `--static-ip` to bypass DHCP entirely. See `skills/qt-dev-tools-setup/references/vm-troubleshooting.md`.
- **Screenshots are small.** scrot output is ~14-22 KB PNG -- cheap to capture and send to an LLM.
- **Each CLI command is stateless.** No persistent state between invocations. The agent chains commands via shell.
- **Transparent VM proxy.** UI commands auto-detect host vs VM via the `QT_AI_DEV_TOOLS_VM=1` env var (set automatically inside the VM). On the host, they proxy through SSH to the VM. On the VM, they run directly. No manual `vm run` wrapping needed for qt-ai-dev-tools commands.

## Project status

Phases 1-5 are complete:

- Phase 1: CLI and library refactor -- proper Python package with Typer CLI
- Phase 2: Type system hardening -- `AtspiNode` typed wrapper, basedpyright strict project-wide
- Phase 3: Vagrant subsystem consolidation -- Jinja2 templates, `workspace init`, `vm *` commands
- Phase 4: VM environment improvements -- auto-sync, multi-provider templates, static IP support
- Phase 5: Agent integration -- compound commands (`fill`, `do`), AI skills, agent workflow docs

Next: Phase 6 (complex widget support, Linux subsystem access) and Phase 7 (shadcn-style distribution via `uvx qt-ai-dev-tools init`).

See [ROADMAP.md](docs/ROADMAP.md) for the full plan.

## Development

```bash
make lint          # ruff check + basedpyright (strict)
make lint-fix      # auto-fix lint issues
make test          # fast offscreen pytest-qt tests (no VM needed)
make test-full     # all tests including AT-SPI, screenshots, CLI
make test-cli      # CLI integration tests only
make status        # check Xvfb, openbox, AT-SPI in VM
make screenshot    # capture current VM display
make destroy       # tear down VM
```

Note: `make workspace-init` must run before VM-dependent make targets (generates Vagrantfile, provision.sh from templates).

### Project structure

```
src/qt_ai_dev_tools/
  _atspi.py        # AtspiNode wrapper -- all raw AT-SPI access confined here
  pilot.py         # QtPilot: connect, find, click, type, read
  cli.py           # Typer CLI entry point
  interact.py      # xdotool click/type/key, AT-SPI actions
  state.py         # Read widget name, role, extents, text
  screenshot.py    # Screenshot via scrot
  models.py        # Extents, WidgetInfo data types
  vagrant/
    workspace.py   # WorkspaceConfig + template rendering
    vm.py          # VM lifecycle commands
    templates/     # Jinja2 templates (Vagrantfile, provision.sh)
skills/            # AI agent skills (setup, app interaction)
app/main.py        # Sample PySide6 todo app (test target)
tests/             # pytest-qt + AT-SPI + CLI integration tests
```

## Documentation

- [Roadmap](docs/ROADMAP.md) -- phases, priorities, and design decisions
- [Philosophy](docs/PHILOSOPHY.md) -- design principles and architectural decisions

## Not to be confused with

[qt-pilot](https://github.com/neatobandit0/qt-pilot) is a different project that uses an in-process Qt test harness requiring `setObjectName()` on widgets. qt-ai-dev-tools uses AT-SPI externally, works with any Qt app without modification, and can access Linux subsystems beyond the application.
