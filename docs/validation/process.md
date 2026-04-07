# Real-World Qt App Validation: Setup Reference

Quick reference for installing and testing real Qt apps in the VM.

## Setup

```bash
# Install all test apps
uv run qt-ai-dev-tools vm run "sudo apt-get update && sudo apt-get install -y speedcrunch keepassxc qbittorrent vlc"

# AT-SPI bus is set automatically by desktop-session.service.
# Verify: uv run qt-ai-dev-tools vm run "xprop -root AT_SPI_BUS"
```

## Apps

### SpeedCrunch (Qt 5.15 — simple calculator)

```bash
nohup speedcrunch &>/dev/null &   # AT-SPI name: "SpeedCrunch"
pkill speedcrunch
```

- 109 widgets. Two unnamed text widgets: index 0 = history, index 1 = input.
- Dynamic label "Current result: N" updates on calculation.
- Keypad toggle via View > Keypad adds 36 buttons.

### KeePassXC (Qt 5.15 — complex password manager)

```bash
nohup keepassxc &>/dev/null &     # AT-SPI name: "KeePassXC"
pkill keepassxc
```

- 237 widgets. Visibility filter reduces buttons from 295 to 13 (95%).
- Stacked widgets cause 3x duplication — filter essential.
- Tray: enable in settings. Icon name: `StatusNotifierItem-<PID>-1`.
- Entry saving: Enter/Return key (no Save button).
- Settings panel extends beyond display bounds (y>1080).
- Config: `/home/vagrant/.config/keepassxc/keepassxc.ini`.

### qBittorrent (Qt 6.4 — torrent client)

```bash
nohup qbittorrent &>/dev/null &   # AT-SPI name: "qBittorrent"
pkill qbittorrent
```

- **First launch:** "Legal notice" dialog — click "I Agree".
- 188 widgets. Transfer list is `[tree]` role, NOT `[table]`.
- Dynamic tab names: "Transfers (0)" includes count.
- Detail panel "tabs" are `[push button]`, not `[page tab]`.
- Status bar has interactive push buttons (speed, DHT).

### VLC (Qt 5.15 — media player)

```bash
nohup vlc &>/dev/null &           # AT-SPI name: "vlc"
pkill vlc
```

- **First launch:** Privacy dialog — dismiss it.
- 674 widgets — `--depth` and `--app` essential.
- Playback buttons have **no accessible names** — use `--index`.
- Sliders (seek, volume) — values readable via `state --json` (`value`/`min_value`/`max_value`).
- Tray icon: `StatusNotifierItem-<PID>-2`. Menu has playback controls.
- Video area: `[layered pane]` > `[filler]` — no special role.
- Closed dialogs persist in tree at (0,0 0x0).

## Testing Workflow

```bash
# Launch app, wait for AT-SPI registration (~3s)
uv run qt-ai-dev-tools vm run "nohup <app> &>/dev/null &"
sleep 4

# Verify
uv run qt-ai-dev-tools apps
uv run qt-ai-dev-tools tree --app "<AppName>" --depth 4
uv run qt-ai-dev-tools screenshot -o /tmp/shot.png

# Test interaction
uv run qt-ai-dev-tools click --role "push button" --name "<Name>" --app "<AppName>"
uv run qt-ai-dev-tools find --role "slider" --app "<AppName>" --json

# Kill
uv run qt-ai-dev-tools vm run "pkill <app>"
```

## Round 3 — April 2026

- **Apps retested:** All 4 — SpeedCrunch, KeePassXC, qBittorrent, VLC
- **Clean VM reprovision** before testing
- **0 regressions** found
- **1 new issue:** ISSUE-025 (closed menu items bypass visibility filter — minor)
- **2 provisioning bugs found and fixed:**
  - ISSUE-026: `.local` directory owned by root on fresh VM (Critical — blocked all CLI usage)
  - ISSUE-027: AT-SPI xprop race condition on fresh boot (Major — bus discovery could fail)
- **Key observation:** Visibility filter works well but menu items with relative coordinates are a known gap. SpeedCrunch unaffected; KeePassXC shows 68 phantom menu items, VLC shows 76.

## Common Patterns

- **Menu items:** Open parent menu first, then click submenu item. Closed items have (0,0) coords.
- **Disambiguation:** Use `--exact` for exact name match, `--index N` for Nth match.
- **Hidden widgets:** `--no-visible` includes hidden widgets; default is visible-only.
- **Tray:** Requires snixembed running. Items findable by app name or D-Bus Title.
- **Bridge:** Python apps only. C++ apps give clear error.
