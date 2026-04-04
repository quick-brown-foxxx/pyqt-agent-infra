# Skills Rewrite Design

Rewrite user-facing docs and skills from wiki-style reference into use-case-driven skills following the Anthropic skills guide.

## Context

Current skills (`install-qt-ai-dev-tools`, `qt-inspect-interact-verify`, `qt-widget-patterns`) and docs (`agent-workflow.md`, `vm-setup-guide.md`) are organized by concept, not by use case. They read like reference documentation — broad, overlapping, and not workflow-driven. The Anthropic skills guide says: start with use cases, use progressive disclosure, include trigger phrases, keep SKILL.md focused.

**Primary user:** AI agent with qt-ai-dev-tools already installed, interacting with a Qt app.
**Secondary user:** AI agent setting up qt-ai-dev-tools from scratch.

## New Skill Structure

```
skills/
├── qt-dev-tools-setup/
│   ├── SKILL.md                    # Sequential setup workflow
│   └── references/
│       └── vm-troubleshooting.md   # DHCP bugs, provider issues, service diagnostics
│
├── qt-app-interaction/
│   ├── SKILL.md                    # Core inspect→interact→verify loop
│   └── references/
│       ├── widget-roles.md         # AT-SPI role ↔ Qt widget mapping table
│       ├── recipes.md              # Form filling, menu nav, dialog handling, combo boxes
│       └── troubleshooting.md      # Widget not found, stale data, focus issues, timing
```

## Files to Delete

- `docs/agent-workflow.md` — absorbed into `qt-app-interaction`
- `docs/vm-setup-guide.md` — absorbed into `qt-dev-tools-setup`
- `skills/install-qt-ai-dev-tools/` — replaced by `qt-dev-tools-setup`
- `skills/qt-inspect-interact-verify/` — replaced by `qt-app-interaction`
- `skills/qt-widget-patterns/` — split into `references/widget-roles.md` and `references/recipes.md`

## Files to Keep (untouched)

- `docs/PHILOSOPHY.md` — developer-facing
- `docs/ROADMAP.md` — developer-facing
- `docs/superpowers/` — developer-facing (plans, specs)

## Skill 1: qt-dev-tools-setup

### Frontmatter

```yaml
---
name: qt-dev-tools-setup
description: >
  Set up qt-ai-dev-tools for AI-driven Qt/PySide app interaction.
  Use when asked to "set up qt-ai-dev-tools", "initialize workspace",
  "configure VM for Qt testing", or when starting a new project that
  needs headless Qt UI testing. Covers installation, workspace init,
  VM boot, and environment verification.
---
```

### SKILL.md content

Sequential workflow — each step has: command, expected output, failure action.

1. **Install the toolkit.** Copy `src/` + `pyproject.toml` from GitHub into `qt-ai-dev-tools/` subdirectory of the target project via curl. Bootstrap a CLI script that runs via `uv run`.
2. **Initialize workspace.** `qt-ai-dev-tools workspace init --path .` — generates Vagrantfile and provision.sh from templates. Mention customization options (memory, cpus, provider, static-ip) but don't over-explain.
3. **Start the VM.** `qt-ai-dev-tools vm up` — first boot ~10 min, subsequent ~30s.
4. **Verify environment.** `vm status` (services running), `apps` (AT-SPI bus accessible), `screenshot` (Xvfb display working). Each with expected output and what failure means.
5. **Launch target app.** `vm sync` + `vm run "python3 /vagrant/app.py &"` + `wait --app`. Explain that `vm run` is for arbitrary commands, but qt-ai-dev-tools commands auto-proxy.
6. **Confirm interaction.** `tree` shows widget tree, `screenshot` shows the app. If both work, setup is complete.

Failure paths say "consult `references/vm-troubleshooting.md`" instead of inlining the full troubleshooting.

### references/vm-troubleshooting.md

Consolidated troubleshooting from current install skill + vm-setup-guide.md:

- DHCP timeout / VM won't get IP (libvirt DHCP bug + fix)
- PySide6 import errors (missing system libs)
- AT-SPI not seeing the app (Xvfb, D-Bus, DISPLAY)
- App crashes silently (debug in foreground)
- Screenshots blank (Xvfb/openbox not running)
- xdotool wrong coordinates (openbox missing)
- Slow file sync (manual rsync, rsync-auto)
- VM won't start (provider not installed, QEMU/KVM check)

### Size

- SKILL.md: ~160 lines (down from 278)
- references/vm-troubleshooting.md: ~80 lines

## Skill 2: qt-app-interaction

### Frontmatter

```yaml
---
name: qt-app-interaction
description: >
  Interact with Qt/PySide apps via AT-SPI accessibility. Use when asked
  to "test the UI", "click a button", "fill a form", "inspect widgets",
  "take a screenshot", "read widget state", or any task requiring
  programmatic Qt app interaction. Covers the full
  inspect-interact-verify workflow loop.
---
```

### SKILL.md content

Workflow-driven, not reference-driven. Three sections.

**Section 1: The Loop**

The core pattern — every UI interaction follows three phases:

1. **Inspect** — understand current state before acting. Commands: `tree` (full tree), `find --role --name` (specific widget), `state` (detailed info), `text` (text content), `screenshot` (visual), `apps` (running apps), `wait` (wait for app).
2. **Interact** — perform the action. Commands: `click --role --name`, `type "text"`, `key Return`, `focus --role --name`, `fill --role --name --value` (focus+clear+type).
3. **Verify** — confirm the action worked. Re-inspect tree, read target widget state, take screenshot.

Include compact "when to use which command" decision table for each phase.

Note: all UI commands auto-detect host vs VM and proxy transparently. No `vm run` wrapping. Use `vm run` only for arbitrary non-qt-ai-dev-tools commands.

**Section 2: Focus & Input Rules**

Critical gotchas that must be in the main file (not references):

- Always focus or click a text field before typing — `type` sends to whatever has focus
- `fill` is preferred over manual focus+clear+type
- AT-SPI `editable_text.insert_text()` does NOT work with Qt — always xdotool
- Click focuses the widget — can type immediately after clicking a text field
- Tab navigates between fields

**Section 3: Error Recovery Essentials**

Top 3 problems inline (full troubleshooting in references):

- **Widget not found** → re-inspect tree, check name/role, check for dialog blocking
- **Click had no effect** → screenshot, check for modal dialog, check if disabled
- **Text went to wrong widget** → use `fill` instead, or explicitly click target first

Point to `references/troubleshooting.md` for the full list.

### references/widget-roles.md

The AT-SPI role ↔ Qt widget mapping table. Kept as-is from current `qt-widget-patterns` — it's a genuine lookup table that agents need when encountering unfamiliar roles. ~25 rows.

### references/recipes.md

Concrete command sequences for common tasks. Each recipe: goal, commands, verification step.

- **Fill a form** — find text fields, fill each, submit, verify
- **Navigate a menu** — click menu, re-inspect for items, click item, handle result
- **Handle a dialog** — detect dialog in tree, find buttons, click OK/Cancel, verify dismissed
- **Select from combo box** — click to open, re-inspect for menu items, click option (or keyboard nav)
- **Switch tabs** — find page tabs, click target tab, re-inspect for new content
- **Interact with a list** — find list items, click to select, verify selection
- **Scroll to reveal widgets** — click inside scroll area, Page_Down/Up, re-inspect

### references/troubleshooting.md

Full error recovery patterns. Consolidated from current skills + docs:

- Widget not found (re-inspect, name changed, dialog blocking)
- Multiple widgets found (more specific name, Python API index)
- Click had no effect (disabled, overlapping, scroll area, wrong match)
- Text input lost/wrong widget (focus management, modal stealing focus)
- AT-SPI stale data (delay, re-read, timing)
- Unnamed widgets (tree position, coordinates, Python API)
- Dynamic content (partial name match, re-find after changes)
- Timing issues (sleep, wait, polling loop)
- App crashed/unresponsive (check apps, screenshot, relaunch)
- Empty tree (app not started, Xvfb/openbox/AT-SPI not running)

### Size

- SKILL.md: ~150 lines (down from 982 combined across 3 files)
- references/widget-roles.md: ~50 lines
- references/recipes.md: ~120 lines
- references/troubleshooting.md: ~100 lines

## Size comparison

| File | Current lines | Target lines |
|------|--------------|-------------|
| qt-dev-tools-setup/SKILL.md | 278 | ~160 |
| qt-dev-tools-setup/references/vm-troubleshooting.md | — | ~80 |
| qt-app-interaction/SKILL.md | 982 combined | ~150 |
| qt-app-interaction/references/widget-roles.md | — | ~50 |
| qt-app-interaction/references/recipes.md | — | ~120 |
| qt-app-interaction/references/troubleshooting.md | — | ~100 |
| **Total** | ~1260 | ~660 |

Nearly half the content, zero duplication, progressive loading.

## CLAUDE.md and README.md Updates

After the skills rewrite, update the skills references in CLAUDE.md and README.md to point to the new skill names (`qt-dev-tools-setup`, `qt-app-interaction`) instead of the old ones.
