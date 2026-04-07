# KeePassXC — Round 2 Validation Log

**App:** KeePassXC 2.7.6 (Qt 5.15.13)
**AT-SPI name:** `KeePassXC`
**Date:** 2026-04-07
**Type:** Regression + tray + complex workflow
**Overall result:** PASS — no regressions, 4 new issues

---

## Category 1: Discovery & Tree Inspection — PASS

- `tree --app "KeePassXC"`: 237 lines, 139 with visible coordinates
- Visibility filter reduces push buttons from 295 to 13 (95% reduction) — critical for this app
- `find --role "menu item"`: all menus/submenus with correct hierarchy
- `tree --depth 3`: manageable overview

## Category 2: Widget Interaction — PASS

Full wizard flow works:
- Click "Create new database" → wizard opens
- `fill` database name + description fields
- Navigate with "Continue" button clicks
- Fill password fields via `fill --role "password text" --index 0/1`
- "Done" triggers file save dialog
- New Entry creation via toolbar button
- Entry fields (title, username, password, URL) all fillable
- Menu interaction works with `--exact` flag

## Category 3: State Reading — PASS

- `find --json` returns complete widget info with extents + visibility
- `text --role "label"` reads status bar correctly
- Frame title changes tracked ("TestDB - KeePassXC" vs "[Locked]")

## Category 4: Screenshots — PARTIAL

Screenshots captured but sometimes show wrong window (terminal on top of KeePassXC). `scrot` captures whatever is focused/on top in Xvfb. Environment issue, not tool bug, but affects usability. See ISSUE-NEW-3.

## Category 5: Compound Commands — PASS

- `do click "Lock Database" --verify "frame:KeePassXC contains Locked"` works
- `snapshot save` captures 250 widgets
- `snapshot diff` shows meaningful changes between snapshots

## Category 6: System Tray — PASS (with setup requirements)

### Setup Requirements
1. `snixembed` must be running (provides StatusNotifierWatcher D-Bus service)
2. KeePassXC must have "Show a system tray icon" enabled in settings
3. Without snixembed: `tray list` fails with `org.kde.StatusNotifierWatcher was not provided by any .service files`

### Tray Item Identity
- Name: `StatusNotifierItem-<PID>-1` (generic, NOT "KeePassXC")
- Bus: `org.kde.StatusNotifierItem-<PID>-1`
- **Gap:** No way to map tray item → app name without D-Bus introspection

### Menu Structure
- Two items: "Toggle window", "Lock All Databases"
- Substring matching works (`tray select "StatusNotifierItem" "Lock"`)

### Behavior
| Command | Result |
|---------|--------|
| `tray list` | Shows item ✓ |
| `tray click "StatusNotifierItem"` (Activate) | Toggles window hide/show ✓ |
| `tray menu "StatusNotifierItem"` | Returns menu items ✓ |
| `tray select ... "Toggle window"` | Hides/shows window ✓ |
| `tray select ... "Lock"` | Locks database, frame title changes ✓ |

### Key Finding
KeePassXC's tray settings checkbox was at y=1158 (outside 1080px display). `click` raised `ValueError: Coordinates outside display bounds`. Had to use AT-SPI `do_action` directly (not exposed in CLI). **No scroll-into-view capability exists** — see ISSUE-NEW-2.

## Category 7: Clipboard — PASS

| Command | Result |
|---------|--------|
| Copy Password → `clipboard read` | Correct password ✓ |
| Copy Username → `clipboard read` | "myuser" ✓ |
| Copy URL → `clipboard read` | "https://example.com" ✓ |
| `clipboard write` + `clipboard read` | Round-trip ✓ |

## Category 8: File Dialogs — PASS

- "Done" on wizard triggers save dialog
- `file-dialog detect` identifies dialog type + path ✓
- `file-dialog fill /tmp/testdb.kdbx` fills path ✓
- `file-dialog accept` saves database ✓
- `file-dialog cancel` dismisses open dialog ✓

## Category 9: Complex Workflow — PASS

Complete end-to-end:
1. Create database (wizard) ✓
2. Fill name + description ✓
3. Set password ✓
4. Save via file dialog ✓
5. Add entry (title, user, pass, URL) ✓
6. Copy password/user/URL to clipboard ✓
7. Lock database via toolbar ✓
8. Lock/Toggle via tray ✓
9. Unlock via password + Return ✓

## Bridge — Not Applicable

KeePassXC is C++. `eval` gives clear error directing users to Python Qt apps. `bridge status` correctly shows no bridges.

## Regressions — None

All Phase 6 fixes confirmed working:
- ISSUE-010 (visibility filter): 95% widget reduction ✓
- ISSUE-009/004 (index addressing): visible-only matches ✓
- ISSUE-003 (click crash on destroyed widget): file dialog cancel works ✓
- ISSUE-001 (multi-app hint): `--app` correctly targets ✓

## New Issues Found

### ISSUE-NEW-1: Substring matching ambiguity (repeat finding)
Searching `--name "Database"` matches 15 menu items. `--exact` fixes it. Consider making `--exact` default or documenting more prominently.

### ISSUE-NEW-2: No scroll-into-view for off-screen widgets
Settings panel checkboxes at y=1158 reported "visible" by AT-SPI but outside 1080px display. `click` raises ValueError. No CLI command for AT-SPI `do_action` or scroll-into-view. Workaround: keyboard Tab+Space, or direct config file editing.

### ISSUE-NEW-3: Screenshot captures wrong window
`scrot` captures focused/top window which may not be the target app. Need `--window`/`--app` targeting via xdotool window search.

### ISSUE-NEW-4: `--index` inconsistency between `find` and `click`/`fill`
`find --json` shows absolute indices (including invisible), but `click --index` / `fill --index` use visible-only indices. JSON index 4 ≠ `--index 4`. Confusing for agents.

## Deferred Issues Status

| Issue | Status |
|-------|--------|
| ISSUE-005/013 (key/type no --app) | Still present |
| ISSUE-007 (popup 0,0) | Not tested |
| ISSUE-011 (file-dialog multi-app) | Not triggered (single app) |

## KeePassXC AT-SPI Notes

- **Stacked widgets:** 3 copies of many fields (entry view, group view, DB settings). Visibility filter essential.
- **Entry saving:** No visible "Save" button — saves on Enter/Return. Common Qt pattern.
- **Settings panel:** Rendered as stacked widget in main window, content extends beyond display bounds.
- **Config path:** `/home/vagrant/.config/keepassxc/keepassxc.ini` — direct editing as alternative to UI.
- **Tray icon name:** Generic `StatusNotifierItem-<PID>-1`, not app name.
