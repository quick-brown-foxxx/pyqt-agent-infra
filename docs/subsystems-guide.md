# Linux Subsystems Guide

qt-ai-dev-tools provides five subsystem modules for AI agents to interact with Linux desktop capabilities beyond the Qt widget tree. Each wraps system CLI tools behind a typed Python API with transparent VM proxying.

All subsystem modules live in `src/qt_ai_dev_tools/subsystems/`. Shared types are in `models.py`, and `_subprocess.py` provides `check_tool()` / `run_tool()` helpers.

---

## Clipboard

**Module:** `subsystems/clipboard.py` | **Tool:** xclip | **VM requirement:** xclip installed, DISPLAY set

Read and write the X11 clipboard.

### CLI

```bash
qt-ai-dev-tools clipboard write "hello world"   # copy text to clipboard
qt-ai-dev-tools clipboard read                   # paste clipboard contents
```

### Python API

```python
from qt_ai_dev_tools.subsystems import clipboard

clipboard.write("hello world")
text = clipboard.read()
```

---

## File Dialog

**Module:** `subsystems/file_dialog.py` | **Tool:** AT-SPI (via QtPilot) | **VM requirement:** running Qt app with QFileDialog

Automate native Qt file dialogs (open/save) through AT-SPI tree traversal.

### CLI

```bash
qt-ai-dev-tools file-dialog detect               # check if a file dialog is open
qt-ai-dev-tools file-dialog fill /path/to/file    # type path into filename field
qt-ai-dev-tools file-dialog accept                # click Open/Save button
qt-ai-dev-tools file-dialog cancel                # click Cancel button
```

### Python API

```python
from qt_ai_dev_tools.subsystems import file_dialog

info = file_dialog.detect(pilot)          # FileDialogInfo
result = file_dialog.fill(pilot, "/tmp/test.txt")  # FileDialogResult
file_dialog.accept(pilot)
file_dialog.cancel(pilot)
```

**Types:** `FileDialogInfo(dialog_type, current_path)`, `FileDialogResult(accepted, selected_path)`

---

## System Tray

**Module:** `subsystems/tray.py` | **Tool:** busctl (D-Bus) | **VM requirement:** SNI watcher running (e.g., snixembed)

Interact with system tray icons via the D-Bus StatusNotifierItem (SNI) protocol.

### CLI

```bash
qt-ai-dev-tools tray list                         # list registered tray items
qt-ai-dev-tools tray click "MyApp"                # activate tray icon
qt-ai-dev-tools tray menu "MyApp"                 # get context menu entries
qt-ai-dev-tools tray select "MyApp" "Quit"        # select menu item by label
```

### Python API

```python
from qt_ai_dev_tools.subsystems import tray

items = tray.list_items()                 # list[TrayItem]
tray.click("MyApp")
entries = tray.menu("MyApp")              # list[TrayMenuEntry]
tray.select("MyApp", "Quit")
```

**Types:** `TrayItem(name, bus_name, object_path, protocol)`, `TrayMenuEntry(label, enabled, index)`

---

## Notifications

**Module:** `subsystems/notify.py` | **Tool:** dbus-monitor, busctl | **VM requirement:** notification daemon (e.g., dunst)

Listen for desktop notifications and interact with them via D-Bus.

### CLI

```bash
qt-ai-dev-tools notify listen                     # capture notifications (5s default)
qt-ai-dev-tools notify listen --timeout 10        # custom timeout
qt-ai-dev-tools notify dismiss 42                 # close notification by ID
qt-ai-dev-tools notify action 42 "reply"          # invoke notification action
```

### Python API

```python
from qt_ai_dev_tools.subsystems import notify

notifications = notify.listen(timeout=5.0)   # list[Notification]
notify.dismiss(42)
notify.action(42, "reply")
```

**Types:** `Notification(id, app_name, summary, body, actions)`, `NotificationAction(key, label)`

---

## Audio

**Module:** `subsystems/audio.py` | **Tool:** pw-loopback, pw-cat, sox | **VM requirement:** PipeWire + WirePlumber running

Create virtual microphones, play audio into apps, record output, and verify non-silence.

### CLI

```bash
# Virtual microphone
qt-ai-dev-tools audio virtual-mic start            # create virtual mic node
qt-ai-dev-tools audio virtual-mic stop             # stop virtual mic
qt-ai-dev-tools audio virtual-mic play audio.wav   # feed audio into virtual mic

# Recording and verification
qt-ai-dev-tools audio record --duration 3 -o /tmp/out.wav
qt-ai-dev-tools audio sources                      # list PipeWire audio sources
qt-ai-dev-tools audio status                       # show active audio streams
qt-ai-dev-tools audio verify /tmp/out.wav          # check recording is not silence
```

### Python API

```python
from qt_ai_dev_tools.subsystems import audio

info = audio.virtual_mic_start()          # VirtualMicInfo(pid, node_name)
audio.virtual_mic_play("/tmp/audio.wav")
audio.virtual_mic_stop()

audio.record(duration=3.0, output="/tmp/out.wav")
sources = audio.sources()                 # list[AudioSource]
streams = audio.status()                  # list[AudioStream]
result = audio.verify_not_silence("/tmp/out.wav")  # AudioVerification
```

**Types:** `VirtualMicInfo(pid, node_name)`, `AudioSource(id, name, description)`, `AudioStream(id, node_name, state)`, `AudioVerification(is_silent, max_amplitude, rms_amplitude, duration_seconds)`
