# Skills Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace wiki-style reference skills with use-case-driven skills following the Anthropic skills guide.

**Architecture:** Two skills (`qt-dev-tools-setup`, `qt-app-interaction`) replace three skills and two docs. Each skill has a focused SKILL.md with progressive-disclosure `references/` files. No TDD — this is pure documentation/content work.

**Spec:** `docs/superpowers/specs/2026-04-05-skills-rewrite-design.md`

---

### Task 1: Create qt-dev-tools-setup skill

**Files:**
- Create: `skills/qt-dev-tools-setup/SKILL.md`
- Create: `skills/qt-dev-tools-setup/references/vm-troubleshooting.md`

Source material to read before writing:
- `skills/install-qt-ai-dev-tools/SKILL.md` (current install skill — rewrite, don't copy)
- `docs/vm-setup-guide.md` (merge troubleshooting into references)

- [ ] **Step 1: Create SKILL.md**

Write `skills/qt-dev-tools-setup/SKILL.md`. Content requirements:

Frontmatter:
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

Body — sequential workflow with 6 steps. Each step has: what to do, the command, expected output, what failure means. Keep it action-oriented, not explanatory.

1. **Install the toolkit.** Copy `src/` + `pyproject.toml` from the GitHub repo into a `qt-ai-dev-tools/` subdirectory of the target project. Bootstrap a CLI entry script that runs via `uv run`. Note: the package is not published to PyPI — this is the only install method.
2. **Initialize workspace.** `qt-ai-dev-tools workspace init --path .` generates Vagrantfile and provision.sh. Mention `--memory`, `--cpus`, `--provider`, `--static-ip` options in a compact list — don't over-explain each.
3. **Start the VM.** `qt-ai-dev-tools vm up`. First boot ~10 min, subsequent ~30s.
4. **Verify environment.** Three checks: `vm status` (services), `apps` (AT-SPI bus), `screenshot -o /tmp/test.png` (Xvfb). Each with expected output and one-line failure action pointing to `references/vm-troubleshooting.md`.
5. **Launch target app.** `vm sync` then `vm run "python3 /vagrant/app.py &"` then `wait --app app.py --timeout 15`. Explain: `vm run` is for arbitrary commands; qt-ai-dev-tools commands auto-proxy.
6. **Confirm interaction.** `tree` should show widget tree. `screenshot` should show the app. If both work, setup is done.

End with a one-line transition: "Setup complete. Use the `qt-app-interaction` skill for the inspect→interact→verify workflow."

File sync section (compact): `vm sync` for manual, `vm sync-auto` for automatic.

Target: ~160 lines. Do NOT include troubleshooting inline — all troubleshooting goes to references.

- [ ] **Step 2: Create references/vm-troubleshooting.md**

Write `skills/qt-dev-tools-setup/references/vm-troubleshooting.md`. Consolidate troubleshooting from current `skills/install-qt-ai-dev-tools/SKILL.md` and `docs/vm-setup-guide.md`.

Sections (each: symptom, cause, fix with commands):
- DHCP timeout / VM won't get IP (libvirt DHCP bug — include the full `virsh` network fix)
- VM won't start (provider not installed, QEMU/KVM check)
- PySide6 import error (missing libegl1, libxkbcommon0)
- AT-SPI not seeing the app (app not running, Xvfb down, D-Bus, wrong DISPLAY)
- App crashes silently (run in foreground to see errors)
- Screenshots blank (Xvfb/openbox not running, app not visible)
- xdotool wrong coordinates (openbox not running)
- Slow file sync (manual rsync, rsync-auto)

Target: ~80 lines.

- [ ] **Step 3: Commit**

```bash
git add skills/qt-dev-tools-setup/
git commit -m "feat: add qt-dev-tools-setup skill (replaces install-qt-ai-dev-tools)"
```

---

### Task 2: Create qt-app-interaction skill

**Files:**
- Create: `skills/qt-app-interaction/SKILL.md`
- Create: `skills/qt-app-interaction/references/widget-roles.md`
- Create: `skills/qt-app-interaction/references/recipes.md`
- Create: `skills/qt-app-interaction/references/troubleshooting.md`

Source material to read before writing:
- `skills/qt-inspect-interact-verify/SKILL.md` (core workflow — rewrite)
- `skills/qt-widget-patterns/SKILL.md` (widget reference — split into references/)
- `docs/agent-workflow.md` (merge workflow content)

- [ ] **Step 1: Create SKILL.md**

Write `skills/qt-app-interaction/SKILL.md`. Content requirements:

Frontmatter:
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

Body — three sections.

**Section 1: The Loop** (~80 lines)

The core pattern. Every UI interaction follows three phases:

1. **Inspect** — understand current state before acting.
   - `tree` — full widget tree (primary orientation tool). Shows role in brackets, name in quotes, position after @.
   - `tree --role "push button"` — filter by role.
   - `find --role "label" --name "Status"` — find specific widget. Add `--json` for structured output.
   - `text --role "label" --name "Status"` — read text content.
   - `state --role "text" --json` — full widget details.
   - `screenshot -o /tmp/before.png` — visual check.
   - `apps` — list running AT-SPI apps. `wait --app "name" --timeout 10` — wait for app.
   - Include compact "when to use which" table.

2. **Interact** — perform the action.
   - `click --role "push button" --name "Save"` — click by role+name (uses xdotool at center coords).
   - `type "hello"` — type into focused widget. MUST focus first.
   - `key Return` / `key Tab` / `key Escape` / `key "ctrl+a"` — send keystrokes.
   - `focus --role "text" --name "Email"` — set focus via AT-SPI.
   - `fill --role "text" --name "Email" --value "a@b.com"` — focus + clear + type in one command (preferred).
   - Include compact "when to use which" table.

3. **Verify** — confirm the action worked.
   - Re-read target widget: `text --role "label" --name "Status"`.
   - Re-inspect tree: `tree` (tree changes after interactions).
   - Screenshot: `screenshot -o /tmp/after.png`.
   - Strategy: read target state, read related widgets, screenshot if uncertain.

Note at top: all UI commands auto-detect host vs VM and proxy transparently. No `vm run` wrapping needed. Use `vm run` only for arbitrary non-qt-ai-dev-tools commands.

**Section 2: Focus & Input Rules** (~20 lines)

Critical gotchas — must be inline, not in references:
- Always focus or click a text field before typing — `type` sends to whatever has focus.
- `fill` is preferred over manual focus+clear+type — handles everything in one command.
- AT-SPI `editable_text.insert_text()` does NOT work with Qt — always use xdotool via `type`.
- Click focuses the clicked widget — can type immediately after clicking a text field.
- `key Tab` navigates between fields in tab order.
- Re-inspect tree after focus changes — focus can change widget state.

**Section 3: Error Recovery Essentials** (~20 lines)

Top 3 problems inline (point to `references/troubleshooting.md` for full list):
- **Widget not found** → `tree` to re-inspect, check if name changed, check for dialog blocking.
- **Click had no effect** → `screenshot` to check, look for modal dialog in tree, check if widget is disabled.
- **Text went to wrong widget** → use `fill` instead of manual focus+type, or click target explicitly first.

Target: ~150 lines total.

- [ ] **Step 2: Create references/widget-roles.md**

Write `skills/qt-app-interaction/references/widget-roles.md`.

The AT-SPI role ↔ Qt widget mapping table from current `qt-widget-patterns`. Keep as-is — it's a genuine lookup reference.

Content: the full 25+ row table mapping Qt widget class → AT-SPI role → notes. Copy from current `qt-widget-patterns/SKILL.md` lines 354-387 (the "AT-SPI role reference" table).

Target: ~50 lines.

- [ ] **Step 3: Create references/recipes.md**

Write `skills/qt-app-interaction/references/recipes.md`.

Concrete command sequences for common tasks. Each recipe has: goal (one line), numbered command sequence, verification step.

Recipes to include:
1. **Add an item to a list** — click text field, type, click Add, verify count.
2. **Fill a form** — find text fields with `find --json`, `fill` each, submit, verify.
3. **Navigate a menu** — click menu, re-inspect for items, click item.
4. **Handle a dialog** — detect `[dialog]`/`[alert]` in tree, find buttons, click OK/Cancel, verify dismissed.
5. **Select from combo box** — click to open, re-inspect for menu items, click option. Alternative: keyboard nav (Down/Down/Return).
6. **Switch tabs** — find `[page tab]`, click target, re-inspect for new content.
7. **Interact with a list** — find `[list item]`, click to select. Note: items outside scroll may not appear.
8. **Scroll to reveal widgets** — click inside scroll area, Page_Down/Up, re-inspect.

Source: recipes from current `qt-inspect-interact-verify/SKILL.md` (common sequences section) and widget-specific patterns from `qt-widget-patterns/SKILL.md`.

Target: ~120 lines.

- [ ] **Step 4: Create references/troubleshooting.md**

Write `skills/qt-app-interaction/references/troubleshooting.md`.

Full error recovery patterns. Each entry: problem, symptom/error message, recovery steps.

Entries to include:
1. **Widget not found** — re-inspect tree, check name changed, check dialog blocking, try partial name.
2. **Multiple widgets found** — more specific name, Python API with index.
3. **Click had no effect** — disabled widget, overlapping widget, widget in scroll area, wrong match.
4. **Text input lost / wrong widget** — focus management, modal stealing focus, use `fill`.
5. **AT-SPI stale data** — short delay, re-read, multiple reads.
6. **Unnamed widgets** — tree position, coordinates from JSON, Python API index.
7. **Dynamic content** — partial name match, re-find after changes.
8. **Timing issues** — sleep, wait command, polling loop (include bash example).
9. **App crashed / unresponsive** — check `apps`, screenshot, relaunch.
10. **Empty tree** — app not started, Xvfb/openbox/AT-SPI not running, `QT_ACCESSIBILITY=1`.

Source: error recovery from current `qt-inspect-interact-verify/SKILL.md` and troubleshooting from `qt-widget-patterns/SKILL.md`.

Target: ~100 lines.

- [ ] **Step 5: Commit**

```bash
git add skills/qt-app-interaction/
git commit -m "feat: add qt-app-interaction skill (replaces inspect-interact-verify + widget-patterns)"
```

---

### Task 3: Delete old skills and docs

**Files:**
- Delete: `skills/install-qt-ai-dev-tools/SKILL.md`
- Delete: `skills/qt-inspect-interact-verify/SKILL.md`
- Delete: `skills/qt-widget-patterns/SKILL.md`
- Delete: `docs/agent-workflow.md`
- Delete: `docs/vm-setup-guide.md`

- [ ] **Step 1: Delete old skill directories**

```bash
rm -rf skills/install-qt-ai-dev-tools/
rm -rf skills/qt-inspect-interact-verify/
rm -rf skills/qt-widget-patterns/
```

- [ ] **Step 2: Delete old docs**

```bash
rm docs/agent-workflow.md
rm docs/vm-setup-guide.md
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove old skills and docs (replaced by qt-dev-tools-setup + qt-app-interaction)"
```

---

### Task 4: Update CLAUDE.md and README.md references

**Files:**
- Modify: `CLAUDE.md:62-67` (AI Skills section)
- Modify: `README.md:150-160` (AI agent skills section)
- Modify: `README.md:169` (VM setup guide link)
- Modify: `README.md:218` (skills directory comment)
- Modify: `README.md:223-228` (Documentation section)

- [ ] **Step 1: Update CLAUDE.md skills section**

Replace lines 62-67:

```markdown
## AI Skills

Agent skills in `skills/` teach AI agents the qt-ai-dev-tools workflow:
- `install-qt-ai-dev-tools` — autonomous setup of the toolkit in a project
- `qt-inspect-interact-verify` — core inspect->interact->verify loop
- `qt-widget-patterns` — widget identification strategies and common recipes
```

With:

```markdown
## AI Skills

Agent skills in `skills/` teach AI agents the qt-ai-dev-tools workflow:
- `qt-dev-tools-setup` — install toolkit, configure VM, verify environment
- `qt-app-interaction` — inspect widgets, interact, verify results (the core workflow loop)
```

- [ ] **Step 2: Update README.md skills section**

Replace lines 150-160:

```markdown
## AI agent skills

The `skills/` directory contains structured guidance that teaches AI agents how to use qt-ai-dev-tools effectively:

| Skill | What it teaches |
|-------|-----------------|
| `install-qt-ai-dev-tools` | Autonomous setup of the toolkit in a project -- workspace init, VM boot, environment verification |
| `qt-inspect-interact-verify` | The core workflow loop: inspect the widget tree, interact with widgets, verify results via state checks and screenshots |
| `qt-widget-patterns` | Widget identification strategies, common recipes (form filling, menu navigation, dialog handling), and error recovery |

Skills are the primary integration point. An agent with the right skill can use even a basic CLI effectively.
```

With:

```markdown
## AI agent skills

The `skills/` directory contains structured guidance that teaches AI agents how to use qt-ai-dev-tools effectively:

| Skill | What it teaches |
|-------|-----------------|
| `qt-dev-tools-setup` | Install toolkit, configure VM, verify environment -- everything needed before first interaction |
| `qt-app-interaction` | The core inspect→interact→verify workflow loop, with progressive references for widget roles, recipes, and troubleshooting |

Skills are the primary integration point. An agent with the right skill can use even a basic CLI effectively.
```

- [ ] **Step 3: Update README.md DHCP bug reference**

Replace line 169:

```markdown
- **Known libvirt DHCP bug.** vagrant-libvirt creates a network with a DHCP range starting at `.1`, colliding with the host bridge IP. Workaround: pre-create the network with a corrected range, or use `--static-ip` to bypass DHCP entirely. See [VM setup guide](docs/vm-setup-guide.md).
```

With:

```markdown
- **Known libvirt DHCP bug.** vagrant-libvirt creates a network with a DHCP range starting at `.1`, colliding with the host bridge IP. Workaround: pre-create the network with a corrected range, or use `--static-ip` to bypass DHCP entirely. See `skills/qt-dev-tools-setup/references/vm-troubleshooting.md`.
```

- [ ] **Step 4: Update README.md project structure**

Replace line 218:

```markdown
skills/            # AI agent skills (inspect-interact-verify, widget patterns, setup)
```

With:

```markdown
skills/            # AI agent skills (setup, app interaction)
```

- [ ] **Step 5: Update README.md documentation section**

Replace lines 223-228:

```markdown
## Documentation

- [Roadmap](docs/ROADMAP.md) -- phases, priorities, and design decisions
- [VM setup guide](docs/vm-setup-guide.md) -- provider setup, troubleshooting, configuration
- [Agent workflow](docs/agent-workflow.md) -- recommended command sequences and error recovery
- [Philosophy](docs/PHILOSOPHY.md) -- design principles and architectural decisions
```

With:

```markdown
## Documentation

- [Roadmap](docs/ROADMAP.md) -- phases, priorities, and design decisions
- [Philosophy](docs/PHILOSOPHY.md) -- design principles and architectural decisions
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update CLAUDE.md and README.md to reference new skill names"
```
