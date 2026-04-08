# Validation Issues

Tracked across 3 rounds against SpeedCrunch, KeePassXC, qBittorrent, VLC.

## Fixed (27 issues)

| Issue | Sev | Description |
|-------|-----|-------------|
| ISSUE-001 | Major | `tree` without `--app` only shows first AT-SPI app |
| ISSUE-002 | Major | Name matching is substring-only, no exact match |
| ISSUE-003 | Major | Click on dialog button crashes when widget destroyed |
| ISSUE-004 | Major | `fill` fails with multiple unnamed text widgets |
| ISSUE-005 | Minor | `key`/`type` commands lack `--app` targeting |
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
| ISSUE-021 | Minor | `do click --screenshot` saves in VM, not host |
| ISSUE-022 | Minor | Click succeeds on invisible popup menu items |
| ISSUE-023 | UX | Tray items identified by PID, not app name |
| ISSUE-025 | Minor | Closed menu items bypass visibility filter |
| ISSUE-026 | Critical | Fresh VM: `.local` dir owned by root — blocks CLI |
| ISSUE-027 | Major | AT-SPI xprop race condition on fresh boot |
| NEW-001 | UX | tree --visible defaults to False, inconsistent with find |

## Deferred (5 issues)

### ISSUE-007: Popup menu items have 0,0 coordinates
- **Sev:** UX | **Complexity:** Small
- **Workaround:** Items clickable by name when parent menu is open.
- **Fix:** Annotate `@(hidden)` when extents are all zero in tree formatter.

### ISSUE-008: Labels with 0x0 extents despite being visible
- **Sev:** UX | **Complexity:** Small | **Root cause:** Qt5 AT-SPI bug
- **Workaround:** Text readable via `find --json`.
- **Fix:** Add `[!]` marker for widgets with text but zero extents.

### ISSUE-011: `file-dialog` fails without `--app` when multiple apps run
- **Sev:** Minor | **Complexity:** Small
- **Workaround:** Use `--app` flag explicitly.
- **Fix:** Iterate all AT-SPI apps searching for file dialogs.

### ISSUE-018: No scroll-into-view for off-screen widgets
- **Sev:** Major | **Complexity:** Large (4+ hours)
- **Repro:** KeePassXC settings panel at y=1158 on 1080px display.
- **Workaround:** Keyboard navigation (Tab+Space), direct config file editing.
- **Fix:** AT-SPI `ScrollTo` interface or scroll wheel simulation. Needs research.

### ISSUE-024: Tables may appear as `[tree]` role in AT-SPI
- **Sev:** UX | **Complexity:** Small
- **Example:** qBittorrent transfer list is `[tree]` with `[table column header]` children.
- **Fix:** Document in skills/CLI help. Consider `--role "table-or-tree"` alias.

## Key Observations

- **Qt6 works identically** — zero Qt6-specific issues (qBittorrent Qt 6.4.2).
- **Visibility filter essential** — KeePassXC: 295 to 13 buttons (95% reduction). `STATE_SHOWING` reliable across Qt5/Qt6.
- **Unnamed widgets common** — use `--index` or coordinates. VLC playback buttons have no accessible names.
