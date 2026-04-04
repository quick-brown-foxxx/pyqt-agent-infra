# qt-ai-dev-tools

Infrastructure for AI agents to interact with Qt/PySide apps on Linux — inspect widgets, click buttons, type text, take screenshots, read state. AT-SPI + xdotool + scrot as a Chrome DevTools MCP equivalent for Qt.

**Not to be confused with** [qt-pilot](https://github.com/neatobandit0/qt-pilot) — a different project using in-process Qt test harness. We use AT-SPI externally, work with any Qt app without modification, and can access Linux subsystems.

## Quick orientation

- `src/qt_ai_dev_tools/` — Python package: AT-SPI tree traversal, xdotool interaction, CLI
  - `pilot.py` — `QtPilot` class: connect to Qt app, find/click/type/read widgets
  - `cli.py` — Typer CLI: `qt-ai-dev-tools tree`, `click`, `find`, `screenshot`, etc.
  - `interact.py` — xdotool click/type/key, AT-SPI actions
  - `state.py` — read widget name, role, extents, text
  - `screenshot.py` — screenshot via scrot
  - `models.py` — `Extents`, `WidgetInfo` data types
- `app/main.py` — sample PySide6 todo app (test subject)
- `tests/` — pytest-qt + AT-SPI + CLI integration tests
- `scripts/vm-run.sh` — run commands inside Vagrant VM
- `scripts/screenshot.sh` — take screenshot in VM, copy to host
- `pyproject.toml` — build config, deps, linting, CLI entry point
- `provision.sh` — VM setup: Xvfb, openbox, AT-SPI, PySide6
- `Vagrantfile` — Ubuntu 24.04 VM (libvirt, 4GB RAM, 4 CPUs)
- `RESULTS.md` — proof-of-concept evaluation
- `docs/ROADMAP.md` — project roadmap

## Current state

Phase 1 complete. The project is a proper Python package (`src/qt_ai_dev_tools/`) with a CLI (`qt-ai-dev-tools`). Agents interact with Qt apps using one-liner commands instead of Python heredocs. The next milestone is VM workflow improvements (Phase 2) and agent integration (Phase 3).

## Key technical facts

- **AT-SPI** provides the widget tree (roles, names, coordinates). Use `gi.repository.Atspi`, NOT `pyatspi` (broken on Python 3.12).
- **xdotool** for text input and clicks by coordinate. AT-SPI's `editable_text.insert_text()` does NOT work with Qt — it updates the accessibility layer but not Qt's internal model.
- **Openbox** window manager is required for correct xdotool coordinates.
- **Xvfb :99** is the virtual display. All tools need `DISPLAY=:99`.
- **scrot** for screenshots. Output is ~14-22KB PNG.
- **VM-first approach.** Vagrant is the primary environment — full OS isolation with D-Bus, audio, system tray access. Container/host support is Phase 6.

## Running things

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

```bash
# In the VM (via vm-run.sh or make ssh):
qt-ai-dev-tools tree                          # full widget tree
qt-ai-dev-tools tree --role "push button"     # filtered by role
qt-ai-dev-tools find --role "label" --json    # find + JSON output
qt-ai-dev-tools click --role "push button" --name "Save"
qt-ai-dev-tools type "hello world"
qt-ai-dev-tools key Return
qt-ai-dev-tools screenshot -o /tmp/shot.png
qt-ai-dev-tools apps                          # list AT-SPI apps
qt-ai-dev-tools wait --app "main.py"          # wait for app
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
