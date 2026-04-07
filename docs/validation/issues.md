# Real-World Validation — Issues

Issues found during Phase 6 validation against SpeedCrunch and KeePassXC.

---

## Fixed in Phase 6

| Issue | Severity | Description | Commit |
|-------|----------|-------------|--------|
| ISSUE-001 | Major | `tree` without `--app` only shows first AT-SPI app | feat: show multi-app hint |
| ISSUE-002 | Major | Name matching is substring-only, no exact match option | (part of ISSUE-009 batch) |
| ISSUE-003 | Major | Click on dialog button crashes when widget destroyed post-click | fix: cache widget info before click |
| ISSUE-004 | Major | `fill` fails when multiple unnamed text widgets exist | (part of ISSUE-009 batch) |
| ISSUE-006 | Minor | `screenshot -o` SCP transfer fails | fix: replace SCP with base64 transfer |
| ISSUE-009 | Major | No way to distinguish unnamed widgets of same role | (visibility filter + index addressing) |
| ISSUE-010 | Critical | Hidden/stacked panels pollute AT-SPI tree with duplicates | (visibility filter) |
| ISSUE-012 | Minor | Off-screen coordinates silently fail | fix: raise on click outside display bounds |
| ISSUE-014 | Critical | VM provisioning missing AT_SPI_BUS X property for Qt5 | (provision.sh.j2 update) |

---

## Deferred Issues

### ISSUE-005 / ISSUE-013: `key` and `type` commands have no `--app` targeting

- **Category:** Missing capability
- **Severity:** Minor
- **Why deferred:** Keyboard input typically follows a `click` (which sets focus). Low priority since the workaround is natural: click the target app first, then type/key.
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools key Return --app SpeedCrunch
  # Error: No such option: --app
  ```
- **Root cause:** `cli.py` `type_cmd()` and `key()` call `interact.type_text()` / `interact.press_key()` which use `xdotool` without window targeting. No `--app` option exists.
- **Fix:** Add `--app` option. When provided, use `xdotool search --name` or AT-SPI to find the app window and `xdotool windowfocus` before sending input.
- **Complexity:** Medium (1-4 hours)

---

### ISSUE-007: Popup menu items have 0,0 coordinates in widget tree

- **Category:** UX/Polish
- **Severity:** UX/Polish
- **Why deferred:** Cosmetic. Does not block interaction -- popup items are clickable by name.
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools tree --app SpeedCrunch 2>&1 | grep "0,0"
  # Many popup menu items show @(0,0 ...)
  ```
- **Root cause:** AT-SPI reports (0,0) for popup menu items not yet rendered. The tree formatter prints all coordinates unconditionally.
- **Fix:** In `_dump()`, annotate `@(hidden)` when extents are all zero, or `@(0,0 WxH) [popup]` when parent is a popup menu.
- **Complexity:** Small (< 1 hour)

---

### ISSUE-008: Label widget has 0x0 extents despite being visible on screen

- **Category:** UX/Polish
- **Severity:** UX/Polish
- **Why deferred:** Upstream Qt5 AT-SPI bridge bug. We can only add informational markers.
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools find --role "label" --app SpeedCrunch --json
  # "extents": {"x": 0, "y": 0, "width": 0, "height": 0} for "Current result: 4"
  ```
- **Root cause:** Qt5's accessibility bridge sometimes reports (0,0 0x0) for widgets rendered via custom painting. Not a qt-ai-dev-tools bug.
- **Fix:** Add `[!]` marker or `"warning": "zero extents"` for widgets with text content but zero extents. Informational only.
- **Complexity:** Small (< 1 hour)

---

### ISSUE-011: `file-dialog` commands fail without explicit `--app` when multiple apps run

- **Category:** UX friction
- **Severity:** Minor
- **Why deferred:** Partially mitigated by ISSUE-001 fix (multi-app hint). Full fix needs file-dialog to search all apps.
- **Repro:**
  ```bash
  # With KeePassXC file dialog open and main.py also running:
  uv run qt-ai-dev-tools file-dialog detect
  # Error: No file dialog found (searched main.py instead of KeePassXC)
  ```
- **Root cause:** `file_dialog.detect()` receives a pilot bound to a single app. Without `--app`, it defaults to the first app on the AT-SPI bus.
- **Fix:** When no `--app` given, iterate ALL apps on AT-SPI bus searching for a file dialog. File dialogs are typically unique (only one open).
- **Complexity:** Small (< 1 hour)

---

## Triage Summary (Remaining)

| Severity | Count | Issues |
|----------|-------|--------|
| Minor | 2 | ISSUE-005/013, ISSUE-011 |
| UX/Polish | 2 | ISSUE-007, ISSUE-008 |

All Critical and Major issues have been fixed.

---

## Round 2 Issues (2026-04-07)

Tested against 4 apps: SpeedCrunch (Qt 5.15), KeePassXC (Qt 5.15), qBittorrent (Qt 6.4), VLC (Qt 5.15).

### Summary

| Severity | Count | Issues |
|----------|-------|--------|
| Critical | 2 | ISSUE-015, ISSUE-016 |
| Major | 2 | ISSUE-017, ISSUE-018 |
| Minor | 4 | ISSUE-019, ISSUE-020, ISSUE-021, ISSUE-022 |
| UX/Polish | 2 | ISSUE-023, ISSUE-024 |

---

### ISSUE-015: Screenshot proxy returns stale images after first capture [CRITICAL]

- **Category:** Bug
- **Severity:** Critical
- **Apps:** All (confirmed on SpeedCrunch, qBittorrent, VLC)
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools screenshot -o /tmp/shot1.png
  # Change display state (open menu, switch tab, etc.)
  uv run qt-ai-dev-tools screenshot -o /tmp/shot2.png
  # shot1.png and shot2.png are identical (same md5sum)
  ```
- **Root cause:** `scrot` on Ubuntu 24.04+ requires `--overwrite` (`-o`) flag. Without it, scrot silently refuses to write when `/tmp/qt-ai-dev-tools-screenshot.png` already exists. The proxy always uses this fixed path.
- **File:** `src/qt_ai_dev_tools/screenshot.py` line 21
- **Fix:** Add `"--overwrite"` to scrot command: `run_command(["scrot", "--overwrite", path], ...)`
- **Complexity:** Small (< 30 min)

---

### ISSUE-016: `desktop-session.service` fails due to bash quoting bug [CRITICAL]

- **Category:** Bug
- **Severity:** Critical
- **Apps:** All (affects AT-SPI setup for all Qt5 apps)
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools vm run "systemctl --user status desktop-session.service"
  # Status: failed (exit-code 2), restart counter 19
  ```
- **Root cause:** The systemd ExecStart command in the desktop-session service contains a bash one-liner with `grep "string \""` and `sed "s/.*string \"//;s/\"//"`. The escaped double quotes inside the ExecStart line get mishandled by systemd's escaping rules, causing a bash syntax error (unexpected EOF). This means AT_SPI_BUS is never set on the X root window, openbox, snixembed, stalonetray, dunst, and pipewire are not started via the service.
- **Impact:** AT-SPI doesn't work for Qt5 apps without manual `xprop` fix. Tray infrastructure (snixembed, stalonetray) not started.
- **File:** `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` (generates the systemd service)
- **Fix:** Fix quoting in the sed/grep command for systemd ExecStart, or extract to a separate script file that the service calls.
- **Complexity:** Medium (1-2 hours — need to test systemd escaping carefully)

---

### ISSUE-017: AT-SPI Value interface not exposed in CLI [MAJOR]

- **Category:** Missing capability
- **Severity:** Major
- **Apps:** VLC (sliders), any app with QSlider/QDial/QScrollBar
- **Repro:**
  ```bash
  # With VLC running:
  uv run qt-ai-dev-tools state --role "slider" --app "vlc" --json --index 0
  # Returns: {"role": "slider", "name": "", "text": "", "extents": {...}, "visible": true}
  # No "value", "minimum", "maximum" fields
  ```
- **Root cause:** The `_widget_dict()` in `cli.py` and the `state` command don't query the AT-SPI Value interface. The underlying support EXISTS in `_atspi.py` (`get_value()`, `set_value()`, `get_minimum_value()`, `get_maximum_value()`, `has_value_iface()`), but it's not wired to the CLI output.
- **Fix:** Update `_widget_dict()` to include `value`, `min_value`, `max_value` when the widget has the Value interface. Update `state` text output similarly.
- **Complexity:** Small (< 1 hour — plumbing already exists)

---

### ISSUE-018: No scroll-into-view for off-screen widgets [MAJOR]

- **Category:** Missing capability
- **Severity:** Major
- **Apps:** KeePassXC (settings panel at y=1158 on 1080px display), any app with scrollable panels
- **Repro:**
  ```bash
  # With KeePassXC settings open:
  uv run qt-ai-dev-tools click --role "check box" --name "Show a system tray icon" --app "KeePassXC"
  # ValueError: Coordinates outside display bounds (y=1158 > 1080)
  ```
- **Root cause:** AT-SPI reports widget as "visible" with coordinates beyond the display. `click` correctly refuses to click off-screen. But there's no mechanism to scroll the widget into view first.
- **Workaround:** Keyboard navigation (Tab + Space), AT-SPI `do_action` (not exposed in CLI), or direct config file editing.
- **Fix:** Add `scroll-to` command or auto-scroll before click. Could use AT-SPI `ScrollTo` interface or simulate scroll wheel at the widget's parent container.
- **Complexity:** Large (4+ hours — need to investigate AT-SPI ScrollTo support across Qt versions)

---

### ISSUE-019: `state` filters invisible widgets but `find` does not [MINOR]

- **Category:** UX friction
- **Severity:** Minor
- **Apps:** SpeedCrunch (label with 0x0 extents)
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools find --role "label" --app "SpeedCrunch" --json
  # Returns label with "visible": false
  uv run qt-ai-dev-tools state --role "label" --app "SpeedCrunch"
  # "No widget found" — filtered out
  ```
- **Root cause:** `state` command filters by visibility; `find` does not. Inconsistent behavior confuses agents.
- **Fix:** Either make both filter by default (with `--include-hidden` flag), or make neither filter (with `--visible` flag). Document the difference.
- **Complexity:** Small (< 1 hour)

---

### ISSUE-020: `do` command lacks `--index` option [MINOR]

- **Category:** Missing capability
- **Severity:** Minor
- **Apps:** VLC, qBittorrent (apps with duplicate widget names)
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools do click "Help" --role "menu item" --app "vlc" --index 0
  # Error: No such option: --index
  ```
- **Root cause:** The `do` compound command doesn't pass through the `--index` option to the underlying `click` call.
- **Workaround:** Use separate `click --index` + `screenshot` commands.
- **Fix:** Add `--index` parameter to `do click` subcommand.
- **Complexity:** Small (< 30 min)

---

### ISSUE-021: `do click --screenshot` saves in VM, not transferred to host [MINOR]

- **Category:** UX friction
- **Severity:** Minor
- **Apps:** All (when using transparent proxy from host)
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools do click "Session" --role "menu item" --app "SpeedCrunch" --screenshot
  # Output reports "/tmp/screenshot.png" — this is the VM path, not accessible from host
  ```
- **Root cause:** The `--screenshot` flag in `do click` saves the screenshot inside the VM. The transparent proxy transfers the screenshot for the standalone `screenshot` command, but `do click --screenshot` doesn't trigger the proxy transfer.
- **Workaround:** Use separate `click` + `screenshot -o <local-path>` commands.
- **Fix:** Wire `do click --screenshot` through the same proxy transfer path as `screenshot`.
- **Complexity:** Medium (1-2 hours)

---

### ISSUE-022: Click succeeds on invisible/closed popup menu items [MINOR]

- **Category:** Bug
- **Severity:** Minor
- **Apps:** qBittorrent, VLC (any app with popup menus)
- **Repro:**
  ```bash
  # Without opening the File menu first:
  uv run qt-ai-dev-tools click --role "menu item" --name "Add Torrent File..." --app "qBittorrent"
  # Reports success, but clicks at (0,0) — the popup menu coordinates when closed
  ```
- **Root cause:** AT-SPI reports popup menu items with (0,0) coordinates when the parent menu is closed. The `click` command doesn't check if the widget is actually visible/rendered before clicking.
- **Workaround:** Always open the parent menu first, then click the submenu item.
- **Fix:** Check widget extents and parent visibility before clicking. Warn or error when target has 0,0 coordinates and parent popup is not showing.
- **Complexity:** Medium (1-2 hours)

---

### ISSUE-023: Tray items identified by PID, not app name [UX/POLISH]

- **Category:** UX friction
- **Severity:** UX/Polish
- **Apps:** KeePassXC (`StatusNotifierItem-<PID>-1`), VLC (`StatusNotifierItem-<PID>-2`)
- **Repro:**
  ```bash
  uv run qt-ai-dev-tools tray list
  # Shows: StatusNotifierItem-22656-1 (not "KeePassXC")
  uv run qt-ai-dev-tools tray click "KeePassXC"
  # No tray item found
  uv run qt-ai-dev-tools tray click "StatusNotifierItem-22656-1"
  # Works
  ```
- **Root cause:** SNI D-Bus items use generic `StatusNotifierItem-<PID>-<N>` bus names. The app name is available via D-Bus properties (`Id`, `Title`, `IconName`) but `tray list` doesn't query them.
- **Fix:** Enrich `tray list` with app identity from D-Bus properties. Allow matching by app name or icon name in addition to bus name.
- **Complexity:** Medium (1-2 hours)

---

### ISSUE-024: Tables/tree views need documentation clarification [UX/POLISH]

- **Category:** Documentation gap
- **Severity:** UX/Polish
- **Apps:** qBittorrent (transfer list is `[tree]` role, not `[table]`)
- **Root cause:** Qt apps may use `QTreeView` for table-like data. AT-SPI reports these as `[tree]` role with `[table column header]` children. An agent searching for `--role "table"` would miss them.
- **Fix:** Document in skills and CLI help that table-like data may use `[tree]` role. Consider adding a `--role "table-or-tree"` alias or mentioning both in agent-facing documentation.
- **Complexity:** Small (< 30 min)

---

## Round 2 — Observations (Not Issues)

These are not bugs but useful findings for the project:

1. **Qt6 compatibility confirmed.** qBittorrent (Qt 6.4.2) works identically to Qt5 apps. No code changes needed.

2. **Unnamed widgets are common in real apps.** VLC's playback buttons have no accessible names. Agents need `--index` or coordinate-based interaction strategies. Consider adding a "click by position within parent" capability.

3. **Large widget trees are manageable.** VLC has 674 widgets but `--depth` and `--app` filters make output usable. The visibility filter is critical for KeePassXC (95% reduction).

4. **Tray requires snixembed.** Without snixembed running, SNI tray items are invisible. This dependency should be documented more prominently.

5. **Bridge is Python-only.** KeePassXC, qBittorrent, VLC are all C++ — bridge not applicable. `eval` gives clear error message. Bridge inject would need Python 3.14+ runtime in the app process.

6. **Substring matching vs exact matching.** The default substring matching causes widespread ambiguity in real apps. Consider making `--exact` the default in a future release (breaking change) or adding smarter matching (prefer exact match, fall back to substring).
