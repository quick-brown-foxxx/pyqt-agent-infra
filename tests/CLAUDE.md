# tests/ — Test Infrastructure Reference

## How to run tests

All test commands run inside the Vagrant VM via `make` targets on the host:

| Target | VM required? | Description |
|---|---|---|
| `make test` | Yes | Fast pytest-qt tests, offscreen (`QT_QPA_PLATFORM=offscreen`), no Xvfb needed. Runs `tests/test_main.py` excluding atspi/scrot markers. |
| `make test-full` | Yes | All tests including AT-SPI, screenshots, CLI, and e2e. Runs `tests/ -v`. |
| `make test-cli` | Yes | CLI integration tests only (`tests/integration/`). |
| `make test-e2e` | Yes | E2E bridge/subsystem tests (`tests/e2e/`). Real apps, real D-Bus. |
| `make test-atspi` | Yes | AT-SPI smoke tests only (`-k atspi`). |
| `make lint` | No | Runs on host: `basedpyright src/` + `ruff check src/ tests/`. |

To run specific tests or markers inside the VM:

```bash
# Via make + vm run:
uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/unit/ -v"
uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/test_bridge_e2e.py -v"
uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest -m unit -v"

# If already SSH'd into the VM:
cd /vagrant && uv run pytest tests/unit/ -v
cd /vagrant && uv run pytest -k "test_tray" -v
```

PySide6 is not in the host venv. Running `pytest` on the host crashes because pytest-qt tries to import PySide6. All tests must run in the VM.

## Test architecture

### Directory structure

```
tests/
  conftest.py           # Root conftest (minimal — just imports)
  test_main.py          # pytest-qt tests for the sample app (offscreen)
  unit/                 # Pure logic tests, no external deps
    test_atspi.py       # AtspiNode wrapper (mocked gi bindings)
    test_models.py      # Extents, WidgetInfo data types
    test_bridge_*.py    # Bridge protocol, eval, client, server
    test_clipboard.py   # Clipboard module (mocked subprocess)
    test_tray.py        # Tray module (mocked D-Bus)
    test_notify.py      # Notification module (mocked)
    test_audio.py       # Audio module (mocked)
    test_file_dialog.py # File dialog module (mocked)
    test_installer.py   # Shadcn installer logic
    test_workspace.py   # Workspace template rendering
    test_vm.py          # VM lifecycle commands
    ...
  integration/          # CLI integration tests (require DISPLAY)
    test_cli.py         # CLI commands via subprocess
    test_cli_errors.py  # CLI error handling
  e2e/                  # End-to-end: real apps, real AT-SPI, real D-Bus
    conftest.py         # App lifecycle fixtures (module-scoped)
    test_bridge_e2e.py  # Bridge eval against running app
    test_tray_e2e.py    # Tray + notification via D-Bus
    test_clipboard_e2e.py
    test_file_dialog_e2e.py
    test_compound_e2e.py
    test_audio_e2e.py
    test_stt_e2e.py
    test_bridge_proxy.py
  apps/                 # Test subject PySide6 apps
    tray_app.py         # System tray + notifications
    file_dialog_app.py  # QFileDialog automation target
    audio_app.py        # Audio recording/playback
    stt_app.py          # Speech-to-text test app
```

### Test tiers and markers

- **`unit`** — Pure logic, no external dependencies. Mocked subprocess/D-Bus/AT-SPI. Runs anywhere.
- **`integration`** — CLI commands via subprocess. Requires DISPLAY (AT-SPI). Runs in VM.
- **`e2e`** — Real PySide6 apps with bridge, AT-SPI, D-Bus, xdotool. Requires full VM environment.

Markers are defined in `pyproject.toml` under `[tool.pytest.ini_options]`. The e2e and integration directories apply their markers via module-level `pytestmark`.

Timeout: `timeout = 30` (seconds) configured in `pyproject.toml`. Requires `pytest-timeout` plugin (installed in VM venv via `uv sync`).

## VM test environment

### Provisioning (from `provision.sh.j2`)

1. **System deps**: Xvfb, xdotool, scrot, openbox, AT-SPI, D-Bus, stalonetray, snixembed, dunst, PipeWire, sox, ffmpeg, xclip, xsel
2. **Python system packages**: PySide6 installed via `pip3 --break-system-packages`
3. **uv installed** at `/opt/uv/`, symlinked to `/usr/local/bin/uv`
4. **Project venv** at `~/.venv-qt-ai-dev-tools`, created via `uv sync --project /vagrant`
5. **System-only packages symlinked** into venv: `gi`, `pygtkcompat`, `_gi*.so` (not pip-installable)
6. **PySide6** is in both system Python (for apps) and venv (via system site-packages or pip)
7. **Desktop session** systemd user service: openbox + AT-SPI + snixembed + stalonetray + dunst + PipeWire

### Environment variables (set in `.bashrc`)

```
DISPLAY=:99
QT_QPA_PLATFORM=xcb
QT_ACCESSIBILITY=1
QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
QT_AI_DEV_TOOLS_VM=1
QT_AI_DEV_TOOLS_BRIDGE=1
UV_PROJECT_ENVIRONMENT=$HOME/.venv-qt-ai-dev-tools
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
```

`UV_PROJECT_ENVIRONMENT` tells `uv run` to use the venv outside `/vagrant`, so `uv run pytest` picks up all dev deps plus the symlinked system packages.

## E2E test infrastructure

### App fixture lifecycle

All app fixtures in `tests/e2e/conftest.py` are **module-scoped** (one app process shared across all tests in a module). The pattern:

1. `_clean_stale_sockets()` — remove leftover bridge sockets
2. `_start_app(path, bridge=True)` — launch app subprocess with env vars (DISPLAY, QT_QPA_PLATFORM, QT_ACCESSIBILITY, QT_AI_DEV_TOOLS_BRIDGE)
3. `_wait_for_app_window(proc, search_term)` — poll AT-SPI apps list and widget tree until the app appears (timeout: 25s)
4. `yield proc` — tests run
5. `_kill_app(proc)` — SIGKILL + wait

### Bridge socket discovery

```python
from qt_ai_dev_tools.bridge._client import find_bridge_socket, eval_code

sock = find_bridge_socket(pid=proc.pid)  # or find_bridge_socket() for any
resp = eval_code(sock, "widgets['status_label'].text()")
```

Sockets live at `/tmp/qt-ai-dev-tools-bridge-<pid>.sock`. `_clean_stale_sockets()` removes them before each fixture starts.

### AT-SPI app name vs window title

AT-SPI application names are the **script filename** (e.g., `tray_app.py`), not the window title (e.g., "Tray Test App"). The `_wait_for_app_window` helper searches both app names and the widget tree, but fixtures must pass the right search term. The `tray_app` fixture uses `"tray_app.py"` (script name), not `"Tray Test App"`.

### Tray-specific fixtures

The tray subsystem requires extra setup because of the SNI-to-XEmbed proxy chain:

**`clean_sni_watcher`** (module-scoped):
- Ensures stalonetray is running (starts it if missing, does NOT restart — avoids XEmbed timing issues)
- Always kills and restarts snixembed to clear stale SNI entries
- Why restart snixembed: its `name-vanished` callback doesn't reliably fire for unique D-Bus names, so old entries persist

**`tray_app`** depends on `clean_sni_watcher`, then:
1. Starts `tests/apps/tray_app.py`
2. Waits for AT-SPI visibility (by script name `"tray_app.py"`)
3. Calls `_wait_for_tray_embedding("tray_app")` — polls `xwininfo -tree` on the stalonetray window until a child with matching WM_CLASS appears

**Why `_wait_for_tray_embedding` matters**: SNI registration (D-Bus) is instant, but XEmbed embedding (X11 window reparenting via snixembed) takes time. Without this wait, xdotool clicks on the tray icon fail because the icon isn't yet a child window of stalonetray.

### Test ordering within modules

Tests within a module run in file order (class by class, method by method). All tests sharing a module-scoped fixture share the same app process. Destructive tests (like `TestTraySelect` which crashes the app via D-Bus thread-safety issue) must be last in the file.

## Known issues and lessons learned

- **tray.select() crashes PySide6 apps**: The D-Bus `Event` method triggers a Qt menu action on a non-main thread, causing a segfault. The original bug was wrong D-Bus menu item IDs (sequential 0,1,2 instead of actual IDs from `GetLayout`). The crash is a separate PySide6 thread-safety issue.
- **Stale SNI entries**: snixembed doesn't reliably detect when an SNI client disappears (unique D-Bus name watcher issue). Restarting snixembed is the only reliable cleanup.
- **PySide6 not in host venv**: pytest-qt import fails on the host. All tests must run in the VM.
- **Bridge blocked by modal dialogs**: QFileDialog, QMessageBox block the Qt event loop. The bridge socket server can't respond while a modal is open. Use AT-SPI/xdotool for dialog interaction.
- **xdotool needs openbox**: Without a window manager, xdotool coordinates are wrong (windows have no decoration/position management).
- **`pytest-timeout`**: Configured in pyproject.toml (`timeout = 30`) but requires the plugin, which is installed in the VM venv via `uv sync`.

## Writing new e2e tests

### Adding a new test app

1. Create the app in `tests/apps/your_app.py`
2. Give it an `objectName` on the main window for bridge access
3. If using the bridge: call `bridge.start()` before `app.exec()`
4. Set `QT_AI_DEV_TOOLS_BRIDGE=1` guard (see existing apps for pattern)

### Adding a fixture

In `tests/e2e/conftest.py`:

```python
@pytest.fixture(scope="module")
def your_app() -> Generator[subprocess.Popen[str], None, None]:
    app_path = _APPS_DIR / "your_app.py"
    proc = _start_app(app_path, bridge=True)
    _wait_for_app_window(proc, "your_app.py")  # AT-SPI script name
    yield proc
    _kill_app(proc)
```

### Access patterns

**Bridge eval** (read/write widget state programmatically):
```python
from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

sock = find_bridge_socket(pid=your_app.pid)
resp = eval_code(sock, "widgets['my_widget'].text()")
assert resp.ok is True
```

**AT-SPI/CLI** (external inspection, as an agent would):
```python
result = subprocess.run(
    ["python3", "-m", "qt_ai_dev_tools", "find", "--role", "push button"],
    capture_output=True, text=True, timeout=5, check=False,
)
```

**Tray tests**: Always depend on `clean_sni_watcher` fixture and call `_wait_for_tray_embedding()` after app startup.

### Module-level skip guard

Every e2e test file needs:
```python
pytestmark = [
    pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="..."),
    pytest.mark.e2e,
]
```
