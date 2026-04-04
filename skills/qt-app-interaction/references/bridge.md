# Bridge: Runtime Code Execution

The bridge is the Chrome DevTools `evaluate_script` equivalent for Qt apps. It executes arbitrary Python code inside a running Qt/PySide application via a Unix socket, with a pre-populated namespace containing the app instance, named widgets, finder helpers, and common Qt classes. Use it when AT-SPI inspection is insufficient -- reading internal state, calling Qt methods directly, or running multi-step logic inside the app.

## Setup

### App-installed (any Python version)

Add to your app after `QApplication` is created:

```python
from qt_ai_dev_tools.bridge import start
start()
```

Set the env var to enable (no-op without it):

```bash
export QT_AI_DEV_TOOLS_BRIDGE=1
```

### Auto-injected (Python 3.14+ only)

No code changes needed:

```bash
qt-ai-dev-tools bridge inject --pid <PID>
```

## CLI commands

| Command | Description |
|---------|-------------|
| `eval "expression"` | Eval expression, return result |
| `eval "statement"` | Exec statement, return captured stdout |
| `eval --json "code"` | Return result as structured JSON |
| `eval --file script.py` | Eval from file |
| `eval --file -` | Eval from stdin |
| `eval --pid PID "code"` | Target specific app by PID |
| `bridge status` | List active bridge sockets |
| `bridge inject --pid PID` | Inject into running Python 3.14+ app |

## Pre-populated namespace

| Name | Description |
|------|-------------|
| `app` | The running `QApplication` instance |
| `widgets` | `dict[str, QWidget]` -- all widgets with `objectName`, keyed by name |
| `find(type, name)` | `app.findChild(type, name)` -- find one widget |
| `findall(type)` | Find all widgets of given type |
| `_` | Result of the last eval expression |
| `QApplication`, `QWidget`, `QPushButton`, `QLabel`, `QLineEdit`, `QTextEdit`, `QComboBox`, `QCheckBox`, `QRadioButton`, `QSlider`, `QSpinBox` | Common Qt classes |
| `Qt` | Qt constants (e.g., `Qt.AlignCenter`) |

## Common recipes

```bash
# Read a widget property
qt-ai-dev-tools eval "widgets['status_label'].text()"

# Find all buttons
qt-ai-dev-tools eval "findall(QPushButton)"

# Click via Qt API (bypasses xdotool)
qt-ai-dev-tools eval "widgets['save_btn'].click()"

# Multi-line with stdout capture
qt-ai-dev-tools eval "
for btn in findall(QPushButton):
    print(btn.text())
"
```

## Troubleshooting

**"No bridge socket found"** -- App not running, `bridge.start()` not called, or `QT_AI_DEV_TOOLS_BRIDGE=1` not set. Check with `apps`. For inject: requires Python 3.14+.

**"Connection refused" / "Broken pipe"** -- App crashed. Check PID is alive (`kill -0 <pid>`). Delete stale socket: `rm /tmp/qt-ai-dev-tools-bridge-<pid>.sock`.

**Eval errors** -- `NameError`: name not in namespace, check spelling. `AttributeError`: use `eval "dir(widget)"` to inspect. Statements (loops, print) return `None` as result but stdout is captured.

**Bridge inject fails** -- Requires Python 3.14+ (`sys.remote_exec`). For older Python, use app-installed method.
