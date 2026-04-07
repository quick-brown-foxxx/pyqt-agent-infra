# VLC — Round 2 Validation Log

**App:** VLC 3.0.20 Vetinari (Qt 5.15.13)
**AT-SPI name:** `vlc`
**Date:** 2026-04-07
**Type:** New app validation
**Overall result:** FUNCTIONAL with caveats — slider values not readable, unnamed playback buttons
**Total widgets:** 674

---

## Slider Findings (Most Important)

**Two main sliders detected:**
- **Seek slider** at (708,698 504x18) — no name, no text, no value
- **Volume slider** at (1158,723 85x26) — no name, no text, no value

**Equalizer sliders** (in Effects dialog):
- 1 named "Preamp" slider + 10 unnamed EQ band sliders

**Critical gap:** `state` command returns no value for sliders. VLC (and Qt generally) exposes slider values via AT-SPI `Value` interface (`current_value`, `minimum_value`, `maximum_value`), but qt-ai-dev-tools does not query this interface. This is a **missing capability** — needs `Value` interface support in `_atspi.py` and `state.py`.

## Playback Controls

7 push buttons in bottom toolbar, ALL with **empty names**:
- Play/Pause (larger, 32x32), Previous, Stop, Next, Fullscreen?, Extended?, Playlist?
- 2 unnamed checkboxes (loop/shuffle?)

**Workaround:** Use `--index N` or keyboard shortcuts (Space = play/pause).

This is a VLC accessibility bug but reveals a gap: agents need coordinate-based or position-based identification for unnamed widgets.

## Category 1: Discovery & Tree Inspection — PASS

- 674 widgets — very large tree, `--depth` flag essential
- All major roles found: push button, slider, label, check box, menu item, text, tree, layered pane
- No `[tool bar]` role — VLC uses frames for toolbar containers
- Video area appears as `[layered pane]` > `[filler]` — no special video role

## Category 2: Widget Interaction — PASS with issues

### Working
| Action | Result |
|--------|--------|
| Menu navigation | Works with `--exact` / `--index` ✓ |
| File dialog open (Media > Open File) | Opens correctly ✓ |
| Preferences dialog | Fully accessible, tabs + settings ✓ |
| Effects dialog | Tabs, EQ sliders visible ✓ |
| `fill` text input | Works in playlist search ✓ |
| `key Escape` | Closes dialogs/menus ✓ |

### Name collision issues
| Command | Problem |
|---------|---------|
| `click --name "Media"` | Matches "Media", "Open Recent Media", "Media Information" |
| `click --name "Playlist"` | Matches "Playlist" and "Save Playlist to File..." |
| `click --name "Help"` | Matches menu bar + popup child |

All solvable with `--exact` or `--index 0`.

## Category 3: State Reading — PARTIAL

| What | Readable? |
|------|-----------|
| Labels (speed "1.00x", time) | Yes ✓ |
| Window title | Yes ✓ |
| Slider values (seek, volume) | **NO** — missing Value interface |
| Status bar labels | Text readable but report 0x0 extents |

## Category 4: Screenshots — PASS

Screenshots capture correctly (36-110KB). Must delete stale file before each screenshot due to scrot overwrite bug.

## Category 5: Compound Commands — PARTIAL

- `snapshot save/diff`: detected 52 added widgets when playlist toggled ✓
- `do click --exact`: works ✓
- `do click --index`: **NOT AVAILABLE** — `do` command lacks `--index` option

## Category 6: System Tray — PASS

VLC registers as `StatusNotifierItem-<PID>-2` (SNI D-Bus).

| Command | Result |
|---------|--------|
| `tray list` | Detects VLC tray icon ✓ |
| `tray click` | Toggles window visibility (hide/show) ✓ |
| `tray menu` | Returns 8 playback controls ✓ |
| `tray select ... "N_ormal Speed"` | Works ✓ |

**Notes:**
- Menu items use D-Bus mnemonics: "Pre_vious", "Ne_xt", "N_ormal Speed"
- Some items disabled when no media playing (Previous, Next, Record)
- Tray menu does NOT include Play/Pause, Open File, Quit, Volume

## Category 7: Clipboard — PASS

Round-trip `clipboard write` + `clipboard read` works correctly.

## Category 8: File Dialogs — PASS

| Command | Result |
|---------|--------|
| `file-dialog detect` | Identifies dialog type + path ✓ |
| `file-dialog fill /tmp/test.ogg` | Types path correctly ✓ |
| `file-dialog accept` | Opens file, VLC plays audio ✓ |
| `file-dialog cancel` | Dismisses dialog ✓ |

## Category 9: Preferences — PASS

- Tab categories as named checkboxes: Interface, Audio, Video, Subtitles/OSD, Input/Codecs, Hotkeys
- Simple/All radio buttons for settings mode
- Save/Cancel/Reset buttons named and clickable

## Menu Structure

8 top-level menus, deep submenus:
| Menu | Items | Notable |
|------|-------|---------|
| Media | 15 | Open Recent Media submenu |
| Playback | 17 | Title, Chapter, Speed submenus |
| Audio | 8 | Track, Device, Stereo Mode, Visualizations |
| Video | 13 | Zoom, Aspect Ratio, Crop, Deinterlace |
| Subtitle | 3 | Sub Track |
| Tools | 11 | Effects, Preferences, Codec Information |
| View | 13 | Playlist, Docked Playlist, Status Bar toggles |
| Help | 2 | About, Update |

## New Issues Found

### ISSUE: Missing AT-SPI Value interface support (MAJOR)
Sliders report no value. qt-ai-dev-tools needs to query `Atspi.Value.get_current_value()`, `get_minimum_value()`, `get_maximum_value()`. Affects VLC's seek/volume sliders and any app using QSlider/QDial.

### ISSUE: `do` command lacks `--index` option (MINOR)
Cannot use `do click` with duplicate-named widgets. Must fall back to separate `click` + `screenshot` commands.

### ISSUE: Unnamed playback buttons (OBSERVATION)
VLC doesn't set accessible names on playback controls. Not a tool bug, but reveals need for position-based widget identification strategy for agents.

### ISSUE: Status bar labels report 0x0 extents (MINOR)
Status bar labels (speed, time) have text content but 0x0 extents. The `--visible` filter hides them despite containing useful state information. Same as ISSUE-008 from Phase 6 but in a different app.

## VLC AT-SPI Notes

- **Video area:** `[layered pane]` > `[filler]` — no special role
- **Dialogs persist in tree** at (0,0 0x0) after closing — VLC keeps them alive
- **Custom widgets** (EQ sliders, buttons) expose correct AT-SPI roles but lack names
- **674 widgets at full depth** — `--depth` and `--app` filters essential
- **Page tabs** work well for Preferences and Effects dialogs
- **Tray icon name** includes PID — not findable by "vlc"
