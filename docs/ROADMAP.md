# qt-ai-dev-tools roadmap

**Goal:** Give AI agents first-class access to Qt/PySide apps — inspect widgets, interact, take screenshots, read state — with the same ease as Chrome DevTools MCP but with typed widget access via AT-SPI.

**Primary user:** AI coding agents (Claude Code, etc.) working on PySide/PyQt projects.

## Design principles

1. **Composable over monolithic.** 80% of use cases should be one-liners (`qt-ai-dev-tools tree`, `qt-ai-dev-tools click "Save"`). The remaining 20% use the Python library directly. No "super-tool" that tries to do everything.
2. **Agent-scriptable.** The agent can write small Python scripts using `qt_ai_dev_tools` as a library when the CLI isn't enough. Primitives are always exposed.
3. **Drop-in portable.** Works in any PySide6/PyQt6 project. `uvx qt-ai-dev-tools init` copies the full toolkit into the project — source, templates, skills, config. Agent owns the code, can read and extend it. No global install required, only `uv`.
4. **VM-first.** Vagrant VM is the primary environment — it gives full OS isolation and access to Linux subsystems (D-Bus, audio, system tray). Container/host support comes later as a lighter-weight option for UI-only workflows.
5. **Feedback-rich.** Every action returns enough context for the agent to know what happened — widget state after click, screenshot after interaction, error messages with available alternatives.

## Workflow rules

Rules that apply to every phase of work:

1. **Clean up before proceeding.** Fix all important code issues and tech debt from the code quality backlog before starting a new phase. Don't carry known bugs forward.
2. **Clean worktree at phase end.** Commit and push all changes, or explicitly discard uncommitted work. The worktree must be clean at the end of every phase.
3. **Quality gate after every phase.** Run quality validator agents after completing each phase:
   - Run separate code analyzer subagents checking alignment with `writing-python-code`, `testing-python`, and architecture skill rules
   - Bugs found → fix immediately
   - Non-critical issues → add to code quality backlog in this roadmap
   - Phase is not "done" until the quality gate passes

## Naming note

The name `qt-pilot` is taken by [neatobandit0/qt-pilot](https://github.com/neatobandit0/qt-pilot) — a similar project but with a fundamentally different approach (in-process Qt test harness requiring `setObjectName()` on widgets). Our tool uses AT-SPI externally, works with any Qt app without modification, and can access Linux subsystems beyond the app. Hence the distinct name `qt-ai-dev-tools`.

## Delivery shape

The final product is a **composable toolkit**, not a single binary:

| Layer | What | How agents use it |
|-------|------|-------------------|
| **Python library** (`qt_ai_dev_tools`) | AT-SPI + xdotool primitives | `from qt_ai_dev_tools import QtPilot` in custom scripts |
| **CLI** (`qt-ai-dev-tools`) | One-liner commands | `qt-ai-dev-tools tree`, `qt-ai-dev-tools click "Save"`, `qt-ai-dev-tools screenshot` |
| **AI skills** | Workflow guidance | Teach agents the inspect→interact→verify loop |
| **VM environment** | Vagrant + Xvfb + AT-SPI setup | Scripts that create and manage the headless Qt environment |

Distribution: Primary: `uvx qt-ai-dev-tools init ./qt-ai-dev-tools` — copies full toolkit (source, templates, skills, config) into the project directory. Agent owns the code, can read and extend it. Secondary: `pip install qt-ai-dev-tools` for library/CLI-only usage. Skills: installed via skills tooling (`npx -y skills add ...`) or bundled with the toolkit copy.

---

## Phase 0: Foundation

**Status:** Done (current repo is the proof-of-concept).

What exists:
- Vagrant VM with Xvfb + openbox + AT-SPI + xdotool + scrot
- `qt_pilot.py` library (~240 lines): tree traversal, click, type, read state, screenshot
- Sample PySide6 app + 8 passing tests
- `vm-run.sh` and `screenshot.sh` helper scripts
- RESULTS.md documenting what works, what doesn't, pain points

Key learnings:
- AT-SPI + xdotool + scrot = full Chrome DevTools equivalent for Qt
- AT-SPI `editable_text.insert_text()` doesn't work — must use xdotool keystrokes
- Openbox required for correct xdotool coordinates
- `gi.repository.Atspi` works on Python 3.12; `pyatspi` does not

---

## Phase 1: CLI & library refactor

**Goal:** Replace verbose Python heredocs with one-liner CLI commands. Make `qt_ai_dev_tools` a proper package.

### 1.1 — [implement] Package structure

Refactor into a proper Python package:

```
qt_ai_dev_tools/
  __init__.py          # QtPilot class (from current qt_pilot.py)
  cli.py               # CLI entry point
  tree.py              # Tree inspection/formatting
  interact.py          # Click, type, key press
  state.py             # Read widget names, text, extents
  screenshot.py        # Screenshot helpers
```

Keep it as a single importable package. No deep abstractions — just logical file splits.

### 1.2 — [implement] CLI interface

```bash
# Tree inspection
qt-ai-dev-tools tree                          # full widget tree
qt-ai-dev-tools tree --role "push button"     # filtered
qt-ai-dev-tools find --role "text" --name "input"  # find + print details

# Interaction
qt-ai-dev-tools click --role "push button" --name "Save"
qt-ai-dev-tools click --index 0 --role "push button"  # by index when name is ambiguous
qt-ai-dev-tools type "hello world"            # type into focused widget
qt-ai-dev-tools key Return                    # press key
qt-ai-dev-tools focus --role "text"           # focus widget

# State
qt-ai-dev-tools state --role "label" --name "status"   # print name/text/extents
qt-ai-dev-tools text --role "text"            # get text content

# Screenshots
qt-ai-dev-tools screenshot                    # stdout: path to PNG
qt-ai-dev-tools screenshot --output /tmp/s.png

# Meta
qt-ai-dev-tools apps                          # list AT-SPI apps on bus
qt-ai-dev-tools wait --app "main.py" --timeout 10  # wait for app to appear
```

Design: each command is self-contained, prints result to stdout, exits. No persistent state between calls. Agent chains commands via shell.

### 1.3 — [implement] JSON output mode

```bash
qt-ai-dev-tools tree --json                   # machine-readable tree
qt-ai-dev-tools find --role "label" --json    # [{role, name, text, extents}, ...]
qt-ai-dev-tools state --role "text" --json    # {role, name, text, extents}
```

Agents can parse JSON when they need structured data. Human-readable is default.

### 1.4 — [test] CLI smoke tests

Test each CLI command against the sample app. Run in VM. Verify output format.

### 1.5 — [doc] CLI usage guide

Document all commands with examples. This becomes the AI skill content.

---

## Phase 2: Type system hardening

**Status:** Done. Created `_atspi.py` typed wrapper confining all `# type: ignore` comments to one module. Migrated `pilot.py`, `state.py`, `interact.py`, and `cli.py` to use `AtspiNode`. Removed all 4 global basedpyright suppressions and enabled strict checks (`reportExplicitAny`, `reportUnnecessaryTypeIgnoreComment`, `reportPrivateUsage`, `reportOptionalMemberAccess`, `reportOptionalCall`, `reportAttributeAccessIssue`).
**Goal:** Eliminate global basedpyright suppressions, confine AT-SPI boundary typing to a single module, enable strict checks project-wide.

### 2.1 — [implement] Typed AT-SPI wrapper (`_atspi.py`)

Create `src/qt_ai_dev_tools/_atspi.py` — a typed `AtspiNode` wrapper class that encapsulates all `gi.repository.Atspi` access behind typed properties and methods. All `# type: ignore` comments for Atspi move into this single module.

Key design:
- `AtspiNode` wraps a native Atspi accessible object
- Properties: `name`, `role_name`, `child_count`, `children`
- Methods: `child_at()`, `get_extents()`, `get_text()`, `get_action_names()`, `do_action()`
- Static: `AtspiNode.desktop()` replaces all `Atspi.get_desktop()` calls
- `__slots__` for performance

Expected: ~12 confined type ignores in `_atspi.py` instead of 39 scattered across 4 files.

### 2.2 — [implement] Migrate codebase to `AtspiNode`

Refactor `pilot.py`, `state.py`, `interact.py` to accept and return `AtspiNode` instead of `object`. These files should have zero `# type: ignore` comments after migration.

### 2.3 — [implement] Eliminate cli.py duplication

`apps()` and `wait()` in `cli.py` duplicate Atspi desktop traversal (14 of 39 total ignores). Refactor to use `AtspiNode.desktop()` or `QtPilot`. Eliminate all 14 type ignores.

### 2.4 — [implement] Enable strict basedpyright

Remove global suppressions from `pyproject.toml`:
```toml
# DELETE these:
reportUnknownMemberType = "none"
reportUnknownArgumentType = "none"
reportUnknownVariableType = "none"
reportMissingTypeStubs = "none"
```

Add additional strict rules:
```toml
reportExplicitAny = "error"
reportUnnecessaryTypeIgnoreComment = "error"
reportPrivateUsage = "error"
reportOptionalMemberAccess = "error"
reportOptionalCall = "error"
reportAttributeAccessIssue = "error"
```

### 2.5 — [implement] Optional: AT-SPI type stub

Create minimal `.pyi` stub at `src/stubs/gi/repository/Atspi.pyi` covering only used methods. Gives IDE completion inside `_atspi.py`. Configure `stubPath = "src/stubs"`.

### 2.6 — [test] Verify strict mode

Run full test suite + lint. Confirm zero regressions, zero new suppressions needed outside `_atspi.py`.

---

## Phase 3: Vagrant subsystem consolidation

**Status:** Done. Moved Vagrantfile, provision.sh, vm-run.sh, and screenshot.sh into Jinja2 templates (`src/qt_ai_dev_tools/vagrant/templates/`). Added `workspace init` CLI command to generate workspace files from templates with configurable parameters. Added `vm up|status|ssh|sync|destroy|run` CLI commands with `--workspace` support. Root infra files are now regenerated from templates.
**Goal:** Consolidate scattered Vagrant/VM helper files into a self-contained subsystem. Make configs templatable so agents can create ad-hoc environments in their target projects.

**Context:** After Phase 1, the project root still has raw ad-hoc infrastructure: `Vagrantfile`, `provision.sh`, `.vagrant-ssh-config`, `Makefile`, `scripts/vm-run.sh`, `scripts/screenshot.sh`. These are hardcoded to one setup (libvirt, 4GB RAM, 4 CPUs, specific package list). The intended workflow is: agent working on a real Qt app creates a `qt-ai-dev-tools/` folder in their project and keeps all ad-hoc configs, Vagrantfiles, SSH configs, notes there. The tool should support this layout natively.

### 3.1 — [explore] Agent workspace layout

Design the workspace layout that agents will use in real projects:

```
my-qt-app/
├── src/                      # the actual Qt app
├── qt-ai-dev-tools/          # agent's workspace (gitignored or committed)
│   ├── Vagrantfile           # generated from template, possibly customized
│   ├── provision.sh          # generated from template
│   ├── .vagrant-ssh-config   # auto-generated
│   ├── .vagrant/             # Vagrant state
│   ├── notes/                # agent's notes, screenshots, findings
│   └── config.toml           # overrides (RAM, CPUs, provider, extra packages)
```

Decide: Jinja2 templates vs simple parametric config vs both. Document the design.

### 3.2 — [implement] Move infra files out of project root

Move `Vagrantfile`, `provision.sh`, `scripts/vm-run.sh`, `scripts/screenshot.sh` into a subsystem location within the package (e.g., `src/qt_ai_dev_tools/vagrant/templates/` or similar). Keep them as Jinja2 templates with parametric overrides.

Template parameters:
- VM provider (libvirt, virtualbox)
- RAM, CPUs
- Base box
- Extra apt packages
- Shared folder path
- Display resolution

### 3.3 — [implement] Workspace init command

```bash
qt-ai-dev-tools workspace init [--path ./qt-ai-dev-tools]
```

Generates a workspace directory with Vagrantfile, provision.sh, and config from templates. Agent can then customize `config.toml` and regenerate, or edit generated files directly.

### 3.4 — [implement] Workspace-aware VM commands

Update `vm up`, `vm status`, `vm ssh`, etc. to work from a workspace directory:

```bash
cd my-qt-app/
qt-ai-dev-tools vm up --workspace ./qt-ai-dev-tools
qt-ai-dev-tools vm status --workspace ./qt-ai-dev-tools
```

Or auto-detect workspace by walking up the directory tree.

### 3.5 — [implement] Makefile replacement

Replace the root `Makefile` with equivalent CLI commands. The Makefile is a development convenience for this repo — in agent usage, `qt-ai-dev-tools vm *` and `qt-ai-dev-tools workspace *` commands replace it.

For this repo's own development, keep a minimal Makefile that delegates to `qt-ai-dev-tools` CLI commands.

### 3.6 — [test] Workspace lifecycle test

Automated test: `workspace init → vm up → run app → interact → screenshot → vm destroy`. Verify the full cycle works from a fresh workspace.

### 3.7 — [doc] Workspace guide

Document the workspace layout, config options, and how agents should use it in real projects.

---

## Phase 4: VM environment improvements

**Status:** Done. Transparent VM proxy eliminates `vm run "qt-ai-dev-tools ..."` double-wrapping — UI commands auto-detect host vs VM via `QT_AI_DEV_TOOLS_VM=1` env var. Redundant `vm-run.sh` and `screenshot.sh` templates removed.
**Goal:** Make the Vagrant VM workflow robust and ergonomic. This is the primary environment — invest in it.

### 4.1 — [implement] VM management CLI

**Status:** Done (implemented in Phase 3). `qt-ai-dev-tools vm up/status/ssh/destroy/sync/run` commands exist. Snapshot save/restore still TODO.

### 4.2 — [implement] Auto-sync

**Status:** Done. `vm sync-auto` command wraps `vagrant rsync-auto` in background.

Background rsync or virtiofs so code changes are immediately available in VM without manual `vagrant rsync`.

### 4.3 — [implement] Portable Vagrantfile

**Status:** Done. Vagrantfile.j2 now defines both libvirt and VirtualBox provider blocks.

Make the Vagrantfile work with multiple providers (libvirt, VirtualBox) for wider compatibility. Extract the vagrant-libvirt DHCP workaround into a documented setup step.

### 4.4 — [implement] Static IP assignment for Vagrant VM

**Status:** Done. `static_ip` field in WorkspaceConfig, `--static-ip` CLI option, conditional private_network in Vagrantfile.

Option to hardcode/pin a static IP for the Vagrant VM instead of relying on DHCP. DHCP can timeout or assign unexpected addresses (known issue with libvirt). The workspace config should support a `static_ip` field, and the generated Vagrantfile should use it when set.

### 4.5 — [test] VM lifecycle tests

**Note:** VM lifecycle tests require a running VM. Tracked but not automated on host.

Automated test: `up → provision → run app → interact → screenshot → destroy`. Verify the full cycle works reliably.

### 4.6 — [doc] VM setup guide

**Status:** Done. Content folded into `skills/qt-dev-tools-setup/SKILL.md` and `CLAUDE.md`.

Document setup for each supported provider. Known issues and workarounds.

---

## Phase 5: Agent integration

**Status:** Done.
**Goal:** Make the agent workflow smooth — minimal commands, maximum feedback. Skills are the highest-value deliverable here: an agent with the right skill can use even a crude CLI effectively.

### 5.1 — [implement] AI skills

**Status:** Done. Two skills created in `skills/`: `qt-dev-tools-setup`, `qt-app-interaction`.

Create agent skills that teach the full qt-ai-dev-tools workflow. These are the primary integration point — skills turn a generic agent into one that knows how to drive Qt apps.

Skills to build:

- **`install-qt-ai-dev-tools`** — instructs the agent how to autonomously set up the toolkit in a project (run `uvx qt-ai-dev-tools init`, verify VM, start app). No manual user steps needed — the agent reads the skill and does everything.
- **Inspect→interact→verify loop** — the core workflow skill. Teaches agents to: get the widget tree, identify targets, interact, take a screenshot to confirm, recover from errors.
- **Widget identification patterns** — how to find the right widget by role, name, index. Strategies for ambiguous names, dynamic content, unnamed widgets.
- **Error recovery** — what to do when a click misses, when the app doesn't respond, when AT-SPI returns stale data. Retry strategies, screenshot-based verification.
- **Environment setup** — VM lifecycle, display configuration, AT-SPI prerequisites. What agents need to check before interacting.
- **Common recipes** — fill a form, navigate a menu, handle a dialog, select from a dropdown, read a table.

Distributable as superpowers-style skills (`npx -y skills add ...` or bundled with the toolkit copy).

```
skills/
  qt-dev-tools-setup/SKILL.md     # Autonomous setup
  qt-app-interaction/SKILL.md     # Core workflow + recipes
```

### 5.2 — [implement] Compound commands

**Status:** Done. `fill` and `do` compound commands added to CLI and QtPilot.

Based on real agent usage, add high-level commands that combine common sequences:

```bash
# Click and verify (click + screenshot + state check)
qt-ai-dev-tools do click "Save" --verify "status contains 'Saved'"

# Fill form field (focus + clear + type)
qt-ai-dev-tools fill --role "text" --name "email" --value "test@example.com"

# Interactive sequence from file
qt-ai-dev-tools run script.yaml
```

Only add what real usage proves valuable. Don't pre-design.

### 5.3 — [explore] Optimal agent workflow

**Status:** Done. Content folded into `skills/qt-app-interaction/SKILL.md` and `CLAUDE.md`.

Use qt-ai-dev-tools myself (the agent) on real projects. Document:
- What sequences of commands are most common?
- Where do I get stuck or need multiple attempts?
- What information do I wish I had after each action?

### 5.4 — [test] End-to-end agent test

**Note:** To be validated through real-world usage.

Have an agent (me) complete a real task using only qt-ai-dev-tools:
- Launch an app
- Navigate UI to accomplish a goal
- Verify the result
- Document friction points

### 5.5 — [test] Iterative skill & tool improvement through practice

**Note:** To be validated through real-world usage.

Run skills and tools through multiple real-world test cases and use case scenarios. After each test:
- Identify friction, gaps, and errors in skills and tools
- Fix tools and update skills based on findings
- Re-run the scenario to verify improvement

This is an iterative loop, not a one-shot test. Skills and tools should be noticeably better after each round. Minimum 3-5 diverse scenarios (e.g., form filling, menu navigation, dialog handling, table interaction, multi-window workflow).

### 5.6 — [doc] Agent workflow documentation

**Status:** Done. Content folded into `skills/qt-app-interaction/SKILL.md` and `CLAUDE.md`.

Based on real usage, document the recommended workflow and common patterns.

---

## Phase 6: Advanced capabilities

**Status:** Done. Bridge eval (6.0) complete. Five Linux subsystem modules (6.3) implemented with CLI, unit tests, and e2e tests (6.4). Complex widgets (6.1-6.2), visual diffing (6.5), state snapshots (6.6), and complex app testing (6.7) deferred to backlog.
**Goal:** Beyond basic inspect/interact — handle complex Qt patterns and Linux subsystems. **Use-case driven:** agree with user on 3-5 most popular/valuable use cases, implement those first. Additional use cases go to the backlog for future work.

**Design references:**
- Design: `docs/superpowers/specs/2026-04-05-linux-subsystems-design.md`
- Plan: `docs/superpowers/plans/2026-04-05-phases-6-6.5-7.md`

### 6.0 — Bridge: Runtime Code Execution

Chrome DevTools `evaluate_script` equivalent for Qt apps. Lets AI agents execute arbitrary Python code inside a running Qt/PySide app via a Unix socket bridge. Two start methods:
1. **App-installed:** `from qt_ai_dev_tools.bridge import start; start()` (any Python)
2. **Auto-injected:** `sys.remote_exec()` (Python 3.14+, preferred when available)

#### 6.0a — [explore] Bridge eval design

**Status:** Done. Design exploration in `docs/superpowers/specs/2026-04-05-bridge-eval-design.md`. Researched embedded REPL server, sys.remote_exec (PEP 768), Chrome DevTools evaluate_script equivalents. Decided on Unix socket bridge with two start methods.

#### 6.0b — [implement] Bridge server module

**Status:** Done.

`src/qt_ai_dev_tools/bridge/` package. Unix socket server on daemon thread, Signal + `BlockingQueuedConnection` dispatch to Qt main thread, eval/exec engine with stdout capture and 64KB truncation. Pre-populated namespace (app, widgets dict, find/findall helpers, 30 PySide6 classes). JSON-over-socket protocol. Dev-mode gated via `QT_AI_DEV_TOOLS_BRIDGE` env var.

#### 6.0c — [implement] CLI eval command

**Status:** Done.

`qt-ai-dev-tools eval <code>`, `eval --file <path>`, `eval --file -` (stdin). Auto-detects bridge socket. Auto-injects via `sys.remote_exec` on 3.14+ if no bridge found. Fail-fast with setup instructions for <3.14.

#### 6.0d — [implement] CLI bridge subcommand

**Status:** Done.

`qt-ai-dev-tools bridge status` (detect running bridge), `bridge inject` (manual `sys.remote_exec` injection).

#### 6.0e — [implement] sys.remote_exec bootstrap

**Status:** Done.

Write temp bootstrap script, inject via `sys.remote_exec(pid, path)`. Handles path setup and starts bridge server inside target process.

#### 6.0f — [test] Bridge integration tests

**Status:** Done.

37 unit tests (protocol, eval engine, client with real socket mocks). 14 e2e tests inside VM against real PySide6 app (eval, widget access, button clicks, exec stdout, errors, CLI commands). 4 host-side proxy tests verifying transparent VM proxy for eval and bridge status. `make test-e2e` runs VM-side suite.

#### 6.0g — [doc] Bridge guide

**Status:** Done.

Content folded into `CLAUDE.md` and skills. Covers setup, usage, examples, security notes, troubleshooting. Skills updated with eval-based recipes.

### 6.1 — [explore] Complex widget support

Research interaction patterns for:
- **QComboBox** (dropdowns) — AT-SPI menu navigation
- **QTableWidget/QTreeWidget** — cell selection, scrolling
- **QTabWidget** — tab switching
- **QMenu/QMenuBar** — menu traversal
- **QDialog** — modal dialog handling
- **QScrollArea** — scroll to reveal widgets

### 6.2 — [implement] Widget-specific helpers

Add helpers as needed based on 6.1 findings. Only for widgets where the basic click/type isn't enough.

### 6.3 — [implement] Linux subsystem modules

Five subsystem modules in `src/qt_ai_dev_tools/subsystems/` wrapping system CLI tools (xclip, pw-cat, sox, busctl, etc.) via typed Python APIs. CLI commands added as typer subcommand groups. Architecture: `@dataclass(slots=True)` for types, `_proxy_to_vm()` for transparent VM proxying.

#### 6.3a — [implement] VM provision updates

**Status:** Done. Added sox, ffmpeg, xclip, xsel, dunst, stalonetray, pipewire packages to provision template. Dunst, stalonetray, and PipeWire autostart configured.

#### 6.3b — [implement] Subsystems package scaffold + shared types + subprocess helper

**Status:** Done. Created `subsystems/` package with `models.py` (12 dataclass types) and `_subprocess.py` (check_tool, run_tool).

#### 6.3c — [implement] Clipboard module + CLI + unit tests

**Status:** Done. `subsystems/clipboard.py` with xsel (preferred) / xclip fallback. CLI: `clipboard write`, `clipboard read`.

#### 6.3d — [implement] File dialog module + CLI + test app + unit tests

**Status:** Done. `subsystems/file_dialog.py` with AT-SPI automation. CLI: `file-dialog detect/fill/accept/cancel`.

#### 6.3e — [implement] System tray module + CLI + test app + unit tests

**Status:** Done. `subsystems/tray.py` with D-Bus SNI interaction. CLI: `tray list/click/menu/select`.

#### 6.3f — [implement] Notifications module + CLI + unit tests

**Status:** Done. `subsystems/notify.py` with D-Bus notification monitoring. CLI: `notify listen/dismiss/action`.

#### 6.3g — [implement] Audio module (PipeWire virtual mic, record, verify) + CLI + test app + unit tests

**Status:** Done. `subsystems/audio.py` with PipeWire virtual mic, recording, and sox verification. CLI: `audio virtual-mic start/stop/play`, `audio record/sources/status/verify`.

### 6.4 — [test] Subsystem e2e tests

E2E tests run in the VM against real PySide6 test apps. Follow test flows from design spec.

#### 6.4a — [test] E2E fixtures for subsystem test apps

**Status:** Done. Module-scoped fixtures in `tests/e2e/conftest.py` start test apps, wait for AT-SPI, kill on teardown.

#### 6.4b — [test] Clipboard e2e tests (flows 2A, 2B)

**Status:** Done. Write+paste and copy+read round-trip tests pass. Flow 2C (cross-app) deferred.

#### 6.4c — [test] File dialog e2e tests (flows 1A, 1B, 1C)

**Status:** Done. Open, save, and cancel dialog tests pass using AT-SPI (not bridge, since modal dialogs block bridge).

#### 6.4d — [test] Tray e2e tests (flows 3A, 3B, 3C, 3D)

**Status:** Skipped — openbox+stalonetray provides XEmbed only, not SNI D-Bus. Tests skip gracefully when StatusNotifierWatcher is unavailable. Requires KDE/GNOME or snixembed for full SNI support.

#### 6.4e — [test] Audio e2e tests (flows 4A, 4B)

**Status:** Done. Virtual mic lifecycle, record+verify silence, tone verification, source listing all pass.

#### 6.4f — [test] STT integration test app + e2e test (flow 4C)

**Status:** Done. Fake STT app (`tests/apps/stt_app.py`) with hardcoded transcription. Three e2e tests pass.

### 6.5 — [implement] Visual diffing

```bash
qt-ai-dev-tools screenshot --diff /tmp/before.png  # highlight pixel changes
qt-ai-dev-tools screenshot --compare /tmp/expected.png --threshold 5%
```

### 6.6 — [implement] State snapshots

```bash
qt-ai-dev-tools snapshot save clean           # save full widget state
qt-ai-dev-tools snapshot diff clean           # show what changed since snapshot
qt-ai-dev-tools snapshot restore clean        # VM snapshot restore
```

### 6.7 — [test] Complex app testing

Test against a non-trivial Qt app (multi-window, tabs, dialogs, menus). Verify all helpers work.

---

## Phase 6.5: Project hygiene

**Status:** Done.
**Goal:** Address findings from the [2026-04-05 project config audit](reviews/2026-04-05-project-config-audit.md). Fix tooling gaps, apply test markers, add missing tests, update docs.

### 6.5.1 — [implement] Setup script and make target

**Status:** Done. `scripts/setup.sh` created, `make setup` target added.

### 6.5.2 — [implement] Pre-commit standard hooks

**Status:** Done. Added trailing-whitespace, end-of-file-fixer, check-yaml hooks.

### 6.5.3 — [implement] Lint scope and minor fixes

**Status:** Done. Lint targets updated, `py.typed` marker added, `_bootstrap.py` type ignore fixed.

### 6.5.4 — [implement] Apply pytest markers

**Status:** Done. Unit, integration, and e2e markers applied to all test files.

### 6.5.5 — [doc] Update CLAUDE.md type-ignore policy

**Status:** Done. Bridge modules documented as second type-ignore boundary.

### 6.5.6 — [test] High-priority test coverage

**Status:** Done. `test_bootstrap.py` and `test_pilot.py` unit tests added.

### 6.5.7 — [test] Medium-priority test coverage

**Status:** Done. `test_bridge_server.py` socket protocol tests added.

### 6.5.8 — [test] Low-priority test coverage

**Status:** Done. `test_qt_namespace.py` and `test_interact.py` tests added.

---

## Phase 7: Distribution

**Goal:** Make it easy to adopt in any project. Primary model is shadcn-like local copy — agent owns the code.

The primary distribution is a self-contained toolkit directory copied into the target project:

```
my-qt-app/
├── src/                          # the actual Qt app
├── qt-ai-dev-tools/              # self-contained toolkit (gitignored or committed)
│   ├── cli                       # shebang script: #!/usr/bin/env -S uv run --script
│   ├── src/                      # full package source, readable/editable by agent
│   │   └── qt_ai_dev_tools/
│   ├── templates/                # Vagrant/provision templates
│   ├── skills/                   # agent skills co-located
│   ├── pyproject.toml            # deps (uv resolves them)
│   ├── config.toml               # workspace config overrides
│   ├── notes/                    # agent's scratch space
│   └── Vagrantfile               # generated from templates, customizable
```

Key properties:
- **Primary installer: `uvx qt-ai-dev-tools init ./qt-ai-dev-tools`** — single command, only requires `uv`
- Agent owns the code — can read, modify, extend, fix bugs, add helpers
- Self-contained — no global install, no venv conflicts
- `uv run` handles dependency resolution via shebang or pyproject.toml
- Skills + config + notes + source all co-located
- Version-controllable per-project (or gitignored)
- **Secondary: `pip install qt-ai-dev-tools`** for users who want system-wide CLI or library usage
- Update story: re-run `uvx qt-ai-dev-tools init` to update, or `qt-ai-dev-tools self-update` from within the toolkit

### 7.1 — [implement] pip package (PyPI metadata + version module + build test)

**Status:** Done. PyPI metadata in `pyproject.toml`, `__version__.py` created, build tested.

### 7.2 — [implement] shadcn-style installer (`uvx qt-ai-dev-tools init`)

**Status:** Done. `installer.py` copies source, templates, skills, config. `init` CLI command added.

### 7.3 — [implement] Self-contained cli shebang script (`uv run --script`)

**Status:** Done. Generated by installer with `#!/usr/bin/env -S uv run --script` shebang.

### 7.4 — [implement] Self-update mechanism

**Status:** Done. `qt-ai-dev-tools self-update` re-runs init, preserves customizations.

### 7.5 — [implement] Skills in `skills/` directory

**Status:** Done. Skills bundled in `skills/` and copied by installer.

### 7.6 — [doc] Documentation updates (subsystems guide, CLAUDE.md, README.md, ROADMAP.md)

**Status:** Done. `docs/subsystems-guide.md` written. CLAUDE.md, README.md, ROADMAP.md updated.

### 7.7 — [test] Manual testing in isolated environments

**Status:** Done. Manual testing completed against running VM. Results: 27 e2e pass, 8 skip (tray SNI + host-only proxy), 1 xfail (Qt notification backend). Fixes applied: clipboard xsel preference, bridge PID for multi-app tests, AT-SPI for modal dialogs, sox stat parsing. Known limitations documented in CLAUDE.md. Published as v0.2.0 on PyPI.

---

## Phase 8: Container & host support

**Goal:** Lighter-weight alternative to VM for UI-only workflows. VM remains primary for full system integration.

### 8.1 — [explore] Container feasibility

Research and test:
- **Podman/Docker** with Xvfb + AT-SPI (rootless, no VM overhead)
- **Distrobox** (immutable OS friendly — Fedora Silverblue etc.)
- What works: UI inspection, interaction, screenshots
- What doesn't: D-Bus system bus, PulseAudio/PipeWire, system tray (these need VM)

### 8.2 — [implement] Container environment

Docker/Podman image for the 80% UI-only use case:

```bash
qt-ai-dev-tools env up --mode container     # lightweight, UI features only
qt-ai-dev-tools env up --mode vm            # full features, system integration
```

### 8.3 — [explore] Direct host support

Research running directly on the host with Xvfb (no isolation). Simplest option for CI/CD or when the agent already runs on the target machine.

### 8.4 — [implement] Environment abstraction

Unified interface regardless of backend:

```bash
qt-ai-dev-tools tree    # works the same in VM, container, or host
```

The tool detects or is configured for its environment. Commands don't change.

### 8.5 — [doc] Environment comparison guide

When to use which environment:
- **VM (Vagrant):** Full features. D-Bus, audio, system tray, file dialogs. Best for development and testing apps with system integration.
- **Container (Docker/Podman):** UI interaction only. Fast startup, low resources. Best for CI/CD and simple UI testing.
- **Host (Xvfb):** No isolation. Simplest setup. Best when the agent already runs on the target machine.

### 8.6 — [test] Cross-environment tests

Same test suite runs in: Vagrant VM, container, direct host. Verify UI features work identically. Document which advanced features (D-Bus, audio) are VM-only.

---

## Phase 9: Alternative VM backends

**Goal:** Explore lighter/faster VM options beyond Vagrant for better performance and broader host compatibility.

**Blocker:** These tools (QEMU microVMs, Lima, cloud-hypervisor, crosvm, Incus/LXD) must be installed and carefully tested before any integration work. They may have incompatibilities with the current AT-SPI + Xvfb + openbox stack, provider-specific networking issues, or missing features. **Initial setup must be pair-programmed with the user** — not autonomous.

### 9.1 — [explore] Evaluate alternative VM tools

Research and test (with user):
- **QEMU microVMs** (firecracker-style, faster boot)
- **cloud-hypervisor** / **crosvm**
- **Lima** (Linux VMs on macOS — extends reach beyond Linux hosts)
- **Incus/LXD** (system containers — middle ground between VM and Docker)

For each: install, test AT-SPI + Xvfb + openbox stack, verify widget interaction works, document issues. Output: findings doc with trade-offs and compatibility matrix.

### 9.2 — [implement] Integration for viable backends

Based on 9.1 findings, add support for backends that passed testing. Extend `qt-ai-dev-tools vm up --backend <name>` or similar.

### 9.3 — [test] Cross-backend compatibility tests

Same test suite runs across Vagrant and any new backends. Verify feature parity or document gaps.

---

## Use case backlog

Future use cases identified during Phase 6 work. Not scheduled — pulled into phases as needed.

_(To be populated during Phase 6 based on real-world usage patterns.)_

---

## Code quality backlog (from Phase 2-3 analysis)

Findings from automated code review against project skill standards. Not blocking — tracked here for future phases.

### CQ-1 — [implement] Replace `print()` with `colorlog` logging

**Status:** Done. Replaced print() with logging in screenshot.py, removed print from pilot.py dump_tree() (CLI layer now handles output).

`screenshot.py` and `pilot.py` use `print()` for output. `colorlog` is already a dependency but unused. Add proper logging.

### CQ-2 — [implement] Add pytest markers and improve test structure

**Status:** Partial. Pytest markers defined. Marker application tracked in Phase 6.5.4. Test structure split remains for future work.

- Define `unit` and `integration` markers in `pyproject.toml`
- Split `test_main.py` into unit (pytest-qt) and integration (AT-SPI/scrot) files
- Remove `sys.path` hack in `test_main.py` — make `app/` importable or use subprocess
- Add type annotations to all test functions

### CQ-3 — [implement] Replace tautological mock tests with meaningful tests

`test_atspi.py` mostly tests that mocks return what they were told to return. `test_vm.py` asserts exact subprocess call lists (implementation detail). Either:
- Delete thin-wrapper tests, rely on integration tests
- Replace subprocess mocks with mock-binary approach (tiny script on PATH)
- Keep only tests that verify real logic (error paths, action lookup)

### CQ-4 — [explore] Evaluate Result-based error handling

`writing-python-code` skill mandates `rusty-results` for expected failures. Currently the project uses Python exceptions everywhere. Evaluate whether adopting `Result[T, E]` is worth the API change for a CLI tool where exceptions are natural. Document decision.

### CQ-5 — [implement] Add integration tests for core library modules

**Status:** Superseded by Phase 6.5.6/6.5.7/6.5.8 with detailed test plans (21 tests across 5 files).

`pilot.py`, `interact.py`, `state.py`, `screenshot.py` have no dedicated tests. Only indirect coverage via `test_cli.py` (help-only on host) and `test_main.py` (AT-SPI smoke). Add VM-based integration tests.

### CQ-6 — [implement] Fix `vm_run` fallback hardcoded display

**Status:** Done. vm_run() accepts display parameter instead of hardcoding.

`vm.py` `vm_run()` fallback path hardcodes `DISPLAY=:99`. Should read from workspace config or accept as parameter.

---

## Task type legend

| Tag | Meaning |
|-----|---------|
| **explore** | Research options, constraints, trade-offs. Output: findings doc. |
| **prototype** | Build quick throwaway to validate an idea. May be discarded. |
| **implement** | Add to the real codebase. Tested, documented. |
| **test** | Verify a feature works. May be automated or manual. |
| **doc** | Persist knowledge: usage, caveats, patterns. |

## How this roadmap evolves

This is not a waterfall plan. Phases overlap. Tasks get added, removed, or reordered based on:
- What the agent (primary user) actually needs when using the tool
- What breaks or is painful in practice
- What the environment constraints turn out to be

After completing any task, update this roadmap with findings and adjust priorities.
