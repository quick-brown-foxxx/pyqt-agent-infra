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
