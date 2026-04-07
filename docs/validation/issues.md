# Real-World Validation — Issues

Tracked issues from validation against real Qt apps.
Phase 6: SpeedCrunch, KeePassXC. Round 2: + qBittorrent (Qt 6.4), VLC. Round 3: all 4 apps retested.

## Fixed

| Issue | Sev | Description |
|-------|-----|-------------|
| ISSUE-001 | Major | `tree` without `--app` only shows first AT-SPI app |
| ISSUE-002 | Major | Name matching is substring-only, no exact match |
| ISSUE-003 | Major | Click on dialog button crashes when widget destroyed |
| ISSUE-004 | Major | `fill` fails with multiple unnamed text widgets |
| ISSUE-006 | Minor | `screenshot -o` SCP transfer fails |
| ISSUE-009 | Major | No way to distinguish unnamed widgets of same role |
| ISSUE-010 | Critical | Hidden/stacked panels pollute AT-SPI tree |
| ISSUE-012 | Minor | Off-screen coordinates silently fail |
| ISSUE-014 | Critical | VM provisioning missing AT_SPI_BUS for Qt5 |
| ISSUE-015 | Critical | Screenshot stale files (`scrot --overwrite`) |
| ISSUE-016 | Critical | desktop-session.service bash quoting bug |
| ISSUE-017 | Major | AT-SPI Value interface not exposed in CLI |
| ISSUE-019 | Minor | `find`/`state` visibility default inconsistency |
| ISSUE-020 | Minor | `do` command missing `--index` |
| ISSUE-022 | Minor | Click succeeds on invisible popup menu items |
| ISSUE-023 | UX | Tray items identified by PID, not app name |
| ISSUE-026 | Critical | Fresh VM: `.local` dir owned by root — blocks CLI |
| ISSUE-027 | Major | AT-SPI xprop race condition on fresh boot |

---

## Deferred Issues

### ISSUE-025: Closed menu items bypass visibility filter

- **Severity:** Minor
- **Found:** Round 3 (SpeedCrunch not affected, KeePassXC + VLC affected)
- **Status:** Open / Deferred
- **Description:** Submenu items report relative coordinates with non-zero extents, making them appear "visible" when menus are closed. KeePassXC shows 68 menu items, VLC shows 76, when only top-level items are truly visible.
- **Workaround:** Use `--exact` name match or `--role "menu"` for top-level menus only.
- **Fix:** Distinguish absolute vs relative coordinates, or check if parent menu is visible.
- **Complexity:** Medium

### ISSUE-005 / ISSUE-013: `key`/`type` commands lack `--app` targeting

- **Severity:** Minor
- **Confirmed:** Round 3
- **Workaround:** Click target app first (sets focus), then type/key.
- **Fix:** Add `--app` option. Use `xdotool windowfocus` before sending input.
- **Complexity:** Medium (1-4 hours)

### ISSUE-007: Popup menu items have 0,0 coordinates in tree output

- **Severity:** UX/Polish
- **Confirmed:** Round 3
- **Workaround:** Items are clickable by name when parent menu is open.
- **Fix:** Annotate `@(hidden)` when extents are all zero in tree formatter.
- **Complexity:** Small (< 1 hour)

### ISSUE-008: Labels with 0x0 extents despite being visible

- **Severity:** UX/Polish — upstream Qt5 AT-SPI bug
- **Confirmed:** Round 3
- **Workaround:** Text readable via `find --json` and `snapshot diff`.
- **Fix:** Add `[!]` marker for widgets with text but zero extents.
- **Complexity:** Small (< 1 hour)

### ISSUE-011: `file-dialog` fails without `--app` when multiple apps run

- **Severity:** Minor
- **Confirmed:** Round 3
- **Workaround:** Use `--app` flag explicitly.
- **Fix:** Iterate all AT-SPI apps searching for file dialogs.
- **Complexity:** Small (< 1 hour)

### ISSUE-018: No scroll-into-view for off-screen widgets

- **Severity:** Major
- **Confirmed:** Round 3
- **Workaround:** Keyboard navigation (Tab+Space), direct config file editing.
- **Repro:** KeePassXC settings panel at y=1158 on 1080px display.
- **Fix:** AT-SPI `ScrollTo` interface or scroll wheel simulation. Needs research.
- **Complexity:** Large (4+ hours)

### ISSUE-021: `do click --screenshot` saves in VM, not on host

- **Severity:** Minor
- **Confirmed:** Round 3
- **Workaround:** Use separate `click` + `screenshot -o <path>` commands.
- **Fix:** Wire `do --screenshot` through the proxy transfer path.
- **Complexity:** Medium (1-2 hours)

### ISSUE-024: Tables may appear as `[tree]` role in AT-SPI

- **Severity:** UX/Polish — documentation gap
- **Confirmed:** Round 3
- **Example:** qBittorrent's transfer list is `[tree]` with `[table column header]` children.
- **Fix:** Document in skills/CLI help. Consider `--role "table-or-tree"` alias.
- **Complexity:** Small (< 30 min)

---

## Observations

Useful findings from validation, not bugs:

1. **Qt6 works identically.** qBittorrent (Qt 6.4.2) — zero Qt6-specific issues.
2. **Unnamed widgets are common.** VLC playback buttons have no accessible names. Use `--index` or coordinates.
3. **Visibility filter is critical.** KeePassXC: 295 → 13 push buttons (95% reduction). VLC: 674 total widgets, `--depth` essential.
4. **Tray requires snixembed.** Without it, SNI items invisible. Now documented in process.md.
5. **Bridge is Python-only.** C++ apps (KeePassXC, qBittorrent, VLC) — bridge not applicable. Clear error message shown.
6. **Substring matching causes friction.** "File" matches "Add Torrent File...", "Media" matches "Media Information". `--exact` flag exists but isn't default. Consider making exact the default in a future release.
