# SpeedCrunch — Round 2 Validation Log

**App:** SpeedCrunch (Qt 5.15.13)
**AT-SPI name:** `SpeedCrunch`
**Date:** 2026-04-07
**Type:** Regression check (tested in Phase 6)
**Overall result:** PASS — no regressions

---

## Category 1: Discovery & Tree Inspection — PASS

| Command | Result |
|---------|--------|
| `apps` | Found "SpeedCrunch" |
| `tree --app "SpeedCrunch"` | Full tree, 109 widgets, all roles correct |
| `tree --depth 3` | Truncation works correctly |
| `find --role "push button"` | 0 initially (keypad hidden), 36 after enabling keypad |
| `find --role "label" --json` | 1 label, JSON includes `visible: false` (0x0 extents) |
| `find --role "text"` | 2 text widgets (history display + input line) |
| `find --role "menu item"` | 96 menu items across all menus |

**Visibility filter:** Partially working. `find` shows invisible widgets with `visible: false`. `state` filters them out entirely (see ISSUE-NEW-1).

## Category 2: Widget Interaction — PASS

| Command | Result |
|---------|--------|
| `type "2+3"` + `key Return` | Calculation = 5 ✓ |
| `click --role "menu item" --name "Session"` | Menu opens ✓ |
| `click --role "menu item" --name "View"` then `click "Keypad"` | Keypad toggled on, 36 buttons ✓ |
| Keypad button clicks (7, +, 3, =) | Result "7+3 = 10" ✓ |
| `fill "99+1" --role "text" --index 1` | Input filled, result = 100 ✓ |
| `key Escape` | Works ✓ |
| `--exact` flag | Resolves "Help" vs "Context Help" ambiguity ✓ |

**Note:** After clicking a menu item, window loses focus — must re-click input to type. Standard WM behavior.

## Category 3: State Reading — PASS

| Command | Result |
|---------|--------|
| `text --role "text" --index 0` | Full history text readable ✓ |
| `text --role "text" --index 1` | Input line text readable ✓ |
| `state --role "text" --index 0 --json` | Correct JSON with role/name/text/extents/visible ✓ |
| `text --role "text"` (no index) | Correctly errors "Multiple widgets found" ✓ |
| `state --role "label"` | **Fails** — label has 0x0 extents, filtered out (ISSUE-NEW-1) |

## Category 4: Screenshots — PASS

Screenshots captured correctly (13772 bytes PNG). SpeedCrunch uses dark theme — text nearly invisible in screenshots. AT-SPI text readback is more reliable for verification.

## Category 5: Compound Commands — PASS

| Command | Result |
|---------|--------|
| `do click "Session" --screenshot` | Click + screenshot ✓ |
| `do click "Help" --exact --screenshot` | Works with exact matching ✓ |
| `snapshot save` + `snapshot diff` | Correctly detected label change and text additions ✓ |
| `wait --app "SpeedCrunch"` | Found immediately ✓ |
| `wait --app "NonExistent" --timeout 2` | Correctly timed out ✓ |

**Note:** `--screenshot` saves in VM (`/tmp/screenshot.png`), not transferred to host (ISSUE-NEW-2).

## Category 6: Clipboard — PASS

| Command | Result |
|---------|--------|
| `clipboard write "test123"` + `clipboard read` | Round-trip ✓ |
| SpeedCrunch Edit > Copy Last Result + `clipboard read` | Reads app clipboard correctly ✓ |

## New Issues Found

### ISSUE-NEW-1: `state` vs `find` inconsistency on invisible widgets

`find --role "label" --json` returns SpeedCrunch's "Current result" label with `visible: false`, but `state --role "label"` returns "No widget found" because it filters invisible widgets. Inconsistent behavior between commands.

### ISSUE-NEW-2: `do click --screenshot` saves in VM, not on host

When using transparent proxy, `--screenshot` saves the file inside the VM at `/tmp/screenshot.png`. Not automatically transferred to host. Agents need a separate `screenshot -o` call.

## Deferred Issues Status

| Issue | Status | Notes |
|-------|--------|-------|
| ISSUE-007 (popup 0,0 coords) | Still present | 14/96 menu items show (0,0) when popup closed |
| ISSUE-008 (label 0x0 extents) | Still present | "Current result" label always 0x0 — upstream Qt5 bug |

## SpeedCrunch AT-SPI Notes

- Two unnamed text widgets: index 0 = history display, index 1 = expression input
- Dynamic label "Current result: N" updates on calculation, visible in snapshot diffs
- Keypad toggle changes window width (640→660), all widget extents update in real-time
- Menu items get real coordinates only when parent popup is open
- Dark theme makes screenshots hard to verify visually — use AT-SPI text readback
