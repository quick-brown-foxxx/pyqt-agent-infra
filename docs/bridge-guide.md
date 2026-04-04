# Bridge Guide: Runtime Code Execution

The bridge is Chrome DevTools `evaluate_script` for Qt apps. It lets AI agents execute arbitrary Python code inside a running Qt/PySide app via a Unix socket, with a pre-populated namespace containing the app instance, named widgets, finder helpers, and common Qt classes. This enables reading/modifying any widget property, calling any method, and running multi-step logic that would be tedious through AT-SPI alone.

## Quick start (app-installed)

Add two lines to your Qt app:

```python
from qt_ai_dev_tools.bridge import start

# After QApplication is created and widgets are set up:
start()
```

Set the env var to enable the bridge (dev-mode gate):

```bash
export QT_AI_DEV_TOOLS_BRIDGE=1
```

The bridge starts a Unix socket server at `/tmp/qt-ai-dev-tools-bridge-<pid>.sock`. The CLI auto-discovers it.

## CLI usage

### Eval expressions and statements

```bash
# Eval a Python expression -- returns the result
qt-ai-dev-tools eval "app.windowTitle()"

# Access named widgets via the widgets dict
qt-ai-dev-tools eval "widgets['status_label'].text()"

# Find widgets by type
qt-ai-dev-tools eval "findall(QPushButton)"

# Multi-line statements (use exec, not eval)
qt-ai-dev-tools eval "
for btn in findall(QPushButton):
    print(btn.text())
"

# JSON output for structured data
qt-ai-dev-tools eval --json "findall(QPushButton)"

# Eval from a file
qt-ai-dev-tools eval --file script.py

# Eval from stdin
qt-ai-dev-tools eval --file - < script.py

# Target a specific app by PID
qt-ai-dev-tools eval --pid 1234 "app.windowTitle()"
```

### Bridge management

```bash
# List active bridge sockets
qt-ai-dev-tools bridge status

# Inject bridge into a running Python 3.14+ app (no code changes needed)
qt-ai-dev-tools bridge inject --pid 1234
```

## Pre-populated namespace

When code runs inside the bridge, these names are available:

| Name | Type | Description |
|------|------|-------------|
| `app` | `QApplication` | The running QApplication instance (use `widgets['MainWindow']` for the main window) |
| `widgets` | `dict[str, QWidget]` | All widgets with `objectName` set, keyed by name |
| `find(type, name)` | function | `app.findChild(type, name)` — find widget by type and objectName |
| `findall(type)` | function | Find all widgets of given type |
| `_` | `object` | Result of the last eval expression |
| `QApplication` | class | Common Qt classes pre-imported |
| `QWidget` | class | |
| `QPushButton` | class | |
| `QLabel` | class | |
| `QLineEdit` | class | |
| `QTextEdit` | class | |
| `QComboBox` | class | |
| `QCheckBox` | class | |
| `QRadioButton` | class | |
| `QSlider` | class | |
| `QSpinBox` | class | |
| `Qt` | namespace | Qt constants (e.g., `Qt.AlignCenter`) |

## Security

The bridge is gated behind a dev-mode env var for safety:

- **`QT_AI_DEV_TOOLS_BRIDGE=1`** must be set, or `start()` is a no-op. This prevents accidental exposure in production.
- **Unix socket permissions** -- the socket file is created with the process owner's permissions. Only the same user can connect. No network exposure.
- **No authentication** -- anyone with filesystem access to the socket can execute code. This is intentional for dev/test environments. Do not enable in production.
- **VM isolation** -- in the VM-first workflow, the bridge runs inside the Vagrant VM, adding an OS-level isolation boundary.

## Troubleshooting

### "No bridge socket found"

The CLI could not find a socket in `/tmp/qt-ai-dev-tools-bridge-*.sock`.

- Is the app running? Check with `qt-ai-dev-tools apps`.
- Did you call `bridge.start()` in the app?
- Is `QT_AI_DEV_TOOLS_BRIDGE=1` set in the app's environment?
- If using `bridge inject`, is the app running Python 3.14+?

### "Connection refused" or "Broken pipe"

The socket file exists but the app is not listening.

- The app may have crashed. Check if the PID is still alive: `kill -0 <pid>`.
- Stale socket file from a previous run. Delete it: `rm /tmp/qt-ai-dev-tools-bridge-<pid>.sock`.

### Eval returns an error

The bridge returns errors as structured JSON with the exception type and traceback.

- `NameError` -- the name is not in the pre-populated namespace. Check spelling. Custom app classes are not auto-imported; use `find()` or `findall()` instead.
- `AttributeError` -- the widget does not have that method/property. Use `dir(widget)` to inspect.
- Statements (assignments, loops, `print()`) use `exec`, not `eval`. They return `None` as the result but `stdout` is captured and returned.

### Bridge inject fails

`sys.remote_exec` requires Python 3.14+. Check the target app's Python version. For older Python, use the app-installed method (`bridge.start()`).
