# Linux Subsystem Helpers — Design Spec

**Date:** 2026-04-05
**Scope:** Phase 6.3/6.4 — Linux subsystem access for AI agents interacting with Qt apps
**Status:** Approved

## Problem

qt-ai-dev-tools gives AI agents eyes and hands for Qt widget interaction (AT-SPI + xdotool). But real Qt apps interact with the OS beyond widgets: file dialogs, clipboard, system tray, notifications, audio. Agents need helpers for these subsystems too.

## Use Cases

Three driving use cases, chosen for breadth of subsystem coverage:

1. **STT app** — record audio (PipeWire virtual mic), transcribe, output text via clipboard paste into external app. Exercises: audio, clipboard, file dialogs.
2. **System tray app** — minimize to tray, context menu, desktop notifications. Exercises: tray, D-Bus notifications.
3. **File picker/saver** — open/save files via native Qt dialog or XDG portal. Exercises: file dialog automation.

## Architecture

New package: `src/qt_ai_dev_tools/subsystems/` — one module per subsystem, each wrapping proven system tools via typed Python APIs.

```
src/qt_ai_dev_tools/subsystems/
├── __init__.py
├── clipboard.py      # xclip wrapper
├── file_dialog.py    # QFileDialog automation (AT-SPI + portal detection)
├── tray.py           # system tray: SNI/XEmbed via D-Bus + AT-SPI
├── notify.py         # D-Bus desktop notifications
├── audio.py          # PipeWire: virtual mic, record, play, verify via sox
```

### Pattern

Each module follows the same structure:
- Typed Python API (functions, not classes) that shells out to system tools via `subprocess.run()`
- All untyped tool output gets runtime-validated typed wrappers — check real types at runtime, fail if mismatch
- CLI commands are thin typer wrappers over the Python API
- Same transparent VM proxy as existing commands
- Return types use `msgspec.Struct` for structured data
- Expected failures return `Result[T, E]` — callers must handle both paths

### CLI Commands

```bash
qt-ai-dev-tools clipboard read|write <text>
qt-ai-dev-tools file-dialog detect|fill <path>|accept|cancel
qt-ai-dev-tools tray list|click|menu|select
qt-ai-dev-tools notify listen|dismiss|action
qt-ai-dev-tools audio virtual-mic start|stop|play|record|verify|sources|status
```

### VM Provision Additions

- `sox` — audio analysis/verification
- `ffmpeg` — audio format conversion
- `xclip` — X11 clipboard access
- `dunst` — lightweight notification daemon
- PipeWire tools (`pw-loopback`, `pw-cat`) — already present with `pipewire` package

## Subsystem Details

### 1. File Dialogs (`file_dialog.py`)

**Problem:** Qt's `QFileDialog` has two modes — native portal-based (via `xdg-desktop-portal`) and Qt's own widget-based. Agent needs to handle both.

**Strategy:**
- `detect()` → check if dialog is portal-based (D-Bus `org.freedesktop.portal.FileChooser`) or Qt-native (AT-SPI shows QFileDialog in widget tree)
- **Portal path:** `dbus-send`/`busctl` to interact with portal API directly
- **Qt-native path:** AT-SPI to find filename text field, type path, click OK — regular widget interaction
- `fill(path)` → type path into filename field (works for both modes)
- `accept()` / `cancel()` → click the appropriate button

**Key insight:** In headless VM with no portal daemon, Qt falls back to its own dialog — fully automatable via existing AT-SPI. Portal support is additive.

**Dependencies:** None new for Qt-native. `xdg-desktop-portal` + `xdg-desktop-portal-gtk` for portal mode (optional).

**Types:**
```python
class FileDialogInfo(msgspec.Struct):
    dialog_type: Literal["qt_native", "portal", "none"]
    current_path: str | None

class FileDialogResult(msgspec.Struct):
    accepted: bool
    selected_path: str | None
```

### 2. Clipboard (`clipboard.py`)

**Strategy:** Wrap `xclip` (X11 — what the VM uses with Xvfb).

```python
def write(text: str) -> Result[None, ClipboardError]
def read() -> Result[str, ClipboardError]
```

- `write()` → pipes text to `xclip -selection clipboard`
- `read()` → `xclip -selection clipboard -o`, validates output is `str`
- Error cases: xclip not installed, empty clipboard, timeout

**Types:**
```python
class ClipboardError(msgspec.Struct):
    message: str
    tool_missing: bool  # True if xclip not found
```

### 3. System Tray (`tray.py`)

**Strategy:** Two protocols:
- **SNI (StatusNotifierItem)** — modern D-Bus protocol. Query `org.kde.StatusNotifierWatcher` for registered items. Interact via D-Bus methods (`Activate`, `ContextMenu`).
- **XEmbed (legacy)** — tray icons in system tray window. Fall back to AT-SPI tree search + xdotool click by coordinates.

**Functions:**
- `list()` → query SNI watcher via `busctl`, return tray items
- `click(app)` → call `Activate` on SNI item, or xdotool click on XEmbed coordinates
- `menu(app)` → call `ContextMenu` on SNI, read popup via AT-SPI
- `select(app, item)` → `menu()` + click menu item by name

**Dependencies:** `busctl` (systemd, already in VM). For XEmbed: xdotool (already present). May need SNI host in openbox — `snixembed` or `stalonetray` if openbox lacks one.

**Types:**
```python
class TrayItem(msgspec.Struct):
    name: str
    bus_name: str
    object_path: str
    protocol: Literal["sni", "xembed"]

class TrayMenuEntry(msgspec.Struct):
    label: str
    enabled: bool
    index: int
```

### 4. Notifications (`notify.py`)

**Strategy:** Monitor D-Bus `org.freedesktop.Notifications` interface.

- `listen(timeout)` → subscribe to `Notify` signal via `dbus-monitor` or `busctl monitor`, parse fields
- `dismiss(id)` → call `CloseNotification(id)` via `busctl`
- `action(id, action_key)` → emit `ActionInvoked` signal

**Dependencies:** `busctl` (systemd), `dunst` notification daemon in VM.

**Types:**
```python
class Notification(msgspec.Struct):
    id: int
    app_name: str
    summary: str
    body: str
    actions: list[NotificationAction]

class NotificationAction(msgspec.Struct):
    key: str
    label: str
```

### 5. Audio (`audio.py`)

**Strategy:** Wrap PipeWire CLI tools + SoX for verification.

**Functions:**
```python
def virtual_mic_start() -> Result[VirtualMicInfo, AudioError]
def virtual_mic_stop() -> Result[None, AudioError]
def virtual_mic_play(path: Path) -> Result[None, AudioError]
def record(duration: float, output: Path, *, loopback: bool = False) -> Result[Path, AudioError]
def sources() -> Result[list[AudioSource], AudioError]
def status() -> Result[list[AudioStream], AudioError]
def verify_not_silence(path: Path, threshold: float = 0.001) -> Result[AudioVerification, AudioError]
```

- Format conversion: `ffmpeg` for MP3→WAV before `pw-cat`
- Verification: `sox file.wav -n stat` → parse "Maximum amplitude" → compare threshold
- Virtual mic lifecycle: store PID of `pw-loopback`, kill on stop

**Types:**
```python
class VirtualMicInfo(msgspec.Struct):
    pid: int
    node_name: str

class AudioSource(msgspec.Struct):
    id: int
    name: str
    description: str

class AudioStream(msgspec.Struct):
    id: int
    node_name: str
    state: Literal["running", "idle", "suspended"]

class AudioVerification(msgspec.Struct):
    is_silent: bool
    max_amplitude: float
    rms_amplitude: float
    duration_seconds: float
```

## Test Flows

### File Dialogs

**1A — Open file via native dialog:**
1. Prepare `/tmp/test-input.txt` with known content
2. Launch test app with "Open File" button
3. `click "Open File"` → dialog appears
4. `file-dialog detect` → reports dialog type
5. `file-dialog fill "/tmp/test-input.txt"` → types path
6. `file-dialog accept` → clicks OK
7. Verify app label shows loaded filename
8. **Success:** app received correct file path

**1B — Save file via dialog:**
1. Launch app, type content into text area
2. `click "Save As"` → save dialog appears
3. `file-dialog fill "/tmp/test-output.txt"`
4. `file-dialog accept`
5. Verify `/tmp/test-output.txt` exists with correct content
6. **Success:** file created with expected content

**1C — Cancel dialog:**
1. `click "Open File"` → dialog appears
2. `file-dialog cancel`
3. Verify app state unchanged
4. **Success:** dialog dismissed, app continues

### Clipboard

**2A — Agent writes clipboard → paste into Qt app:**
1. Launch app with text field
2. `clipboard write "hello from agent"`
3. `key ctrl+v` → paste
4. Verify text field contains "hello from agent"

**2B — Copy from Qt app → agent reads:**
1. Launch app with pre-filled text
2. Focus field, `key ctrl+a`, `key ctrl+c`
3. `clipboard read` → returns field content

**2C — Cross-app round-trip:**
1. Launch two apps
2. Copy from app A → `clipboard read` → paste into app B
3. Verify app B received text

### System Tray

**3A — Tray icon → restore window:**
1. Launch app that minimizes to tray on close
2. Close window → tray icon appears
3. `tray list` → shows app
4. `tray click --app "test_app"` → window restores

**3B — Tray context menu:**
1. App minimized to tray
2. `tray menu --app "test_app"` → returns menu items
3. `tray select --app "test_app" --item "Settings"` → settings dialog appears

**3C — Notification read and dismiss:**
1. App sends notification "Task complete"
2. `notify listen --timeout 5` → captures it
3. Verify body contains "Task complete"
4. `notify dismiss`

**3D — Notification with action:**
1. App sends notification with action "View Results"
2. `notify listen --timeout 5` → captures notification + actions
3. `notify action --name "View Results"` → app reacts

### Audio

**4A — Feed audio into virtual mic → app receives:**
1. `audio virtual-mic start` → creates PipeWire virtual source
2. `audio virtual-mic play /tmp/voice_note.wav` → feeds file
3. App records from virtual mic
4. `audio verify /tmp/voice_note.wav --not-silence` → sanity check

**4B — Record app output via loopback → verify content:**
1. Launch app that plays sound on button click
2. `audio record --loopback --duration 5 --output /tmp/capture.wav &`
3. `click "Play Sound"`
4. `audio verify /tmp/capture.wav --not-silence` → confirms non-silent

**4C — Full STT round-trip:**
1. `audio virtual-mic start`
2. Launch STT app with virtual mic
3. `audio virtual-mic play /tmp/known-speech.wav`
4. App transcribes → text appears in field
5. Read transcription via AT-SPI
6. `clipboard write` + `key ctrl+v` into external target
7. **Success:** known words in → correct text out

## Test Apps

Minimal dedicated apps in `tests/apps/`:

| App | Purpose | Subsystems |
|-----|---------|-----------|
| `file_dialog_app.py` | Open/Save buttons, label for loaded file | File dialogs |
| `clipboard_app.py` | Text field for copy/paste, output label | Clipboard |
| `tray_app.py` | Minimize to tray, context menu, notifications | Tray + Notifications |
| `audio_app.py` | Record from mic, play audio, status display | Audio |
| `stt_app.py` | Load audio → fake transcribe → output text | All combined |

`stt_app.py` fakes transcription (returns known text for known audio) for deterministic tests.

## E2E Tests

`tests/e2e/` — one file per subsystem:
- `test_file_dialog_e2e.py` — flows 1A, 1B, 1C
- `test_clipboard_e2e.py` — flows 2A, 2B, 2C
- `test_tray_e2e.py` — flows 3A, 3B, 3C, 3D
- `test_audio_e2e.py` — flows 4A, 4B, 4C

All run in VM via `make test-e2e`. Marked `@pytest.mark.e2e`.

## Implementation Order

1. **Clipboard** — simplest, needed by others
2. **File dialogs** — self-contained, exercises AT-SPI patterns
3. **System tray + notifications** — D-Bus integration
4. **Audio** — most complex, depends on clipboard for STT flow
5. **STT integration test** — composes all subsystems

## Risks

- **SNI host in openbox:** May need `snixembed` or `stalonetray` if openbox lacks SNI support. Research during implementation.
- **Portal availability in headless VM:** Qt likely falls back to native dialog. Portal tests may need `xdg-desktop-portal` + `xdg-desktop-portal-gtk` installed.
- **PipeWire in VM:** Vagrant VM may not have PipeWire by default. Provision script needs updating.
- **Notification daemon:** Need `dunst` or similar in VM for D-Bus notification tests.
