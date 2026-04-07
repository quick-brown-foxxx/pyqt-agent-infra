# qt-ai-dev-tools

Chrome Dev Tools but for Linux Qt desktop apps — give your AI agent eyes and hands to inspect, click, type, and screenshot any Qt/PySide application on Linux.

## The problem

AI coding agents can build Qt apps, but they can't see or interact with them. There's no equivalent of Chrome DevTools for desktop applications. When your agent writes UI code, it's flying blind — no way to verify layouts, click buttons, fill forms, or confirm that changes actually work.

## What this gives your agent

qt-ai-dev-tools bridges that gap. Your AI agent can:

**Core interaction** — see and control the app:
- **Full widget tree** — every button, label, text field, menu, and dialog, with roles, names, and coordinates, via AT-SPI. Filter with `--visible`, `--exact`, `--index`, and `--app` flags for precise targeting
- **Click, type, press keys** — real X11 input events via xdotool. Compound commands like `fill` (focus + clear + type) and `do` (click + verify/screenshot) for common workflows
- **Screenshots** — visual verification after any interaction (~14-22 KB PNG, cheap to send to an LLM). Snapshot save/diff for comparison

**Forms and data** — handle user input:
- **Fill forms** — focus fields, clear existing text, type new values in one command
- **Automate file dialogs** — detect, fill, accept, and cancel native Qt file dialogs via AT-SPI
- **Clipboard** — read and write the system clipboard for copy/paste workflows

**Desktop integration** — interact beyond the app window:
- **System tray** — list tray icons, click them, read context menus, select items via D-Bus SNI
- **Notifications** — listen for desktop notifications, dismiss them, invoke actions via D-Bus
- **Audio** — create PipeWire virtual microphones, play audio into apps, record output, verify non-silence

**Runtime eval** — reach inside the process:
- **Execute code inside the app** — run arbitrary Python via a Unix socket bridge, accessing widgets, properties, and Qt internals directly

**VM environment** — isolated and reproducible:
- **Vagrant VM** — Ubuntu 24.04 with Xvfb, openbox, AT-SPI, and D-Bus pre-configured. No host contamination. Templated with Jinja2, multi-provider support

The agent never modifies or instruments the target app. It uses the same accessibility tree that screen readers use, from the outside.

## How it works

```
  AI Agent (Claude Code, etc.)
       |
       |  shell commands
       v
  qt-ai-dev-tools CLI
       |
       |  auto-detects host vs VM
       |  (proxies through SSH when on host)
       |
       +---> AT-SPI (widget tree: roles, names, coords, text)
       +---> xdotool (clicks, keystrokes, text input)
       +---> scrot (screenshots)
       +---> subsystems (clipboard, file dialogs, tray, notifications, audio)
       |
  [ Vagrant VM: Ubuntu 24.04 + Xvfb + openbox + D-Bus ]
       |
       v
  Target Qt/PySide App (unmodified)
```

CLI allows to execute any commands in VM, simplifying ssh connection.

## Host requirements

- **Linux** (Fedora, Ubuntu, Arch, etc.)
- **Vagrant** with the **libvirt** provider (`vagrant-libvirt` plugin + QEMU/KVM)
- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**

VirtualBox is partially supported in templates but only libvirt has been tested.

## Getting started

### 1. Install the agent skills

```bash
npx -y skills add quick-brown-foxxx/qt-ai-dev-tools
```

This gives your agent five skills:
- `qt-dev-tools-setup` — install and configure the environment
- `qt-app-interaction` — inspect, click, type, verify (core workflow)
- `qt-form-and-input` — fill forms, handle file dialogs, clipboard
- `qt-desktop-integration` — system tray, notifications, audio
- `qt-runtime-eval` — execute Python inside running apps

### 2. Ask your agent to set up the toolkit

The agent will use the `qt-dev-tools-setup` skill to:
- Copy the toolkit into your project
- Initialize a Vagrant workspace
- Boot the VM and verify the environment

### 3. Start interacting

Once set up, the agent uses the appropriate skill for each task. `qt-app-interaction` covers the core workflow: **inspect** the widget tree → **interact** with widgets → **verify** results. `qt-form-and-input` handles form filling, file dialogs, and clipboard. `qt-desktop-integration` covers system tray, notifications, and audio. `qt-runtime-eval` enables executing Python inside running apps for deeper inspection.

### Manual installation

**Option A — shadcn-style local copy** (recommended, agent owns the code):
```bash
uvx qt-ai-dev-tools init ./qt-ai-dev-tools
```

**Option B — pip install** (system-wide CLI/library):
```bash
pip install qt-ai-dev-tools
```

**Option C — follow the skill guide** directly: read `skills/qt-dev-tools-setup/SKILL.md` for step-by-step instructions.

## Project status

**Working now:**
- CLI with one-liner commands — `tree`, `click`, `type`, `screenshot`, `fill`, `do`, snapshot save/diff, and more
- Widget addressing — `--visible`, `--exact`, `--index` flags for precise targeting
- Multi-app support — `--app` flag to target a specific application
- Python library (`QtPilot`) with strict typing (basedpyright strict, typed AT-SPI wrapper)
- Vagrant VM environment — Xvfb + openbox + AT-SPI, templated with Jinja2, multi-provider support
- Compound commands — `fill` (focus + clear + type), `do` (click + verify/screenshot)
- Bridge — execute arbitrary Python inside running Qt apps via Unix socket
- Five Linux subsystem modules:
  - Clipboard (xsel/xclip read/write)
  - File dialogs (AT-SPI detect, fill, accept, cancel)
  - System tray (D-Bus SNI list, click, menu, select)
  - Notifications (D-Bus listen, dismiss, action)
  - Audio (PipeWire virtual mic, recording, verification)
- Distribution — `pip install qt-ai-dev-tools`, `uvx qt-ai-dev-tools init` (shadcn-style), five AI skills

**Next up:**
- Architecture rewrite — backend abstraction for multiple environments
- Docker environment — lighter-weight alternative to VM

See [ROADMAP.md](docs/ROADMAP.md) for the full plan and phase details.

### Debugging

Use `-v` to see shell commands being executed, `-vv` for full output, and `--dry-run` to preview without executing:

```bash
qt-ai-dev-tools -v tree              # show commands on stderr
qt-ai-dev-tools -vv vm up            # show commands + full output
qt-ai-dev-tools --dry-run vm up      # preview without executing
```

Logs are always written to `~/.local/state/qt-ai-dev-tools/logs/qt-ai-dev-tools.log`.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup, make targets, and contribution guidance.
