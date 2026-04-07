# qt-ai-dev-tools

Infrastructure for AI agents to interact with Qt/PySide apps on Linux — inspect widgets, click buttons, type text, take screenshots, read state. AT-SPI + xdotool + scrot as a Chrome DevTools MCP equivalent for Qt.

**Not to be confused with** [qt-pilot](https://github.com/neatobandit0/qt-pilot) — a different project using in-process Qt test harness. We use AT-SPI externally, work with any Qt app without modification, and can access Linux subsystems.

## Foundational Philosophy

**YOU MUST read and internalize `docs/PHILOSOPHY.md` before writing any code.** It defines the non-negotiable principles (pit of success, explicitness through types, fail fast, Result-based errors, testing philosophy, architecture, tooling) that drive every decision in this project. All rules below are applications of those principles.

@docs/PHILOSOPHY.md

---

## Critical Reading Path

1. **New context?** Review this document and `docs/PHILOSOPHY.md` fully.
2. **Implementation phase?** Consult `### Skills` section below for detailed  instructions.

**Invariant:** Run `uv run poe lint_full` continuously during development, not just at finalization.

## Quick orientation

- `src/qt_ai_dev_tools/` — Python package: AT-SPI tree traversal, xdotool interaction, CLI
  - `_atspi.py` — `AtspiNode` typed wrapper: ALL raw `gi.repository.Atspi` access confined here
  - `pilot.py` — `QtPilot` class: connect to Qt app, find/click/type/read widgets (uses `AtspiNode`)
  - `cli.py` — Typer CLI: `qt-ai-dev-tools tree`, `click`, `find`, `screenshot`, `workspace`, `vm`
  - `interact.py` — xdotool click/type/key, AT-SPI actions (accepts `AtspiNode`)
  - `state.py` — read widget name, role, extents, text (accepts `AtspiNode`)
  - `screenshot.py` — screenshot via scrot
  - `models.py` — `Extents`, `WidgetInfo` data types
  - `bridge/` — Bridge: runtime code execution inside Qt apps
    - `__init__.py` — public API: start(), stop()
    - `_server.py` — Unix socket server, main-thread dispatch via QObject signals
    - `_client.py` — socket client for CLI
    - `_eval.py` — eval/exec engine with stdout capture
    - `_qt_namespace.py` — pre-populated namespace (Qt imports, widgets, helpers)
    - `_protocol.py` — EvalRequest/EvalResponse, JSON codec
    - `_bootstrap.py` — sys.remote_exec injection (Python 3.14+)
  - `subsystems/` — Linux subsystem helpers for AI agents
    - `clipboard.py` — xsel/xclip wrapper: read/write system clipboard
    - `file_dialog.py` — AT-SPI automation of QFileDialog (detect, fill, accept, cancel)
    - `tray.py` — D-Bus SNI interaction: list/click/menu/select system tray items
    - `notify.py` — D-Bus notification daemon: listen/dismiss/action
    - `audio.py` — PipeWire wrapper: virtual mic, record, verify, sources/status
    - `models.py` — Subsystem data types (FileDialogInfo, TrayItem, Notification, AudioVerification, etc.)
    - `_subprocess.py` — Typed subprocess helpers: check_tool(), run_tool()
  - `vagrant/` — Vagrant subsystem
    - `workspace.py` — `WorkspaceConfig` + `render_workspace()` template rendering
    - `vm.py` — VM lifecycle: up, status, ssh, destroy, sync, run
    - `templates/` — Jinja2 templates for Vagrantfile, provision.sh
  - `installer.py` — Shadcn-style installer: `uvx qt-ai-dev-tools init` copies toolkit into project
  - `__version__.py` — Package version (single source of truth)
- `app/main.py` — sample PySide6 todo app (test subject)
- `tests/` — pytest-qt + AT-SPI + CLI integration tests
- `pyproject.toml` — build config, deps, linting, CLI entry point
- `provision.sh` — VM setup: Xvfb, openbox, AT-SPI, PySide6 (generated from template)
- `Vagrantfile` — Ubuntu 24.04 VM (libvirt, 4GB RAM, 4 CPUs) (generated from template)
- `RESULTS.md` — proof-of-concept evaluation
- `docs/ROADMAP.md` — project roadmap

## Current state

Phases 1-7 complete. The project is a proper Python package (`src/qt_ai_dev_tools/`) with a CLI (`qt-ai-dev-tools`), installable via `pip install qt-ai-dev-tools` or copyable via `uvx qt-ai-dev-tools init`. All AT-SPI boundary typing is confined to `_atspi.py` with strict basedpyright enabled project-wide. Vagrant infrastructure is templated (Jinja2) with multi-provider support (libvirt + VirtualBox), static IP option, and auto-sync. Compound commands (`fill`, `do`) streamline agent interaction. The bridge feature adds `evaluate_script` equivalent via Unix socket. Five Linux subsystem modules (clipboard, file dialog, system tray, notifications, audio) give agents access to desktop capabilities beyond the widget tree. Phase 6.5 hygiene improvements include setup script, pre-commit hooks, pytest markers, and expanded test coverage. The shadcn-style installer (`installer.py`) copies the full toolkit into target projects. The next milestone is Phase 8 (container & host support).

## Key technical facts

- **AT-SPI** provides the widget tree (roles, names, coordinates). Use `gi.repository.Atspi`, NOT `pyatspi` (broken on Python 3.12).
- **`AtspiNode` wrapper** (`_atspi.py`) — ALL raw Atspi access is confined here. The rest of the codebase uses `AtspiNode` with typed properties (`name`, `role_name`, `children`, `get_extents()`, `get_text()`, `do_action()`). This keeps `# type: ignore` comments out of business logic.
- **basedpyright strict** — project runs with strict type checking. No global suppressions. Type-ignore boundaries are confined to: (1) `_atspi.py` (AT-SPI/gi bindings), (2) bridge modules `_server.py` and `_qt_namespace.py` (PySide6 imports used inside the target app process). A PySide6 typed wrapper was investigated and ruled out — PySide6 lacks stubs in the venv (it's a system dep), making full wrapping impractical.
- **xdotool** for text input and clicks by coordinate. AT-SPI's `editable_text.insert_text()` does NOT work with Qt — it updates the accessibility layer but not Qt's internal model.
- **Openbox** window manager is required for correct xdotool coordinates.
- **Xvfb :99** is the virtual display. All tools need `DISPLAY=:99`.
- **scrot** for screenshots. Output is ~14-22KB PNG.
- **VM-first approach.** Vagrant is the primary environment — full OS isolation with D-Bus, audio, system tray access. Container/host support is Phase 8.
- **Jinja2 templates** — Vagrantfile and provision.sh are generated from templates via `qt-ai-dev-tools workspace init`. Templates live in `src/qt_ai_dev_tools/vagrant/templates/`.
- **Host/VM command parity** — UI commands (tree, click, type, screenshot, etc.) work identically from the host or inside the VM. On the host, they execute via SSH automatically. No `vm run` wrapping needed for qt-ai-dev-tools commands. Use `vm run` only for arbitrary commands (pytest, systemctl, etc.). Detection is via `QT_AI_DEV_TOOLS_VM=1` env var set inside the VM.
- **X11-only** — The toolkit targets X11 applications via Xvfb in the VM. Wayland is not supported. The host's display server doesn't matter — everything runs in the VM's virtual X11 display.
- **Tested provider: libvirt only.** VirtualBox support exists in templates but is NOT TESTED. Only libvirt (QEMU/KVM via vagrant-libvirt) has been verified.
- **Bridge** — runtime code execution inside Qt apps via Unix socket. `bridge.start()` in the app starts a server on `/tmp/qt-ai-dev-tools-bridge-<pid>.sock`. CLI `eval` command sends code, gets results as JSON. Pre-populated namespace includes `app`, `widgets`, `find()`, `findall()`, and common Qt classes. Dev-mode gated via `QT_AI_DEV_TOOLS_BRIDGE=1` env var. **Note:** bridge cannot respond while a modal dialog (QFileDialog, QMessageBox) is open — use AT-SPI/xdotool for dialog interaction.
- **Clipboard** — uses `xsel` (preferred, exits immediately) with `xclip` fallback. `xclip` write hangs because it stays alive to serve the X selection — `xsel` avoids this.
- **System tray** — requires SNI (StatusNotifierItem) D-Bus watcher. Openbox + stalonetray provides XEmbed tray only, not SNI. Full tray D-Bus interaction needs KDE/GNOME or `snixembed`.
- **Notifications** — `notify.listen()` uses `dbus-monitor` on `org.freedesktop.Notifications`. Qt's `QSystemTrayIcon.showMessage()` may not emit standard D-Bus signals depending on the notification backend.
- **Test parallelism** — `make test-unit` runs unit tests in parallel via pytest-xdist (`-n auto`) on the host without VM. `make test-vm` uses a two-phase approach: unit tests in parallel first, then e2e/integration tests serially. `make test` runs `test-vm` plus host-side proxy tests. E2E tests cannot run with xdist (Qt/AT-SPI worker crashes). The `pytest_collection_modifyitems` hook in `tests/conftest.py` auto-groups tests for loadgroup mode if used manually.

## AI Skills

Agent skills in `skills/` teach AI agents the qt-ai-dev-tools workflow:
- `qt-dev-tools-setup` — install toolkit, configure VM, verify environment
- `qt-app-interaction` — inspect widgets, interact, verify results (the core workflow loop)

## Running things

**Note:** `make workspace-init` must be run before other make targets that depend on the VM (generates Vagrantfile, provision.sh from templates).

```bash
make setup         # initial project setup (uv sync + pre-commit install)
make up            # start VM (~10min first time)
make test          # ALL tests — VM + host proxy, zero skips
make test-vm       # all VM tests (unit parallel + e2e/integration serial)
make test-unit     # unit tests only (parallel, no VM needed)
make test-e2e      # e2e tests only
make test-cli      # CLI integration only
make lint          # run ruff check + basedpyright
make lint-fix      # auto-fix lint issues
make screenshot    # screenshot current VM display
make status        # check Xvfb, openbox, AT-SPI status
make destroy       # tear down VM
```

### CLI usage

UI commands work the same from host or VM — no SSH wrapping needed.

```bash
# UI commands (work the same from host or VM):
qt-ai-dev-tools tree                          # full widget tree
qt-ai-dev-tools tree --role "push button"     # filtered by role
qt-ai-dev-tools find --role "label" --json    # find + JSON output
qt-ai-dev-tools click --role "push button" --name "Save"
qt-ai-dev-tools type "hello world"
qt-ai-dev-tools key Return
qt-ai-dev-tools screenshot -o /tmp/shot.png
qt-ai-dev-tools apps                          # list AT-SPI apps
qt-ai-dev-tools wait --app "main.py"          # wait for app

# Compound commands (also work from host or VM):
qt-ai-dev-tools fill "hello" --role text --name input   # focus + clear + type
qt-ai-dev-tools do click "Save" --role "push button" --verify "label:status contains Saved"
qt-ai-dev-tools do click "Add" --screenshot              # click + screenshot

# Workspace management (runs on host):
qt-ai-dev-tools workspace init --path .                    # default config
qt-ai-dev-tools workspace init --memory 8192 --cpus 8      # custom VM resources

# VM lifecycle (runs on host):
qt-ai-dev-tools vm up                         # start VM
qt-ai-dev-tools vm status                     # check VM status
qt-ai-dev-tools vm ssh                        # SSH into VM
qt-ai-dev-tools vm sync                       # rsync files to VM
qt-ai-dev-tools vm sync-auto                  # background file sync
qt-ai-dev-tools vm run "pytest /vagrant/tests/"  # arbitrary command in VM
qt-ai-dev-tools vm destroy                    # destroy VM

# Bridge commands (eval code inside running Qt app):
qt-ai-dev-tools eval "app.windowTitle()"          # eval expression
qt-ai-dev-tools eval "widgets['status_label'].text()"  # access named widgets
qt-ai-dev-tools eval --json "findall(QPushButton)"     # JSON output
qt-ai-dev-tools eval --file script.py                   # eval from file
qt-ai-dev-tools eval --file - < script.py               # eval from stdin
qt-ai-dev-tools eval --pid 1234 "code"                  # target specific app
qt-ai-dev-tools bridge status                            # list active bridges
qt-ai-dev-tools bridge inject --pid 1234                 # inject into 3.14+ app

# Subsystem commands (also work from host or VM):
qt-ai-dev-tools clipboard read                           # read system clipboard
qt-ai-dev-tools clipboard write "hello"                  # write to clipboard
qt-ai-dev-tools file-dialog detect                       # detect open file dialog
qt-ai-dev-tools file-dialog fill /path/to/file           # type path into dialog
qt-ai-dev-tools file-dialog accept                       # click Open/Save
qt-ai-dev-tools tray list                                # list system tray items
qt-ai-dev-tools tray click "MyApp"                       # activate tray icon
qt-ai-dev-tools tray menu "MyApp"                        # get tray context menu
qt-ai-dev-tools notify listen --timeout 10               # capture notifications
qt-ai-dev-tools notify dismiss 42                        # close notification
qt-ai-dev-tools audio virtual-mic start                  # create virtual mic
qt-ai-dev-tools audio virtual-mic play audio.wav         # feed audio to app
qt-ai-dev-tools audio record --duration 3 -o /tmp/out.wav
qt-ai-dev-tools audio verify /tmp/out.wav                # check not silence
```

### Debugging

```bash
# Show all shell commands being executed:
qt-ai-dev-tools -v tree

# Show commands + their full stdout/stderr:
qt-ai-dev-tools -vv vm up

# Preview what would run without executing:
qt-ai-dev-tools --dry-run vm up

# Combine verbose + dry-run:
qt-ai-dev-tools -v --dry-run click --role "push button" --name "Save"

# Log file (always written, even without -v):
# ~/.local/state/qt-ai-dev-tools/logs/qt-ai-dev-tools.log
```

## Workflow for improving this project

### Before starting work

1. Read `docs/ROADMAP.md` to understand current priorities
2. Check `RESULTS.md` for known constraints and pain points
3. If the VM is needed: `make up` and `make status` to verify environment

### Development cycle

The project evolves through typed tasks (see roadmap for definitions):

- **explore** — research before building. Write findings in `docs/`. Update roadmap.
- **prototype** — quick throwaway to test an idea. May live in `prototypes/` or a branch.
- **implement** — real code, tested, goes into `src/qt_ai_dev_tools/` package.
- **test** — verify features. Prefer automated tests in `tests/`.
- **doc** — persist learnings in `docs/` or inline.

### When implementing

1. Check if the task is in the roadmap. If not, decide if it should be added.
2. Write the code. Keep it simple — no speculative abstractions.
3. Test it. For CLI commands: test against the sample app in the VM. For library code: pytest.
4. Update `docs/ROADMAP.md` with findings and next steps.

### When exploring/researching

1. Document findings in `docs/` (e.g., `docs/findings-container-env.md`).
2. Update roadmap task with results and adjusted plan.
3. If the exploration changes priorities, reorder the roadmap.

### Key principle: you are the user

This tool is built FOR AI agents BY AI agents. When working on it:
- Actually use the tool to interact with Qt apps
- Notice what's painful and fix it
- Don't guess what the agent needs — be the agent, feel the friction
- Compound commands and shortcuts should emerge from real usage, not speculation

### Skills — ALWAYS CHECK, ALWAYS USE

<EXTREMELY_IMPORTANT>

**BEFORE writing ANY code, ALWAYS check available skills and USE every skill that matches your scope.** Skills are project standards — code that ignores them WILL fail review. When delegating to subagents, tell them which skills to use.

#### Python

- `writing-python-code` — ALWAYS load when writing/editing Python. NEVER write Python without this.
- `testing-python` — ALWAYS load when writing tests or fixtures. NEVER write pytest tests without this.
- `setting-up-python-projects` — ALWAYS load when bootstrapping a new package. NEVER set up pyproject.toml manually.
- `writing-python-scripts` — ALWAYS load when creating standalone scripts. NEVER write single-file CLI tools without this.
- `setting-up-logging` — DO load when adding or changing logging. DON'T configure logging manually.
- `building-multi-ui-apps` — DO load when app has both CLI and/or GUI and/or API sharing logic. DON'T duplicate business logic across interfaces.

</EXTREMELY_IMPORTANT>

### Code style

- Python 3.12+, PySide6
- Type hints on public APIs
- Tests use pytest + pytest-qt or similar tools
- CLI uses typer

### What NOT to do

- Don't add features that aren't needed yet (the roadmap has phases for a reason)
- Don't over-abstract the library — it's glue between AT-SPI and xdotool, not a framework
- Don't make the CLI stateful between invocations — each command is self-contained
- Don't assume container/host environments — VM is primary, everything else is Phase 8

## Documentation

- `docs/PHILOSOPHY.md` — foundational development principles
- `docs/ROADMAP.md` — project roadmap and task tracking
- `docs/subsystems-guide.md` — Linux subsystem modules (clipboard, file dialog, tray, notify, audio)
- `DEVELOPMENT.md` — development environment setup and make targets
