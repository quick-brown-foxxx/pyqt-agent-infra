# Real-World Validation Round 2 — Implementation Plan

> **For agentic workers:** This is a sequential validation plan. Each task produces documentation artifacts. Use superpowers:executing-plans to work through tasks. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate qt-ai-dev-tools against 4 real Qt apps (2 repeat, 2 new) to discover bugs, missing capabilities, and architectural gaps. Produce a triaged issue list with repro steps and fix estimates.

**Architecture:** Sequential app-by-app validation in a shared Vagrant VM. Each app gets installed, launched, tested across all tool capabilities, and documented. A final triage phase consolidates all findings.

**Tech Stack:** qt-ai-dev-tools CLI, Vagrant VM (Ubuntu 24.04), AT-SPI, xdotool, scrot, D-Bus

**Key principle:** This is exploration, not implementation. Spawn a researcher/prototyper agent for each app to test strategies, adjust environment, and report findings. First runs may fail — that's expected and valuable. Document everything for reproducibility.

**Bridge note:** If a CLI command fails but the same goal is achievable via `qt-ai-dev-tools eval "code"`, that's a Minor issue (not Critical). Bridge is a first-class interaction method.

---

## Output Files

| File | Purpose |
|------|---------|
| `docs/validation/process.md` | Updated: add qBittorrent, VLC setup instructions |
| `docs/validation/issues.md` | Updated: append new issues (ISSUE-015+) |
| `docs/validation/round2/plan.md` | Copy of this plan for future reference |
| `docs/validation/round2/speedcrunch.md` | SpeedCrunch detailed test log |
| `docs/validation/round2/keepassxc.md` | KeePassXC detailed test log |
| `docs/validation/round2/qbittorrent.md` | qBittorrent detailed test log |
| `docs/validation/round2/vlc.md` | VLC detailed test log |

---

## How to Run Commands

- **UI commands** (tree, click, type, screenshot, find, apps, wait, fill, do, tray, clipboard, etc.): Run directly on host — they auto-proxy to VM via SSH.
  ```bash
  uv run qt-ai-dev-tools tree --app "SpeedCrunch"
  uv run qt-ai-dev-tools click --role "push button" --name "Save"
  ```
- **Arbitrary VM commands** (install packages, launch apps, kill apps, check processes):
  ```bash
  uv run qt-ai-dev-tools vm run "sudo apt-get install -y qbittorrent"
  uv run qt-ai-dev-tools vm run "nohup qbittorrent &>/dev/null &"
  uv run qt-ai-dev-tools vm run "pkill qbittorrent"
  ```
- **Bridge eval** (run Python inside the app process — only works for Python apps or with inject for 3.14+):
  ```bash
  uv run qt-ai-dev-tools eval "app.windowTitle()"
  ```
- **Screenshots**:
  ```bash
  uv run qt-ai-dev-tools screenshot -o /tmp/shot.png
  ```

**Important:** Always `cd /var/home/user1/Projects/pyqt-agent-infra` before running commands.

---

## Test Categories Reference

When testing each app, work through these categories in order. Skip categories that don't apply (e.g., bridge won't work on C++ apps without inject).

### Category 1: Discovery & Tree Inspection
```bash
uv run qt-ai-dev-tools apps                           # App visible on AT-SPI bus?
uv run qt-ai-dev-tools tree --app "<AppName>"          # Full widget tree
uv run qt-ai-dev-tools tree --app "<AppName>" --depth 3  # Shallow tree
uv run qt-ai-dev-tools find --role "push button" --app "<AppName>"  # Find by role
uv run qt-ai-dev-tools find --role "label" --app "<AppName>" --json  # JSON output
```
Document: widget count, role distribution, any duplicates from hidden panels, tree depth, app name on AT-SPI bus.

### Category 2: Widget Interaction
```bash
uv run qt-ai-dev-tools click --role "push button" --name "<ButtonName>" --app "<AppName>"
uv run qt-ai-dev-tools type "some text"
uv run qt-ai-dev-tools key Return
uv run qt-ai-dev-tools key ctrl+a
uv run qt-ai-dev-tools fill "text" --role "text" --name "<FieldName>" --app "<AppName>"
```
Document: which widgets are clickable, which aren't, error messages, coordinate issues.

### Category 3: State Reading
```bash
uv run qt-ai-dev-tools text --role "label" --name "<LabelName>" --app "<AppName>"
uv run qt-ai-dev-tools state --role "text" --app "<AppName>"
```
Document: what state is readable, what's missing, accuracy of reported values.

### Category 4: Screenshots
```bash
uv run qt-ai-dev-tools screenshot -o /tmp/shot.png
```
Document: screenshot captures correctly, app is visible, resolution is adequate.

### Category 5: Compound Commands
```bash
uv run qt-ai-dev-tools do click "<ButtonName>" --role "push button" --app "<AppName>" --screenshot
uv run qt-ai-dev-tools do click "<ButtonName>" --role "push button" --app "<AppName>" --verify "label:<LabelName> contains <text>"
uv run qt-ai-dev-tools snapshot save --app "<AppName>" -o /tmp/before.json
# ... do something ...
uv run qt-ai-dev-tools snapshot diff /tmp/before.json --app "<AppName>"
```

### Category 6: System Tray (if app has tray icon)
```bash
uv run qt-ai-dev-tools tray list
uv run qt-ai-dev-tools tray click "<AppName>"
uv run qt-ai-dev-tools tray menu "<AppName>"
uv run qt-ai-dev-tools tray select "<AppName>" "<MenuItemLabel>"
```
Document: tray icon detected? SNI vs XEmbed? Menu items accessible? Actions work?

### Category 7: Clipboard (if app supports copy/paste)
```bash
uv run qt-ai-dev-tools clipboard write "test"
uv run qt-ai-dev-tools clipboard read
```
Document: clipboard integration works end-to-end with the app.

### Category 8: Bridge (Python apps only, or 3.14+ inject)
```bash
uv run qt-ai-dev-tools bridge status
uv run qt-ai-dev-tools eval "app.windowTitle()" --app "<AppName>"
```
Note: Most real-world apps are C++ compiled Qt — bridge won't work without Python 3.14+ inject. Document this limitation.

### Category 9: File Dialogs (if app uses them)
```bash
uv run qt-ai-dev-tools file-dialog detect --app "<AppName>"
uv run qt-ai-dev-tools file-dialog fill "/path/to/file" --app "<AppName>"
uv run qt-ai-dev-tools file-dialog accept --app "<AppName>"
```

---

## Task 1: Setup — Install All Apps in VM

**Files:**
- Modify: `docs/validation/process.md` (add qBittorrent, VLC sections)

- [ ] **Step 1: Install qBittorrent and VLC in the VM**

```bash
uv run qt-ai-dev-tools vm run "sudo apt-get update && sudo apt-get install -y qbittorrent vlc"
```

- [ ] **Step 2: Verify SpeedCrunch and KeePassXC are still available (or install)**

```bash
uv run qt-ai-dev-tools vm run "which speedcrunch && which keepassxc || sudo apt-get install -y speedcrunch keepassxc"
```

- [ ] **Step 3: Test-launch each app and verify AT-SPI visibility**

For each app, launch it, wait 3 seconds, check `qt-ai-dev-tools apps`, then kill it. Document the AT-SPI app name for each.

```bash
# Pattern for each app:
uv run qt-ai-dev-tools vm run "nohup <app-command> &>/dev/null &"
sleep 3
uv run qt-ai-dev-tools apps
uv run qt-ai-dev-tools vm run "pkill <app-name>"
```

Apps to test: `speedcrunch`, `keepassxc`, `qbittorrent`, `vlc`

- [ ] **Step 4: Take a screenshot of each app to verify display**

Launch each app, take screenshot, verify it shows the app window, kill it.

- [ ] **Step 5: Update `docs/validation/process.md`**

Add qBittorrent and VLC sections with install/launch/kill commands and AT-SPI app names.

- [ ] **Step 6: Commit**

```bash
git add docs/validation/process.md
git commit -m "docs(validation): add qBittorrent and VLC setup instructions"
```

---

## Task 2: Validate SpeedCrunch (Regression)

**Files:**
- Create: `docs/validation/round2/speedcrunch.md`

This is a quick regression check. SpeedCrunch was the simple baseline in Phase 6.

- [ ] **Step 1: Launch SpeedCrunch**

```bash
uv run qt-ai-dev-tools vm run "nohup speedcrunch &>/dev/null &"
sleep 3
```

- [ ] **Step 2: Run researcher agent for SpeedCrunch validation**

Spawn a researcher/prototyper agent. It should:
1. Run all Category 1-5 tests (discovery, interaction, state, screenshots, compound)
2. SpeedCrunch has no tray icon — skip Category 6
3. Test clipboard: copy a calculation result, read clipboard
4. Test specific use cases from Phase 6: enter calculation (click digits or type), verify result label, clear
5. Compare behavior against Phase 6 findings — do visibility filters work? Exact matching?
6. Document EVERYTHING in a structured log

The agent should report:
- What worked (with exact commands)
- What failed (with exact error messages)
- New issues discovered
- Regressions from Phase 6 fixes

- [ ] **Step 3: Write `docs/validation/round2/speedcrunch.md`**

Document all findings from the researcher agent.

- [ ] **Step 4: Kill SpeedCrunch**

```bash
uv run qt-ai-dev-tools vm run "pkill speedcrunch"
```

- [ ] **Step 5: Commit**

```bash
git add docs/validation/round2/speedcrunch.md
git commit -m "docs(validation): SpeedCrunch round 2 results"
```

---

## Task 3: Validate KeePassXC (Regression + Tray)

**Files:**
- Create: `docs/validation/round2/keepassxc.md`

KeePassXC was the complex stress test. This round adds tray testing and checks deferred issues.

- [ ] **Step 1: Launch KeePassXC**

```bash
uv run qt-ai-dev-tools vm run "nohup keepassxc &>/dev/null &"
sleep 3
```

- [ ] **Step 2: Run researcher agent for KeePassXC validation**

Spawn a researcher/prototyper agent. It should:
1. Run ALL categories (1-9) — KeePassXC has tray, clipboard, file dialogs
2. **Tray testing (critical):** `tray list`, `tray click`, `tray menu`, `tray select` — KeePassXC uses SNI tray
3. Test deferred issues: ISSUE-005/013 (key/type without --app), ISSUE-007 (popup coordinates), ISSUE-011 (file-dialog multi-app)
4. Test complex workflows: create database → add entry → copy password → lock → unlock
5. Test stacked widget behavior (Phase 6 key finding)
6. Try bridge inject if possible (KeePassXC is C++ — likely won't work, document this)
7. Document EVERYTHING

- [ ] **Step 3: Write `docs/validation/round2/keepassxc.md`**

- [ ] **Step 4: Kill KeePassXC**

```bash
uv run qt-ai-dev-tools vm run "pkill keepassxc"
```

- [ ] **Step 5: Commit**

```bash
git add docs/validation/round2/keepassxc.md
git commit -m "docs(validation): KeePassXC round 2 results"
```

---

## Task 4: Validate qBittorrent (New App)

**Files:**
- Create: `docs/validation/round2/qbittorrent.md`

qBittorrent is a torrent client with tables, status bars, tabs, filters, and a system tray icon.

- [ ] **Step 1: Launch qBittorrent**

```bash
uv run qt-ai-dev-tools vm run "nohup qbittorrent &>/dev/null &"
sleep 3
```

- [ ] **Step 2: Run researcher agent for qBittorrent validation**

Spawn a researcher/prototyper agent. It should:
1. Start with discovery: `apps`, `tree`, `screenshot` — learn the AT-SPI app name
2. Explore the widget tree — tabs, tables, status bar, filter sidebar
3. Test interaction: click tabs, interact with filter sidebar, try search
4. Test tray: `tray list`, minimize to tray, restore from tray, tray menu
5. Test compound commands and snapshot diff
6. Test clipboard (if qBittorrent supports copy operations)
7. Test file dialogs (add torrent file dialog)
8. Document all findings, especially:
   - How the table widget appears in AT-SPI (rows, cells, selection)
   - Tab switching behavior
   - Tray icon type (SNI vs XEmbed) and menu accessibility
   - Any new widget types not seen before

- [ ] **Step 3: Write `docs/validation/round2/qbittorrent.md`**

- [ ] **Step 4: Kill qBittorrent**

```bash
uv run qt-ai-dev-tools vm run "pkill qbittorrent"
```

- [ ] **Step 5: Commit**

```bash
git add docs/validation/round2/qbittorrent.md
git commit -m "docs(validation): qBittorrent round 2 results"
```

---

## Task 5: Validate VLC (New App)

**Files:**
- Create: `docs/validation/round2/vlc.md`

VLC is a media player with menus, playlists, sliders, custom rendering, and a system tray icon.

- [ ] **Step 1: Launch VLC**

```bash
uv run qt-ai-dev-tools vm run "nohup vlc &>/dev/null &"
sleep 3
```

- [ ] **Step 2: Run researcher agent for VLC validation**

Spawn a researcher/prototyper agent. It should:
1. Start with discovery: `apps`, `tree`, `screenshot` — learn the AT-SPI app name
2. Explore the widget tree — menus, playback controls, sliders, playlist
3. Test interaction: click play/pause, navigate menus, open media dialog
4. Test sliders: volume slider, seek slider — can we read position? Set position?
5. Test tray: `tray list`, minimize to tray, restore, tray menu items
6. Test compound commands
7. Test file dialogs (Open Media dialog)
8. Test clipboard (if VLC supports copy of media info)
9. Document all findings, especially:
   - Slider widget representation in AT-SPI (range, value, settable?)
   - Menu structure (VLC has deep menus)
   - Custom-rendered video area in AT-SPI
   - Tray icon behavior
   - Any AT-SPI issues specific to VLC's custom UI components

- [ ] **Step 3: Write `docs/validation/round2/vlc.md`**

- [ ] **Step 4: Kill VLC**

```bash
uv run qt-ai-dev-tools vm run "pkill vlc"
```

- [ ] **Step 5: Commit**

```bash
git add docs/validation/round2/vlc.md
git commit -m "docs(validation): VLC round 2 results"
```

---

## Task 6: Triage — Consolidate Issues

**Files:**
- Modify: `docs/validation/issues.md`

- [ ] **Step 1: Collect all issues from round 2 logs**

Read all 4 app logs (`speedcrunch.md`, `keepassxc.md`, `qbittorrent.md`, `vlc.md`) and extract every issue found.

- [ ] **Step 2: Deduplicate and categorize**

For each issue:
- Assign an ID (ISSUE-015+)
- **Category:** Bug / Missing capability / UX friction / Architectural gap
- **Severity:** Critical (blocks core workflow) / Major (significant friction) / Minor (workaround exists) / UX-Polish (cosmetic)
- **Repro steps:** Exact commands to reproduce
- **Root cause:** Best understanding of why it happens
- **Workaround:** Especially bridge-based alternatives
- **Potential fix:** What code would need to change
- **Complexity:** Small (<1h) / Medium (1-4h) / Large (4h+)
- **Apps affected:** Which of the 4 apps exhibit this issue

- [ ] **Step 3: Reproduce each issue**

Spawn an agent to re-run the repro steps for each issue and confirm it's real and the repro is accurate. Update repro steps if needed.

- [ ] **Step 4: Write the final issue list**

Update `docs/validation/issues.md`:
- Keep existing Phase 6 sections
- Add new "Round 2 Issues" section
- Include full triage table and detailed issue descriptions
- Add a summary table at the top

- [ ] **Step 5: Commit**

```bash
git add docs/validation/issues.md docs/validation/round2/
git commit -m "docs(validation): round 2 triage — N issues found across 4 apps"
```

---

## Task 7: Final Summary & Roadmap Update

- [ ] **Step 1: Write round 2 summary**

Create a summary section in `docs/validation/round2/plan.md` with:
- Total issues found by category and severity
- Key themes (e.g., "tray interaction unreliable", "table widgets poorly supported")
- Comparison with Phase 6 results
- Recommendations for next priorities

- [ ] **Step 2: Present final issue list to user**

Show the triaged issue list with severity, category, and fix complexity.

- [ ] **Step 3: Commit all remaining changes**

```bash
git add docs/
git commit -m "docs(validation): round 2 complete — summary and roadmap notes"
```
