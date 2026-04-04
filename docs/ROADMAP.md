# qt-ai-dev-tools roadmap

**Goal:** Give AI agents first-class access to Qt/PySide apps — inspect widgets, interact, take screenshots, read state — with the same ease as Chrome DevTools MCP but with typed widget access via AT-SPI.

**Primary user:** AI coding agents (Claude Code, etc.) working on PySide/PyQt projects.

## Design principles

1. **Composable over monolithic.** 80% of use cases should be one-liners (`qt-ai-dev-tools tree`, `qt-ai-dev-tools click "Save"`). The remaining 20% use the Python library directly. No "super-tool" that tries to do everything.
2. **Agent-scriptable.** The agent can write small Python scripts using `qt_ai_dev_tools` as a library when the CLI isn't enough. Primitives are always exposed.
3. **Drop-in portable.** Works in any PySide6/PyQt6 project. No project-specific config required. Copy the folder, run the commands.
4. **VM-first.** Vagrant VM is the primary environment — it gives full OS isolation and access to Linux subsystems (D-Bus, audio, system tray). Container/host support comes later as a lighter-weight option for UI-only workflows.
5. **Feedback-rich.** Every action returns enough context for the agent to know what happened — widget state after click, screenshot after interaction, error messages with available alternatives.

## Naming note

The name `qt-pilot` is taken by [neatobandit0/qt-pilot](https://github.com/neatobandit0/qt-pilot) — a similar project but with a fundamentally different approach (in-process Qt test harness requiring `setObjectName()` on widgets). Our tool uses AT-SPI externally, works with any Qt app without modification, and can access Linux subsystems beyond the app. Hence the distinct name `qt-ai-dev-tools`.

## Delivery shape

The final product is a **composable toolkit**, not a single binary:

| Layer | What | How agents use it |
|-------|------|-------------------|
| **Python library** (`qt_ai_dev_tools`) | AT-SPI + xdotool primitives | `from qt_ai_dev_tools import QtPilot` in custom scripts |
| **CLI** (`qt-ai-dev-tools`) | One-liner commands | `qt-ai-dev-tools tree`, `qt-ai-dev-tools click "Save"`, `qt-ai-dev-tools screenshot` |
| **AI skills** | Workflow guidance | Teach agents the inspect→interact→verify loop |
| **MCP server** (later) | Structured tool interface | Native tool calls from Claude Code / other agents |
| **VM environment** | Vagrant + Xvfb + AT-SPI setup | Scripts that create and manage the headless Qt environment |

Distribution: pip-installable package + optional AI skills drop-in. Think `pip install qt-ai-dev-tools` for the tool, copy `.agents/skills/qt-ai-dev-tools/` for the agent knowledge.

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

**Goal:** Make the Vagrant VM workflow robust and ergonomic. This is the primary environment — invest in it.

### 4.1 — [implement] VM management CLI

Wrap Vagrant commands into the tool itself:

```bash
qt-ai-dev-tools vm up          # vagrant up + verify services
qt-ai-dev-tools vm status      # Xvfb, openbox, AT-SPI health
qt-ai-dev-tools vm ssh         # vagrant ssh with env vars
qt-ai-dev-tools vm sync        # vagrant rsync
qt-ai-dev-tools vm destroy     # vagrant destroy
qt-ai-dev-tools vm snapshot save/restore  # fast VM reset
```

### 4.2 — [implement] Auto-sync

Background rsync or virtiofs so code changes are immediately available in VM without manual `vagrant rsync`.

### 4.3 — [implement] Portable Vagrantfile

Make the Vagrantfile work with multiple providers (libvirt, VirtualBox) for wider compatibility. Extract the vagrant-libvirt DHCP workaround into a documented setup step.

### 4.4 — [explore] Alternative VM tools

Research lighter VM options for future compatibility:
- **QEMU microVMs** (firecracker-style, faster boot)
- **cloud-hypervisor** / **crosvm**
- **Lima** (Linux VMs on macOS — extends reach beyond Linux hosts)
- **Incus/LXD** (system containers — middle ground between VM and Docker)

Output: findings doc with trade-offs. No implementation yet.

### 4.5 — [test] VM lifecycle tests

Automated test: `up → provision → run app → interact → screenshot → destroy`. Verify the full cycle works reliably.

### 4.6 — [doc] VM setup guide

Document setup for each supported provider. Known issues and workarounds.

---

## Phase 5: Agent integration

**Goal:** Make the agent workflow smooth — minimal commands, maximum feedback.

### 5.1 — [explore] Optimal agent workflow

Use qt-ai-dev-tools myself (the agent) on real projects. Document:
- What sequences of commands are most common?
- Where do I get stuck or need multiple attempts?
- What information do I wish I had after each action?

### 5.2 — [implement] Compound commands

Based on 5.1, add high-level commands that combine common sequences:

```bash
# Click and verify (click + screenshot + state check)
qt-ai-dev-tools do click "Save" --verify "status contains 'Saved'"

# Fill form field (focus + clear + type)
qt-ai-dev-tools fill --role "text" --name "email" --value "test@example.com"

# Interactive sequence from file
qt-ai-dev-tools run script.yaml
```

Only add what real usage proves valuable. Don't pre-design.

### 5.3 — [implement] AI skills

Create agent skills that teach the inspect→interact→verify workflow:

```
.agents/skills/qt-ai-dev-tools/
  SKILL.md              # How to use qt-ai-dev-tools: workflow, commands, gotchas
```

### 5.4 — [prototype] MCP server

Wrap qt-ai-dev-tools CLI as an MCP server:

```json
{
  "tools": [
    {"name": "qt_tree", "description": "Get widget tree"},
    {"name": "qt_click", "description": "Click a widget by role/name"},
    {"name": "qt_type", "description": "Type text into focused widget"},
    {"name": "qt_screenshot", "description": "Take screenshot"},
    {"name": "qt_state", "description": "Read widget state"}
  ]
}
```

Simple stdio MCP server. Each tool maps 1:1 to a CLI command.

### 5.5 — [test] End-to-end agent test

Have an agent (me) complete a real task using only qt-ai-dev-tools:
- Launch an app
- Navigate UI to accomplish a goal
- Verify the result
- Document friction points

### 5.6 — [doc] Agent workflow documentation

Based on real usage, document the recommended workflow and common patterns.

---

## Phase 6: Advanced capabilities

**Goal:** Beyond basic inspect/interact — handle complex Qt patterns and Linux subsystems.

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

### 6.3 — [explore] Linux subsystem access

Research agent access to (VM gives full OS — use it):
- **D-Bus** — system/session bus interaction (notifications, media controls)
- **PulseAudio/PipeWire** — audio state (is sound playing?)
- **System tray** — tray icon interaction
- **File dialogs** — native file picker automation
- **Clipboard** — read/write clipboard content

### 6.4 — [prototype] Subsystem helpers

Add `qt-ai-dev-tools dbus`, `qt-ai-dev-tools clipboard`, etc. as proven useful.

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

## Phase 7: Polish & distribution

**Goal:** Make it easy to adopt in any project.

### 7.1 — [implement] pip package

`pip install qt-ai-dev-tools` — installs the library + CLI. System deps (xdotool, AT-SPI) documented in install guide.

### 7.2 — [implement] Drop-in skills

Publishable AI skills that any project can reference.

### 7.3 — [doc] README, examples, troubleshooting

### 7.4 — [test] Compatibility matrix

Test with: PySide6, PyQt6, PySide2, PyQt5. Document what works.

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
