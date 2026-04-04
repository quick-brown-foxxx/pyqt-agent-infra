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

## Phase 2: VM environment improvements

**Goal:** Make the Vagrant VM workflow robust and ergonomic. This is the primary environment — invest in it.

### 2.1 — [implement] VM management CLI

Wrap Vagrant commands into the tool itself:

```bash
qt-ai-dev-tools vm up          # vagrant up + verify services
qt-ai-dev-tools vm status      # Xvfb, openbox, AT-SPI health
qt-ai-dev-tools vm ssh         # vagrant ssh with env vars
qt-ai-dev-tools vm sync        # vagrant rsync
qt-ai-dev-tools vm destroy     # vagrant destroy
qt-ai-dev-tools vm snapshot save/restore  # fast VM reset
```

### 2.2 — [implement] Auto-sync

Background rsync or virtiofs so code changes are immediately available in VM without manual `vagrant rsync`.

### 2.3 — [implement] Portable Vagrantfile

Make the Vagrantfile work with multiple providers (libvirt, VirtualBox) for wider compatibility. Extract the vagrant-libvirt DHCP workaround into a documented setup step.

### 2.4 — [explore] Alternative VM tools

Research lighter VM options for future compatibility:
- **QEMU microVMs** (firecracker-style, faster boot)
- **cloud-hypervisor** / **crosvm**
- **Lima** (Linux VMs on macOS — extends reach beyond Linux hosts)
- **Incus/LXD** (system containers — middle ground between VM and Docker)

Output: findings doc with trade-offs. No implementation yet.

### 2.5 — [test] VM lifecycle tests

Automated test: `up → provision → run app → interact → screenshot → destroy`. Verify the full cycle works reliably.

### 2.6 — [doc] VM setup guide

Document setup for each supported provider. Known issues and workarounds.

---

## Phase 3: Agent integration

**Goal:** Make the agent workflow smooth — minimal commands, maximum feedback.

### 3.1 — [explore] Optimal agent workflow

Use qt-ai-dev-tools myself (the agent) on real projects. Document:
- What sequences of commands are most common?
- Where do I get stuck or need multiple attempts?
- What information do I wish I had after each action?

### 3.2 — [implement] Compound commands

Based on 3.1, add high-level commands that combine common sequences:

```bash
# Click and verify (click + screenshot + state check)
qt-ai-dev-tools do click "Save" --verify "status contains 'Saved'"

# Fill form field (focus + clear + type)
qt-ai-dev-tools fill --role "text" --name "email" --value "test@example.com"

# Interactive sequence from file
qt-ai-dev-tools run script.yaml
```

Only add what real usage proves valuable. Don't pre-design.

### 3.3 — [implement] AI skills

Create agent skills that teach the inspect→interact→verify workflow:

```
.agents/skills/qt-ai-dev-tools/
  SKILL.md              # How to use qt-ai-dev-tools: workflow, commands, gotchas
```

### 3.4 — [prototype] MCP server

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

### 3.5 — [test] End-to-end agent test

Have an agent (me) complete a real task using only qt-ai-dev-tools:
- Launch an app
- Navigate UI to accomplish a goal
- Verify the result
- Document friction points

### 3.6 — [doc] Agent workflow documentation

Based on real usage, document the recommended workflow and common patterns.

---

## Phase 4: Advanced capabilities

**Goal:** Beyond basic inspect/interact — handle complex Qt patterns and Linux subsystems.

### 4.1 — [explore] Complex widget support

Research interaction patterns for:
- **QComboBox** (dropdowns) — AT-SPI menu navigation
- **QTableWidget/QTreeWidget** — cell selection, scrolling
- **QTabWidget** — tab switching
- **QMenu/QMenuBar** — menu traversal
- **QDialog** — modal dialog handling
- **QScrollArea** — scroll to reveal widgets

### 4.2 — [implement] Widget-specific helpers

Add helpers as needed based on 4.1 findings. Only for widgets where the basic click/type isn't enough.

### 4.3 — [explore] Linux subsystem access

Research agent access to (VM gives full OS — use it):
- **D-Bus** — system/session bus interaction (notifications, media controls)
- **PulseAudio/PipeWire** — audio state (is sound playing?)
- **System tray** — tray icon interaction
- **File dialogs** — native file picker automation
- **Clipboard** — read/write clipboard content

### 4.4 — [prototype] Subsystem helpers

Add `qt-ai-dev-tools dbus`, `qt-ai-dev-tools clipboard`, etc. as proven useful.

### 4.5 — [implement] Visual diffing

```bash
qt-ai-dev-tools screenshot --diff /tmp/before.png  # highlight pixel changes
qt-ai-dev-tools screenshot --compare /tmp/expected.png --threshold 5%
```

### 4.6 — [implement] State snapshots

```bash
qt-ai-dev-tools snapshot save clean           # save full widget state
qt-ai-dev-tools snapshot diff clean           # show what changed since snapshot
qt-ai-dev-tools snapshot restore clean        # VM snapshot restore
```

### 4.7 — [test] Complex app testing

Test against a non-trivial Qt app (multi-window, tabs, dialogs, menus). Verify all helpers work.

---

## Phase 5: Polish & distribution

**Goal:** Make it easy to adopt in any project.

### 5.1 — [implement] pip package

`pip install qt-ai-dev-tools` — installs the library + CLI. System deps (xdotool, AT-SPI) documented in install guide.

### 5.2 — [implement] Drop-in skills

Publishable AI skills that any project can reference.

### 5.3 — [doc] README, examples, troubleshooting

### 5.4 — [test] Compatibility matrix

Test with: PySide6, PyQt6, PySide2, PyQt5. Document what works.

---

## Phase 6: Container & host support

**Goal:** Lighter-weight alternative to VM for UI-only workflows. VM remains primary for full system integration.

### 6.1 — [explore] Container feasibility

Research and test:
- **Podman/Docker** with Xvfb + AT-SPI (rootless, no VM overhead)
- **Distrobox** (immutable OS friendly — Fedora Silverblue etc.)
- What works: UI inspection, interaction, screenshots
- What doesn't: D-Bus system bus, PulseAudio/PipeWire, system tray (these need VM)

### 6.2 — [implement] Container environment

Docker/Podman image for the 80% UI-only use case:

```bash
qt-ai-dev-tools env up --mode container     # lightweight, UI features only
qt-ai-dev-tools env up --mode vm            # full features, system integration
```

### 6.3 — [explore] Direct host support

Research running directly on the host with Xvfb (no isolation). Simplest option for CI/CD or when the agent already runs on the target machine.

### 6.4 — [implement] Environment abstraction

Unified interface regardless of backend:

```bash
qt-ai-dev-tools tree    # works the same in VM, container, or host
```

The tool detects or is configured for its environment. Commands don't change.

### 6.5 — [doc] Environment comparison guide

When to use which environment:
- **VM (Vagrant):** Full features. D-Bus, audio, system tray, file dialogs. Best for development and testing apps with system integration.
- **Container (Docker/Podman):** UI interaction only. Fast startup, low resources. Best for CI/CD and simple UI testing.
- **Host (Xvfb):** No isolation. Simplest setup. Best when the agent already runs on the target machine.

### 6.6 — [test] Cross-environment tests

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
