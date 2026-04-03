# Vagrant + Qt/PySide6 headless testing — results

Date: 2026-04-04

## Goal

Evaluate if Vagrant + Ubuntu + Xvfb + AT-SPI can serve as a Chrome MCP replacement for agent-driven interaction with Qt/PySide6 apps: launch, visually traverse, interact, take screenshots, read state.

## Setup

- **Host:** Fedora 43 (Silverblue), QEMU/libvirt via vagrant-libvirt
- **Guest:** Ubuntu 24.04 (bento/ubuntu-24.04), 4GB RAM, 4 CPUs
- **Display:** Xvfb :99, 1920x1080x24
- **Window manager:** Openbox (headless, required for correct xdotool coords)
- **Accessibility:** AT-SPI via `gi.repository.Atspi`, dbus user session
- **Services:** `xvfb.service` (system), `desktop-session.service` (user, runs openbox + at-spi-bus-launcher)

## What works

### 1. pytest-qt unit tests (offscreen) — WORKS

Standard pytest-qt with `QT_QPA_PLATFORM=offscreen`. No Xvfb needed. Fast (<0.1s for 6 tests).

```bash
./scripts/vm-run.sh "cd /vagrant && QT_QPA_PLATFORM=offscreen pytest tests/ -v"
```

### 2. Screenshots via scrot — WORKS

scrot captures the Xvfb framebuffer. Files are ~14-22KB PNG. Agent can view them via the Read tool after scp to host.

```bash
./scripts/vm-run.sh "scrot /tmp/screen.png"
scp -F .vagrant-ssh-config default:/tmp/screen.png /tmp/screen.png
```

### 3. AT-SPI widget tree traversal — WORKS

Full accessibility tree with roles, names, and screen coordinates. Equivalent to DOM inspection in Chrome MCP but typed to Qt widget roles.

```python
from qt_pilot import QtPilot
pilot = QtPilot()
pilot.dump_tree()
```

Output:
```
[application] "main.py"
  [frame] "Qt Dev Proto" @(720,387 480x320)
    [filler] ""
      [label] "Готов" @(736,403 448x14)
      [text] "" @(736,429 356x22)
      [push button] "Добавить" @(1104,429 80x22)
      [list] "" @(736,463 448x194)
      [push button] "Очистить" @(736,669 80x22)
      [label] "Элементов: 0" @(1099,669 85x22)
```

### 4. Button clicks via AT-SPI — WORKS (most reliable method)

AT-SPI action interface triggers the button's native click handler. No coordinate calculation needed.

```python
btn = pilot.find_one(role="push button", name="Добавить")
pilot.action(btn, "Press")
```

### 5. Text input via xdotool — WORKS

xdotool sends real X11 keystrokes. Must click/focus the widget first. AT-SPI's `editable_text.insert_text()` does NOT work — it updates the accessible layer but not Qt's internal model.

```python
text_input = pilot.find_one(role="text")
pilot.click(text_input)       # focus via xdotool click at widget center
pilot.type_text("hello")      # xdotool type
```

### 6. Reading widget state — WORKS

Widget names update in real-time after interactions.

```python
status = pilot.find_one(role="label", name="Добавлено")
count = pilot.find_one(role="label", name="Элементов")
list_w = pilot.find_one(role="list")
items = [pilot.get_name(c) for c in pilot.get_children(list_w)]
```

### 7. Full test suite (8/8) — WORKS

All tests pass including AT-SPI smoke test and scrot screenshot test.

```bash
./scripts/vm-run.sh "cd /vagrant && pytest tests/ -v"
# 8 passed, 0 skipped
```

## What does NOT work

### AT-SPI editable_text for input

`widget.get_editable_text_iface().insert_text()` modifies the accessibility layer but Qt's `QLineEdit.text()` stays empty. The button handler sees empty input and rejects it. This is a Qt/AT-SPI bridge limitation — text must go through X11 key events (xdotool).

### xdotool without a window manager

Without openbox, `xdotool mousemove --window <id>` uses wrong coordinates and `windowactivate` fails with `_NET_ACTIVE_WINDOW not supported`. Openbox is required.

### pyatspi (old Python API)

The `pyatspi` package is not pip-installable on Python 3.12. Use `gi.repository.Atspi` instead (installed via `gir1.2-atspi-2.0` + `python3-gi` system packages).

## What is painful

### 1. Interaction requires inline Python heredocs

Every agent interaction is a multi-line `vm-run.sh "python3 << 'EOF' ... EOF"` block. ~15 lines minimum to click a button and check the result. No CLI shorthand exists yet.

### 2. Screenshot round-trip is 3 steps

`scrot` inside VM → `scp` to host → `Read` tool to view. Could be a single `./scripts/screenshot.sh` but that script currently requires ControlMaster to already exist.

### 3. No persistent AT-SPI session

Each `vm-run.sh` call is a fresh SSH command. The agent re-discovers the app, re-builds the widget tree every time. Can't do iterative "poke and observe" without reconnecting.

### 4. rsync is manual

Files must be synced with `vagrant rsync` before running updated code. The `--sync` flag on `vm-run.sh` helps but it's easy to forget.

### 5. vagrant-libvirt DHCP bug

vagrant-libvirt creates the `vagrant-libvirt` network with DHCP range starting at `.1` (the host bridge IP). dnsmasq cannot allocate addresses. Fix: pre-create the network with `start='192.168.121.2'` and optionally pin a static MAC→IP mapping in the Vagrantfile (`v.management_network_mac`).

## Architecture

```
Host (Fedora)                          Guest (Ubuntu 24.04)
─────────────                          ────────────────────
vm-run.sh ──SSH──────────────────────▶ bash (env vars set)
  │                                      │
  │  "python3 << EOF                     ├── python3
  │   from qt_pilot import QtPilot       │   ├── AT-SPI (gi.repository.Atspi)
  │   ...                                │   │   └── dbus session bus
  │   EOF"                               │   └── xdotool (X11 keystrokes)
  │                                      │
screenshot.sh ──SSH──────────────────▶ scrot (captures Xvfb :99)
  │ ◀──SCP──────────────────────────── /tmp/screenshot.png
  │
  └── Read tool (view PNG)

Services (auto-start):
  xvfb.service (system)      → Xvfb :99
  desktop-session (user)     → openbox + at-spi-bus-launcher
```

## How to reproduce

```bash
# 1. Pre-create the libvirt network (fixes DHCP bug)
virsh -c qemu:///system net-define /tmp/vagrant-libvirt-net.xml
virsh -c qemu:///system net-start vagrant-libvirt
# (see net XML in repo or use range 192.168.121.2-254 with host entry for MAC)

# 2. Start VM
vagrant up --provider=libvirt

# 3. Run tests
make test-full

# 4. Interactive use
./scripts/vm-run.sh "python3 /vagrant/app/main.py &"
sleep 2
./scripts/vm-run.sh "python3 -c '
import sys; sys.path.insert(0, \"/vagrant/scripts\")
from qt_pilot import QtPilot
pilot = QtPilot()
pilot.dump_tree()
pilot.screenshot(\"/tmp/shot.png\")
'"
scp -F .vagrant-ssh-config default:/tmp/shot.png /tmp/shot.png

# 5. Cleanup
vagrant destroy -f
vagrant box remove bento/ubuntu-24.04   # if you need the disk space
```

## Potential next steps

1. **qt_pilot CLI** — `./scripts/qt-pilot.sh dump-tree`, `click "push button" "Save"`, `type "hello"`, `screenshot`. Eliminates Python heredocs for agent interaction.

2. **One-shot screenshot script** — single command that takes screenshot + copies to host + prints path.

3. **Persistent pilot server** — a long-running process inside the VM that accepts commands over a socket/stdin, avoiding AT-SPI reconnection on every call. Could be a simple JSON-RPC or line-protocol over SSH.

4. **MCP server wrapper** — expose qt_pilot as an MCP server so Claude Code can call `click`, `type`, `screenshot`, `dump_tree` as native tools instead of bash commands.

5. **rsync-auto** — `vagrant rsync-auto` in background for live sync. Or switch to NFS/virtiofs if performance matters.

6. **Snapshot for fast reset** — `vagrant snapshot save clean && vagrant snapshot restore clean` to reset VM state between test runs.

## Verdict

**This setup works as a Chrome MCP replacement for Qt apps.** The combination of AT-SPI (structured widget tree with roles/names/coords) + xdotool (real keystrokes) + scrot (screenshots) gives the agent everything Chrome DevTools provides: inspect → interact → verify. For Qt specifically it's arguably better than Chrome MCP because AT-SPI gives typed widget access rather than generic DOM nodes.

The main friction is ergonomics — the agent interaction API is verbose. A CLI wrapper or MCP server would make this production-ready.
