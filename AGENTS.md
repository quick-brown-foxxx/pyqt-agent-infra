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
  - `vagrant/` — Vagrant subsystem
    - `workspace.py` — `WorkspaceConfig` + `render_workspace()` template rendering
    - `vm.py` — VM lifecycle: up, status, ssh, destroy, sync, run
    - `templates/` — Jinja2 templates for Vagrantfile, provision.sh
- `app/main.py` — sample PySide6 todo app (test subject)
- `tests/` — pytest-qt + AT-SPI + CLI integration tests
- `pyproject.toml` — build config, deps, linting, CLI entry point
- `provision.sh` — VM setup: Xvfb, openbox, AT-SPI, PySide6 (generated from template)
- `Vagrantfile` — Ubuntu 24.04 VM (libvirt, 4GB RAM, 4 CPUs) (generated from template)
- `RESULTS.md` — proof-of-concept evaluation
- `docs/ROADMAP.md` — project roadmap

## Current state

Phases 1-5 complete. Phase 6 in progress — bridge eval (6.0) is complete. The project is a proper Python package (`src/qt_ai_dev_tools/`) with a CLI (`qt-ai-dev-tools`). All AT-SPI boundary typing is confined to `_atspi.py` with strict basedpyright enabled project-wide. Vagrant infrastructure is templated (Jinja2) with multi-provider support (libvirt + VirtualBox), static IP option, and auto-sync. Compound commands (`fill`, `do`) streamline agent interaction. The bridge feature adds `evaluate_script` equivalent — AI agents can execute arbitrary Python code inside running Qt apps via Unix socket. AI skills in `skills/` teach agents the inspect-interact-verify workflow. The next milestone is remaining Phase 6 tasks (complex widgets, subsystems) and Phase 7 (distribution).

## Key technical facts

- **AT-SPI** provides the widget tree (roles, names, coordinates). Use `gi.repository.Atspi`, NOT `pyatspi` (broken on Python 3.12).
- **`AtspiNode` wrapper** (`_atspi.py`) — ALL raw Atspi access is confined here. The rest of the codebase uses `AtspiNode` with typed properties (`name`, `role_name`, `children`, `get_extents()`, `get_text()`, `do_action()`). This keeps `# type: ignore` comments out of business logic.
- **basedpyright strict** — project runs with strict type checking. No global suppressions. Only `_atspi.py` has type ignores (confined AT-SPI boundary).
- **xdotool** for text input and clicks by coordinate. AT-SPI's `editable_text.insert_text()` does NOT work with Qt — it updates the accessibility layer but not Qt's internal model.
- **Openbox** window manager is required for correct xdotool coordinates.
- **Xvfb :99** is the virtual display. All tools need `DISPLAY=:99`.
- **scrot** for screenshots. Output is ~14-22KB PNG.
- **VM-first approach.** Vagrant is the primary environment — full OS isolation with D-Bus, audio, system tray access. Container/host support is Phase 8.
- **Jinja2 templates** — Vagrantfile and provision.sh are generated from templates via `qt-ai-dev-tools workspace init`. Templates live in `src/qt_ai_dev_tools/vagrant/templates/`.
- **Transparent VM proxy** — UI commands (tree, click, type, screenshot, etc.) auto-detect host vs VM via the `QT_AI_DEV_TOOLS_VM=1` env var (set inside the VM). On the host, they proxy through SSH to the VM. No `vm run` wrapping needed for qt-ai-dev-tools commands. Use `vm run` only for arbitrary commands (pytest, systemctl, etc.).
- **Tested provider: libvirt only.** VirtualBox support exists in templates but is NOT TESTED. Only libvirt (QEMU/KVM via vagrant-libvirt) has been verified.
- **Bridge** — runtime code execution inside Qt apps via Unix socket. `bridge.start()` in the app starts a server on `/tmp/qt-ai-dev-tools-bridge-<pid>.sock`. CLI `eval` command sends code, gets results as JSON. Pre-populated namespace includes `app`, `widgets`, `find()`, `findall()`, and common Qt classes. Dev-mode gated via `QT_AI_DEV_TOOLS_BRIDGE=1` env var.

## AI Skills

Agent skills in `skills/` teach AI agents the qt-ai-dev-tools workflow:
- `qt-dev-tools-setup` — install toolkit, configure VM, verify environment
- `qt-app-interaction` — inspect widgets, interact, verify results (the core workflow loop)

## Running things

**Note:** `make workspace-init` must be run before other make targets that depend on the VM (generates Vagrantfile, provision.sh from templates).

```bash
make up            # start VM (~10min first time)
make test          # fast offscreen pytest-qt tests
make test-full     # all tests including AT-SPI, screenshots, and CLI
make test-cli      # CLI integration tests only
make lint          # run ruff check + basedpyright
make lint-fix      # auto-fix lint issues
make screenshot    # screenshot current VM display
make status        # check Xvfb, openbox, AT-SPI status
make destroy       # tear down VM
```

### CLI usage

UI commands auto-detect host vs VM and proxy transparently. Run them directly from the host -- no `vm run` wrapping needed.

```bash
# UI commands (work the same from host or VM -- auto-proxy):
qt-ai-dev-tools tree                          # full widget tree
qt-ai-dev-tools tree --role "push button"     # filtered by role
qt-ai-dev-tools find --role "label" --json    # find + JSON output
qt-ai-dev-tools click --role "push button" --name "Save"
qt-ai-dev-tools type "hello world"
qt-ai-dev-tools key Return
qt-ai-dev-tools screenshot -o /tmp/shot.png
qt-ai-dev-tools apps                          # list AT-SPI apps
qt-ai-dev-tools wait --app "main.py"          # wait for app

# Compound commands (also auto-proxy):
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
- Don't assume container/host environments — VM is primary, everything else is Phase 6

## Documentation

- `docs/PHILOSOPHY.md` — foundational development principles
- `docs/ROADMAP.md` — project roadmap and task tracking
- `DEVELOPMENT.md` — development environment setup and make targets
