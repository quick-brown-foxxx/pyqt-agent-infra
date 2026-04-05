# Wayland Support Feasibility

**Date:** 2026-04-05
**Status:** Research complete, not started
**Effort estimate:** 2-3 weeks focused work for dual-backend support

## Summary

Medium-hard. Clipboard and screenshots are easy swaps. Input automation (xdotool) is the real pain point. The VM infrastructure change (Xvfb to sway headless) is significant but well-documented. AT-SPI mostly works but has a coordinate gotcha.

## Tool-by-Tool Breakdown

| Current (X11) | Wayland Replacement | Drop-in? | Reliability | Effort |
|---|---|---|---|---|
| **xdotool** (click/type/key) | **ydotool** + swaymsg | No | Decent but quirky | **High** |
| **scrot** | **grim** | Nearly | Rock-solid | **Low** |
| **xsel/xclip** | **wl-copy/wl-paste** | Nearly | Mature, universal | **Low** |
| **Xvfb + openbox** | **sway `--headless`** | No | Well-tested | **Medium** |
| **AT-SPI** | **AT-SPI** (same) | Yes* | Coordinate caveat | **Low-Medium** |
| **stalonetray + snixembed** | D-Bus SNI directly | N/A | Simpler | **Simplification** |
| **D-Bus (notify, tray, audio)** | Same | Yes | No change needed | **None** |

## Display-Server Agnostic (No Changes Needed)

These components use D-Bus or other non-display protocols:

- **AT-SPI** — D-Bus IPC, works on both X11 and Wayland
- **D-Bus subsystems** — Notifications (`org.freedesktop.Notifications`) and system tray (SNI) use D-Bus
- **Audio subsystem** — PipeWire is display-server independent
- **File dialog automation** — Uses AT-SPI exclusively
- **Bridge (unix socket)** — Display-server agnostic

## Easy Wins

### Clipboard: wl-clipboard

`wl-clipboard` (`wl-copy` / `wl-paste`) is the definitive answer. Mature, universally supported across all Wayland compositors, nearly API-compatible with xsel. The project's `clipboard.py` just needs a third backend alongside xsel/xclip.

```bash
# X11
xsel --clipboard --input        # write
xsel --clipboard --output       # read

# Wayland
wl-copy "text"                  # write
wl-paste                        # read
```

### Screenshots: grim

`grim` on wlroots compositors. Near-identical CLI to scrot. One function change in `screenshot.py`.

```bash
# X11
scrot /tmp/screenshot.png

# Wayland (wlroots)
grim /tmp/screenshot.png
```

Only works on wlroots compositors (sway, Hyprland, cage). GNOME/KDE need xdg-desktop-portal Screenshot instead (complex, consent dialog).

### System Tray: Simplification

Wayland compositors handle SNI natively. The entire stalonetray + snixembed + xwininfo + xdotool-click-on-tray-icon dance goes away. Just use D-Bus SNI directly (which tray.py already partially does).

## The Hard Part: Input Automation

### ydotool — The Strongest Candidate

- Uses `/dev/uinput` (kernel-level input emulation) — works on **any** compositor
- Requires persistent daemon (`ydotoold`) + permissions (`input` group or root)
- **No window targeting** — can't focus/activate specific windows. Need compositor IPC (`swaymsg`) for that
- Different CLI syntax from xdotool — `interact.py` needs a rewrite
- No `--delay` flag for typing
- Project announced a JavaScript rewrite in 2024, status unclear — stability risk

### Alternatives (All Worse)

| Tool | Problem |
|---|---|
| **wtype** | Doesn't work on GNOME (missing protocol) |
| **wlrctl** | wlroots-only, doesn't do input, only window management |
| **dotool** | Same uinput approach as ydotool, less mature, less packaged |
| **xdg-desktop-portal RemoteDesktop** | Requires user consent dialog — fatal for headless automation |

### What interact.py Needs

Current xdotool operations that need ydotool equivalents:

```python
# Mouse (ydotool equivalent exists)
xdotool mousemove --screen 0 X Y    →  ydotool mousemove --absolute -x X -y Y
xdotool click 1                      →  ydotool click 0xC0
xdotool click 3                      →  ydotool click 0xC2

# Keyboard (ydotool equivalent exists)
xdotool key Return                   →  ydotool key 28:1 28:0
xdotool key ctrl+a                   →  ydotool key 29:1 30:1 30:0 29:0
xdotool type --delay 20 "text"       →  ydotool type "text"  (no delay control)

# Window management (NO ydotool equivalent)
xdotool search --class stalonetray   →  swaymsg -t get_tree (compositor-specific)
xdotool getwindowgeometry WID        →  swaymsg -t get_tree (compositor-specific)
```

## The Tricky Part: AT-SPI Coordinates

AT-SPI's `get_extents()` returns widget screen coordinates for click-by-position. On Wayland, **apps don't know their global position** (security design):

- Qt apps may report `(0,0)` or surface-relative coordinates instead of absolute
- In a controlled sway headless environment with one output, this *might* be predictable
- Needs real testing — could break the core `find widget -> get coords -> click` loop
- GNOME has a DE-specific protocol for accessibility coordinate translation (as of 2025)
- A next-gen accessibility architecture is being designed with surface-relative coordinates

**Risk level:** Medium. In a controlled headless sway environment, behavior may be deterministic, but needs prototyping to verify.

## VM Infrastructure: Xvfb + openbox → sway headless

```bash
# Current (provision.sh.j2)
Xvfb :99 -screen 0 1920x1080 -ac &
openbox &

# Wayland equivalent
WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 sway &
swaymsg output HEADLESS-1 resolution 1920x1080
```

Environment variable changes:
- `DISPLAY=:99` → `WAYLAND_DISPLAY=wayland-0`
- `QT_QPA_PLATFORM=xcb` → `QT_QPA_PLATFORM=wayland`
- `QT_ACCESSIBILITY=1` — stays the same
- `DBUS_SESSION_BUS_ADDRESS` — stays the same

Desktop session service changes:
- Remove: Xvfb, openbox, stalonetray, snixembed
- Add: sway (headless), ydotoold
- Keep: at-spi-bus-launcher, dunst, pipewire, wireplumber, pipewire-pulse

### Headless Compositor Options

| Compositor | Pros | Cons |
|---|---|---|
| **sway (headless)** | Full IPC, largest ecosystem, grim works | Tiling default (configurable) |
| **cage** | Simplest, single-app kiosk | Can't run multiple windows |
| **weston (headless)** | Reference implementation | No wlroots protocols, less tooling |
| **labwc** | Openbox-like feel | No headless backend, no IPC |

**Recommendation:** sway headless for multi-window testing, cage for single-app simplicity.

## Recommended Approach: Dual-Backend

Don't replace X11 — add Wayland as an opt-in alternative.

### Phase 1: Abstract + easy swaps (low risk)

- Abstract tool detection in `_subprocess.py` to support X11/Wayland dispatch
- Add wl-copy/wl-paste backend to `clipboard.py`
- Add grim backend to `screenshot.py`
- Detection: check `$WAYLAND_DISPLAY` vs `$DISPLAY`

### Phase 2: Prototype input + headless (medium risk)

- Set up sway headless in a test branch
- Test ydotool daemon lifecycle + permissions
- **Test AT-SPI coordinate behavior under sway** — this is the make-or-break
- Prototype `interact.py` ydotool backend

### Phase 3: Full integration (high effort)

- Rewrite `interact.py` with backend abstraction (xdotool vs ydotool+swaymsg)
- Create Wayland variant of `provision.sh.j2`
- Simplify tray infrastructure (remove stalonetray/snixembed, use D-Bus SNI directly)
- Update `vm.py` environment setup for Wayland

### Phase 4: CI + polish (optional)

- Dual VM testing (X11 and Wayland)
- Unified provisioning that auto-detects
- Documentation updates

## Files That Need Changes

| File | Change | Priority |
|---|---|---|
| `interact.py` | ydotool backend | High |
| `screenshot.py` | grim backend | Low |
| `clipboard.py` | wl-clipboard backend | Low |
| `tray.py` | Remove xwininfo/stalonetray, pure D-Bus SNI | Medium |
| `provision.sh.j2` | Wayland compositor + tools | Medium |
| `vm.py` | WAYLAND_DISPLAY env, QT_QPA_PLATFORM | Medium |
| `_subprocess.py` | Backend detection helpers | Low |

## Key Risks

1. **AT-SPI coordinates on Wayland** — may break click-by-position. Needs prototyping.
2. **ydotool stability** — daemon management, permission requirements, uncertain project future.
3. **No window targeting without compositor IPC** — ties implementation to specific compositor (sway).
4. **Two code paths to maintain** — dual-backend means double the testing surface.

## References

- [ydotool](https://github.com/ReimuNotMoe/ydotool) — kernel-level input emulation
- [grim](https://github.com/emersion/grim) — wlroots screenshot
- [wl-clipboard](https://github.com/bugaevc/wl-clipboard) — Wayland clipboard
- [sway headless](https://gist.github.com/dluciv/972cc07f081a0b926a3bb07102405dce) — headless config
- [cage](https://github.com/cage-kiosk/cage) — Wayland kiosk compositor
- [wayvnc](https://github.com/any1/wayvnc) — VNC for Wayland (debugging)
- [AT-SPI2 new protocol](https://gnome.pages.gitlab.gnome.org/at-spi2-core/devel-docs/new-protocol.html) — next-gen accessibility
- [Wayland accessibility notes](https://github.com/splondike/wayland-accessibility-notes)
