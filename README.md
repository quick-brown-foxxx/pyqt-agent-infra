# qt-ai-dev-tools

Chrome Dev Tools but for Linux Qt desktop apps — give your AI agent eyes and hands to inspect, click, type, and screenshot any Qt/PySide application on Linux (X11).

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

The agent doesn't modify or instrument the target app. It uses the same accessibility tree that screen readers use, from the outside.

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

Most CLI commands work identically from the host or inside the VM — no SSH wrapping needed. Use `vm run` only for arbitrary commands (pytest, systemctl, etc.).

**Note:** This toolkit targets X11 applications. Wayland is not supported. All interaction happens inside the VM where Xvfb provides the X11 display server, so the host's display server doesn't matter.

## Host requirements

- **Linux** (Fedora, Ubuntu, Arch, etc.)
- **Vagrant** with the **libvirt** provider (`vagrant-libvirt` plugin + QEMU/KVM), **virtualbox** is supported but not tested
- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**

## Getting started

### 1. Install the agent skills

```bash
npx -y skills add quick-brown-foxxx/qt-ai-dev-tools
```

This gives your agent five skills:
- `qt-devtools-setup` — install and configure the environment
- `qt-devtools-app-interaction` — inspect, click, type, verify (core workflow)
- `qt-devtools-form-and-input` — fill forms, handle file dialogs, clipboard
- `qt-devtools-desktop-integration` — system tray, notifications, audio
- `qt-devtools-runtime-eval` — execute Python inside running apps

### 2. Ask your agent to set up the toolkit

Run `/qt-devtools-setup` skill as command or ask agent to load and execute it:
- Copy the toolkit into your project
- Initialize a Vagrant workspace
- Boot the VM and verify the environment

### 3. Start interacting

Once set up, the agent uses the appropriate skill for each task. `qt-devtools-app-interaction` covers the core workflow: **inspect** the widget tree → **interact** with widgets → **verify** results. `qt-devtools-form-and-input` handles form filling, file dialogs, and clipboard. `qt-devtools-desktop-integration` covers system tray, notifications, and audio. `qt-devtools-runtime-eval` enables executing Python inside running apps for deeper inspection.

### Manual installation

**Option A — persistent install** (recommended for repeated use):
```bash
uv tool install qt-ai-dev-tools
qt-ai-dev-tools workspace init
```
Installs into `~/.local/bin/`. Subsequent runs are instant — no temporary venv creation.

**Option B — quick try via uvx** (zero-install, good for one-off usage):
```bash
uvx qt-ai-dev-tools workspace init
```
Creates a temporary venv on each invocation. Convenient for trying the tool, but slower for repeated use.

**Option C — local copy** (advanced, you own and maintain the code):
```bash
uvx qt-ai-dev-tools install-and-own ./qt-ai-dev-tools --yes-I-will-maintain-it
```

<details>
<summary>Other install options</summary>

- **`pipx install qt-ai-dev-tools`** — same isolated-venv model as `uv tool install`, just slower. Works if you already have pipx.
- **`pip install qt-ai-dev-tools`** (in a venv) — works fine inside a virtual environment. No isolation from other packages in that venv.
- **`pip install --user qt-ai-dev-tools`** (global) — lands in `~/.local/`. On many Linux distros (Fedora, Debian, Ubuntu) system Python is managed by the OS and global pip installs are restricted or break things. Not recommended — use `uv tool` or `pipx` instead.

</details>

## Project status

**Working now (beta):**
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
- Distribution — `uvx qt-ai-dev-tools <any-command>` without installation, `install-and-own` for local copies, five AI skills

Subsystem commands (clipboard, file dialog, tray, notifications, audio) are **alpha** — functional but less battle-tested.

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
