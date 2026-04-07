# qBittorrent — Round 2 Validation Log

**App:** qBittorrent v4.6.3 (Qt 6.4.2) — first Qt6 real-world app tested
**AT-SPI name:** `qBittorrent`
**Date:** 2026-04-07
**Type:** New app validation
**Overall result:** PASS with notable issues — 3 new issues, 1 critical bug

---

## Qt6 vs Qt5 Differences

**No behavioral AT-SPI differences observed.** Tree structure, roles, extents, and text work identically to Qt5 apps. Strong evidence qt-ai-dev-tools works transparently across Qt5 and Qt6.

One cosmetic Qt6-specific observation: Preferences list items report `width=32767` (likely `QWIDGETSIZE_MAX` leaking through AT-SPI). Not functional.

## Category 1: Discovery & Tree Inspection — PASS

- 188 widgets total — manageable, well-organized tree
- `find --role "push button"`: 31 buttons (toolbar, detail tabs, status bar)
- `find --role "page tab"`: 2 main tabs (Transfers, Search)
- `find --role "table"`: **NONE** — transfer list is `[tree]` role (see Table Findings)
- `find --role "tree"`: 6 tree widgets (transfer list, sidebars, detail panels)
- `find --role "menu item"`: 47 items across all menus
- `find --role "text"`: 2 text fields (toolbar search, search tab input)
- `find --role "list item"`: 14 status filter items + 4 tracker items
- 5 `[unknown]` role widgets (splitter handles) — exist in Qt5 too

## Category 2: Widget Interaction — PASS with issues

### Working
| Action | Result |
|--------|--------|
| Tab switching (`page tab`) | Works ✓ |
| Toolbar buttons (unique names) | Resume, Pause, Preferences ✓ |
| Combo box click | Opens dropdown ✓ |
| `fill` text fields | Fills toolbar search ✓ |
| `key Escape` | Closes menus/dialogs ✓ |
| Unique menu items | "Search Engine", "About" work ✓ |

### Failing due to substring matching
| Command | Problem |
|---------|---------|
| `click --name "File"` | Matches "File" AND "Add Torrent File..." |
| `click --name "Downloading (0)"` | Matches "Downloading" AND "Stalled Downloading" |
| `click --name "Open"` | Matches "Open" AND "Open URL" |

### Detail tabs are buttons, not tabs
The detail panel "tabs" (General, Trackers, Peers, etc.) are `[push button]`, NOT `[page tab]`. qBittorrent-specific AT-SPI implementation.

## Category 3: State Reading — PASS

- `state --role "page tab" --json` returns correct JSON
- `find --role "label" --name "DHT" --json` shows live DHT count (updates over time)
- Labels from hidden detail panels report 0x0 extents correctly

## Category 4: Screenshots — FAIL (critical bug)

**BUG:** Screenshot proxy uses fixed path `/tmp/qt-ai-dev-tools-screenshot.png`. `scrot` on Ubuntu 24.04+ refuses to overwrite without `--overwrite` flag. After first screenshot, ALL subsequent screenshots return stale first image. Command reports success with matching file size.

- **File:** `src/qt_ai_dev_tools/screenshot.py`
- **Fix:** Add `"--overwrite"` to scrot command arguments
- **Workaround:** Delete the file in VM before each screenshot

## Category 5: Compound Commands — PASS

- `snapshot save` + `snapshot diff`: correctly detected tab changes (187 widgets)
- `do click --screenshot`: works (but screenshot is stale after first — see above)
- `fill --role "text"`: works for toolbar search

## Category 6: System Tray — NOT TESTABLE

- qBittorrent v4.6.3 does NOT register an SNI tray icon by default
- `tray list` returns "No tray items found" even with snixembed running
- Would need to enable in Preferences > Behavior — not tested further
- Not a qt-ai-dev-tools bug; environment/configuration issue

## Category 7: File Dialogs — PASS

- "Add Torrent File..." opens native QFileDialog
- `file-dialog detect`: correctly reports dialog type and path
- `file-dialog cancel`: correctly dismisses
- "Add Torrent Link..." dialog fully accessible (text area, buttons)

## Category 8: Settings/Preferences — PASS

- Preferences dialog opens via toolbar or menu
- Full dialog tree: split pane, 8 category items, settings panel, OK/Cancel/Apply
- Categories: Behavior, Downloads, Connection, Speed, BitTorrent, RSS, Web UI, Advanced

## Table Widget Findings (Critical)

**qBittorrent's transfer list is `[tree]` role, NOT `[table]`.**

The transfer tree contains:
- 34 `[table column header]` children
- Visible columns (width > 0): #, Name, Size, Progress, Status, Seeds, Peers, Down Speed, Up Speed, ETA, Ratio, Category, Tags, Availability
- Hidden columns (width = 0): Total Size, Added On, Completed On, Tracker, limits, hashes, etc.
- Detail panel trees also use `[tree]` role

**Implication:** Agents looking for tables should check BOTH `--role "table"` AND `--role "tree"`. Documentation should clarify this.

## New Issues Found

### ISSUE: Screenshot proxy stale file (CRITICAL)
`scrot` on Ubuntu 24.04+ requires `--overwrite` flag. Without it, subsequent screenshots silently return the first image. Fix: add `--overwrite` to scrot command in `screenshot.py`.

### ISSUE: Substring matching causes widespread ambiguity
Common names like "File", "Open", "Downloading" trigger "Multiple widgets found" errors. The `--exact` flag exists but is not the default. In qBittorrent, 3 out of 8 top-level menu items fail due to substring matching.

### OBSERVATION: Click succeeds on invisible menu items
`click --role "menu item" --name "Add Torrent File..."` reports success even when the File menu is closed. Clicks go to AT-SPI coordinates which may be (0,0). Tool should check visibility before clicking.

## qBittorrent AT-SPI Notes

- **Widget density:** 188 nodes, well-organized. Filter sidebar uses `[list]` > `[list item]`.
- **Dynamic tab names:** "Transfers (0)" includes torrent count — changes with state.
- **Status bar buttons:** Interactive speed limit, DHT, connection indicators as push buttons.
- **Search tab coordinates:** Search tab widgets report 0,0 when not active tab. Coordinates update when tab activated.
- **`fill` with multiple text widgets:** Correctly targets visible one when only one visible. Would fail if both visible.
- **Popup menus:** Items report (0,0) when closed, real coordinates when opened — same as Qt5.
