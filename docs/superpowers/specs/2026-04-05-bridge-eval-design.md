# Bridge Eval Design Exploration

**Date:** 2026-04-05
**Status:** Research / Design exploration
**Author:** AI agent (Claude)

---

## The Gap

qt-ai-dev-tools gives AI agents Chrome DevTools-like inspection and interaction for Qt apps:
AT-SPI for the widget tree, xdotool for clicks and typing, scrot for screenshots. But AT-SPI
only exposes the accessibility layer — roles, names, bounding boxes, and a limited set of
text/action interfaces. There is a whole world of widget state, application logic, and Qt
internals that AT-SPI simply cannot reach.

Chrome DevTools MCP has `evaluate_script` — agents can run arbitrary JavaScript inside the
page, access the DOM, read hidden state, call application functions, manipulate widgets
programmatically. We want the Python/Qt equivalent: a bridge that lets agents execute
arbitrary Python code inside a running Qt app's process.

This document captures research findings, design ideas, and open questions. It is not a
final spec.

---

## Use Cases

These are the scenarios that motivate the bridge, with Chrome DevTools JS equivalents
alongside the Python/Qt equivalents.

### A. Reading hidden state

AT-SPI exposes labels and roles, but not widget properties, stylesheets, dynamic properties,
or custom data attributes.

```javascript
// Chrome DevTools: read a data attribute
el.dataset.errorCode
```

```python
# Qt bridge: read a dynamic property
app.findChild(QWidget, "status").property("errorCode")
```

### B. Widget manipulation beyond click/type

Some widget interactions are painful or impossible via AT-SPI + xdotool: selecting combo box
items by value (not coordinate), scrolling to specific positions, expanding tree nodes,
toggling checkboxes programmatically.

```javascript
// Chrome DevTools: set a select value
select.value = 'JP'
```

```python
# Qt bridge: set combo box by text
combo = app.findChild(QComboBox, "country")
combo.setCurrentIndex(combo.findText("Japan"))
```

### C. Access application models

AT-SPI shows what is rendered in the view. The underlying `QAbstractItemModel` may have
hundreds of rows, complex data roles, or hierarchical structure that the accessibility
layer flattens or truncates.

```javascript
// Chrome DevTools: read table data
Array.from(document.querySelectorAll('tr')).map(r => r.textContent)
```

```python
# Qt bridge: read model data directly
model = app.findChild(QTableView, "orders").model()
[model.data(model.index(row, 0)) for row in range(model.rowCount())]
```

### D. Trigger application logic

Skip multi-step UI workflows by calling controller methods directly. Reset state between
test runs. Invoke business logic that has no UI surface.

```javascript
// Chrome DevTools: call app method
window.app.resetState()
```

```python
# Qt bridge: call a controller method
app.findChild(QObject, "ctrl").resetState()
```

### E. Find widgets by Qt class and objectName

AT-SPI reports "push button" for both `QPushButton` and `QToolButton`. It cannot
distinguish `QLineEdit` in normal mode from password mode. The bridge gives access to
the full Qt class hierarchy.

```javascript
// Chrome DevTools: query by attribute
document.querySelectorAll('input[type=password]')
```

```python
# Qt bridge: find password fields by echo mode
[w for w in app.findChildren(QLineEdit) if w.echoMode() == QLineEdit.EchoMode.Password]
```

### F. Verify internal state

Check the data layer, not just what the UI label says. The label might say "5 orders"
but the actual model might have 4 (rendering bug). The bridge lets agents verify truth.

```javascript
// Chrome DevTools: check app state
assert(app.orders.length === 5)
```

```python
# Qt bridge: check controller property
ctrl = app.findChild(QObject, "ctrl")
ctrl.property("orderCount")
```

---

## Two Engines, Same Bridge

There are two ways to start the bridge inside the target app. The key insight is that
they share the same protocol, eval engine, and client — the only difference is how the
bridge process gets bootstrapped.

### 1. App-installed bridge (any Python version)

The app explicitly starts the bridge. Works with any Python version.

```python
# In the target app's startup code:
from qt_ai_dev_tools.bridge import start
start()
```

This starts a Unix socket server on a daemon thread. Code execution requests arrive over
the socket and get dispatched to the Qt main thread via
`QMetaObject.invokeMethod` with `Qt.ConnectionType.BlockingQueuedConnection`.

**Pros:** Works with any Python. App developer has full control over when/if bridge starts.
**Cons:** Requires modifying the target app's source code.

### 2. sys.remote_exec injection (Python 3.14+, PEP 768)

Python 3.14 introduced `sys.remote_exec(pid, script_path)` — it injects a Python script
into a running process without any prior instrumentation. The script runs on the main
thread at the next bytecode checkpoint.

```python
# From the agent/CLI side:
import sys
sys.remote_exec(target_pid, "/tmp/qt-ai-dev-tools-bootstrap-1234.py")
```

**Important characteristics of sys.remote_exec:**

- Fire-and-forget: no return value, no way to know when execution completes
- Script runs on the main thread at the next safe point (bytecode eval breaker check)
- The target process must be running Python 3.14+
- Requires appropriate OS permissions (same user, or CAP_SYS_PTRACE)

Since it is fire-and-forget, we use it purely as a delivery mechanism: the injected script
bootstraps the same socket server that approach 1 uses. After injection, the CLI polls
for the socket file to appear.

**Pros:** Zero modification to the target app. True "attach to any Qt app" capability.
**Cons:** Python 3.14+ only. Requires OS-level permissions. No feedback on injection success.

### Priority

Use `sys.remote_exec` as the primary method when the target runs Python 3.14+. Fall back
to requiring the app-installed bridge for older Python versions. Both paths converge on
the same socket server and protocol — the agent experience is identical once connected.

---

## CLI API Design

### eval command

The most common agent interaction — execute Python code inside the running app.

```bash
# Inline expression (most common for agents)
qt-ai-dev-tools eval "app.findChild(QComboBox, 'country').currentText()"

# Inline statement
qt-ai-dev-tools eval "combo = widgets['country']; combo.setCurrentIndex(0)"

# Execute from file (avoids shell escaping, good for multi-line scripts)
qt-ai-dev-tools eval --file /path/to/script.py

# Execute from stdin (pipe-friendly, good for generated code)
echo "print(app.windowTitle())" | qt-ai-dev-tools eval --file -

# Target a specific app by PID
qt-ai-dev-tools eval --pid 1234 "app.windowTitle()"

# JSON output (default for agents, human-readable otherwise)
qt-ai-dev-tools eval --json "widgets.keys()"
```

### bridge command

Manage the bridge lifecycle explicitly when needed.

```bash
# Check if a bridge is running, show connection info
qt-ai-dev-tools bridge status

# Inject bridge into a running process (Python 3.14+ only)
qt-ai-dev-tools bridge inject --pid 1234

# Inject with auto-discovery (find the Qt app process)
qt-ai-dev-tools bridge inject
```

---

## Bridge Detection Flow

The `eval` command should handle connection automatically. The agent should not need to
think about bridge lifecycle in the common case.

### Step 1: Find the socket

Look for Unix sockets at the predictable path pattern:

```
/tmp/qt-ai-dev-tools-bridge-<pid>.sock
```

If `--pid` is provided, check that specific socket. Otherwise, scan for any active bridge
socket (`/tmp/qt-ai-dev-tools-bridge-*.sock`). If exactly one exists, use it. If multiple
exist, fail with a list and ask the agent to specify `--pid`.

### Step 2: Socket found — connect and execute

Connect, send the code, read the response. Fast path, no ceremony.

### Step 3: No socket found — attempt injection

Check if the target process is Python 3.14+:

- **Yes:** Auto-inject the bridge via `sys.remote_exec`. Poll for the socket to appear
  (timeout: 5 seconds, poll interval: 100ms). Once it appears, connect and execute.

- **No:** Fail fast with an actionable error message:

```
Error: No bridge found for PID 1234.

Target app is Python 3.13 -- automatic injection requires Python 3.14+.

Add this to your app to enable the bridge:
  from qt_ai_dev_tools.bridge import start; start()

Or set QT_AI_DEV_TOOLS_BRIDGE=1 if bridge.start() is already in the code
but not activated.
```

### Step 4: Socket exists but unresponsive

```
Error: Bridge at /tmp/qt-ai-dev-tools-bridge-1234.sock not responding
(timeout 5s). The app may be frozen or the bridge crashed.
```

### Design rationale

This flow follows the fail-fast philosophy: detect problems at the earliest possible moment,
and when something fails, the error message itself contains the fix. The agent never gets
a generic "connection refused" — it gets a diagnosis and a remedy.

---

## Dev Mode Enforcement

The bridge gives full code execution access to the target app. It must only run in
development/testing environments.

### Environment variable gate

`bridge.start()` checks for `QT_AI_DEV_TOOLS_BRIDGE=1` in the environment. Without it,
the function is a no-op (or raises with a clear message, TBD — no-op is probably better
for library code that conditionally enables the bridge).

```python
def start() -> None:
    """Start the bridge server if QT_AI_DEV_TOOLS_BRIDGE=1 is set."""
    if os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") != "1":
        return
    _start_server()
```

### Force bypass

For tests and scripts that explicitly want the bridge regardless of env:

```python
def start(*, force: bool = False) -> None:
    if not force and os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") != "1":
        return
    _start_server()
```

The `sys.remote_exec` injection path uses `_start_server(force=True)` directly — the
act of injecting implies consent.

### Startup logging

When the bridge starts, it logs clearly:

```
qt-ai-dev-tools bridge active on /tmp/qt-ai-dev-tools-bridge-1234.sock (DEV MODE)
```

### VM environment

The `provision.sh` template should set `QT_AI_DEV_TOOLS_BRIDGE=1` in the VM environment
by default. The VM is inherently a dev/test environment — no reason to require manual
activation there.

---

## Result Format

Rich JSON responses designed for agent consumption. The format uses `ok` as a discriminator
for success/failure — agents can pattern match on this field.

### Success with return value

```json
{
  "ok": true,
  "result": "Japan",
  "type": "str",
  "stdout": "",
  "duration_ms": 2
}
```

### Success with no return value (exec mode)

```json
{
  "ok": true,
  "result": null,
  "type": "NoneType",
  "stdout": "printed output here\n",
  "duration_ms": 5
}
```

### Error

```json
{
  "ok": false,
  "error": "AttributeError: 'NoneType' object has no attribute 'currentText'",
  "traceback": "Traceback (most recent call last):\n  File \"<eval>\", line 1, in <module>\nAttributeError: ...",
  "duration_ms": 1
}
```

### eval/exec fallback behavior

The eval engine tries `eval()` first (expression that produces a value), then falls back
to `exec()` (statements, no return value but captures stdout). This matches Python REPL
behavior and means agents do not need to think about the distinction.

```python
def execute(code: str, namespace: dict[str, object]) -> EvalResult:
    try:
        result = eval(code, namespace)
        return EvalResult(ok=True, result=repr(result), type_name=type(result).__name__)
    except SyntaxError:
        pass  # not an expression, try exec

    stdout_capture = io.StringIO()
    with contextlib.redirect_stdout(stdout_capture):
        exec(code, namespace)
    return EvalResult(ok=True, result=None, type_name="NoneType", stdout=stdout_capture.getvalue())
```

### Serialization

Return values are `repr()`-ed, not JSON-serialized. This avoids the problem of
non-serializable Qt objects — `repr()` always works. For structured data, the agent
can use `json.dumps()` inside the eval code:

```bash
qt-ai-dev-tools eval "import json; json.dumps([w.objectName() for w in app.allWidgets() if w.objectName()])"
```

Open question: should we attempt `json.dumps()` first and fall back to `repr()`? This
would give agents structured data when possible. But it adds complexity and might be
surprising when serialization silently changes format. Leaning toward `repr()` only, with
the agent using explicit `json.dumps()` when needed.

---

## Pre-populated Namespace

Every eval call gets a namespace with helpful shortcuts. The goal is to minimize boilerplate
for common agent tasks.

### Always available

| Name | Value | Purpose |
|------|-------|---------|
| `app` | `QApplication.instance()` | The application instance |
| `widgets` | `{w.objectName(): w for w in app.allWidgets() if w.objectName()}` | Dict of named widgets |
| `find(type, name)` | `app.findChild(type, name)` | Find single child by type and name |
| `findall(type)` | `app.findChildren(type)` | Find all children by type |
| `_` | Result of previous eval | REPL convention |

### Pre-imported Qt classes

All commonly used PySide6 widget and core classes:

```python
# QtWidgets
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QRadioButton, QLabel, QTextEdit, QPlainTextEdit, QSpinBox,
    QDoubleSpinBox, QSlider, QProgressBar, QTabWidget, QTableView,
    QTreeView, QListView, QGroupBox, QMenuBar, QToolBar, QStatusBar,
    QDialog, QMainWindow, QDockWidget, QScrollArea, QStackedWidget,
)

# QtCore
from PySide6.QtCore import Qt, QObject, QTimer, QModelIndex
```

### Design note on `widgets`

The `widgets` dict is rebuilt on every eval call to reflect current state. This is cheap
(iterating `allWidgets()` is fast) and avoids stale references. Named widgets are the
most common lookup pattern for agents — `widgets["saveButton"].click()` is much nicer
than `app.findChild(QPushButton, "saveButton").click()`.

### The `_` variable

Persisted across eval calls within the same bridge session. Enables REPL-style workflows:

```bash
qt-ai-dev-tools eval "find(QComboBox, 'country')"
# _ is now the QComboBox
qt-ai-dev-tools eval "_.currentText()"
# returns "United States"
```

Open question: should the namespace persist entirely across calls (accumulating variables),
or reset each time (only `_` carries over)? Persistent namespace enables multi-step
scripts. Reset namespace avoids memory leaks and stale state. Leaning toward persistent
with a `--fresh` flag to reset.

---

## Architecture

### Module structure

```
src/qt_ai_dev_tools/
    bridge.py           # or bridge/ package if it grows
    bridge_client.py    # client-side socket connection (used by CLI)
```

If the bridge grows complex enough (protocol, server, client, namespace, bootstrap),
promote to a package:

```
src/qt_ai_dev_tools/bridge/
    __init__.py         # public API: start(), start_server()
    _server.py          # Unix socket server, runs in target app
    _client.py          # Socket client, used by CLI
    _eval.py            # eval/exec engine, namespace management
    _protocol.py        # message format, serialization
    _bootstrap.py       # sys.remote_exec bootstrap script generation
```

### Server (runs inside target app)

- Daemon thread running a Unix domain socket server
- Accepts connections, reads newline-delimited JSON requests
- Dispatches code execution to Qt main thread via `QMetaObject.invokeMethod`
  with `Qt.ConnectionType.BlockingQueuedConnection`
- Returns JSON response over the socket

Why `BlockingQueuedConnection`? The socket server thread needs to wait for the result.
`QueuedConnection` would be async (fire-and-forget). `BlockingQueuedConnection` blocks
the calling thread until the slot completes on the main thread, giving us synchronous
request-response semantics.

### Client (runs in CLI process)

- Connects to Unix domain socket
- Sends request as newline-delimited JSON: `{"code": "...", "mode": "auto"}`
- Reads response: the result format described above
- Handles timeouts, connection errors

### Protocol

Newline-delimited JSON over Unix domain socket. Simple, debuggable, no dependencies.

Request:

```json
{"code": "app.windowTitle()", "mode": "auto"}
```

Mode options:
- `"auto"` — try eval, fall back to exec (default)
- `"eval"` — expression only, error if not an expression
- `"exec"` — statement only, no return value

Response: the result format described in the Result Format section.

### Why Unix domain sockets?

- **No network exposure.** TCP sockets would require binding to an address, firewall
  considerations, auth tokens. Unix sockets inherit filesystem permissions.
- **Fast.** No TCP overhead, no serialization beyond our JSON messages.
- **Discoverable.** Socket path is predictable from PID: `/tmp/qt-ai-dev-tools-bridge-<pid>.sock`.
- **Cleanup.** Socket file is deleted on bridge shutdown. Stale sockets can be detected
  (connect attempt fails).

---

## sys.remote_exec Bootstrap

When injecting via `sys.remote_exec`, the CLI generates a temporary bootstrap script:

```python
# /tmp/qt-ai-dev-tools-bootstrap-<pid>.py
# Injected into target process via sys.remote_exec() (Python 3.14+, PEP 768)
import sys
sys.path.insert(0, "/path/to/qt-ai-dev-tools/src")
from qt_ai_dev_tools.bridge import _start_server
_start_server()  # bypass env var check -- injection implies consent
```

### Bootstrap flow

1. CLI determines the target PID (from `--pid` flag or auto-discovery)
2. CLI checks target Python version (read `/proc/<pid>/exe`, check version)
3. CLI writes bootstrap script to `/tmp/qt-ai-dev-tools-bootstrap-<pid>.py`
4. CLI calls `sys.remote_exec(pid, bootstrap_path)`
5. CLI polls for `/tmp/qt-ai-dev-tools-bridge-<pid>.sock` (timeout 5s, interval 100ms)
6. Socket appears — CLI connects and proceeds with eval
7. Cleanup: delete bootstrap script (socket persists for future calls)

### Detecting target Python version

To check if the target supports `sys.remote_exec`:

```bash
# Read the Python binary from /proc
readlink /proc/<pid>/exe
# e.g., /usr/bin/python3.14

# Or check version
/proc/<pid>/exe --version 2>&1
# Python 3.14.0
```

This can also be done from Python using `/proc/<pid>/exe` symlink resolution.

### Permissions

`sys.remote_exec` requires that the calling process has permission to ptrace the target.
On most Linux systems this means:
- Same user (most common in dev environments)
- Root
- `CAP_SYS_PTRACE` capability
- `/proc/sys/kernel/yama/ptrace_scope` set to 0

The VM environment should ensure ptrace_scope is permissive. The provision.sh template
should set `kernel.yama.ptrace_scope=0` if needed.

---

## Thread Safety Considerations

This is the trickiest part of the design. Qt widgets must only be accessed from the main
thread. The bridge server runs on a background thread. Every eval request must be
marshaled to the main thread.

### QMetaObject.invokeMethod approach

```python
class BridgeExecutor(QObject):
    """Lives on the main thread, executes eval requests."""

    def __init__(self) -> None:
        super().__init__()
        self._result: EvalResult | None = None

    @Slot(str)
    def execute(self, code: str) -> None:
        """Called on the main thread via BlockingQueuedConnection."""
        self._result = _run_eval(code, self._namespace)
```

From the server thread:

```python
QMetaObject.invokeMethod(
    executor,
    "execute",
    Qt.ConnectionType.BlockingQueuedConnection,
    Q_ARG(str, code),
)
result = executor._result
```

### Deadlock risk

`BlockingQueuedConnection` blocks the calling thread until the main thread processes the
event. If the main thread is blocked (modal dialog, long computation, frozen app), the
eval request will hang indefinitely.

Mitigation: timeout on the client side (default 30s). The bridge server itself should
also have a timeout — if `invokeMethod` does not return within N seconds, return an
error response rather than blocking forever. This may require a secondary mechanism
(timer on the server thread that checks if the main thread responded).

Open question: is there a cleaner way to do this? Could use `QTimer.singleShot(0, ...)` on
the main thread with a `threading.Event` for synchronization, but that is essentially
reimplementing `BlockingQueuedConnection`.

### Re-entrancy

If the eval code itself triggers event processing (e.g., `QApplication.processEvents()`,
modal dialogs), and there is another eval request queued, we could get re-entrant
execution. The bridge should serialize requests — only one eval at a time, enforced by
a lock on the server side.

---

## Documentation Plan

### docs/bridge-guide.md

Full guide covering:
- What the bridge is and why you need it
- Setup: app-installed vs. injection
- CLI usage with examples
- Security notes (dev mode only, Unix socket permissions)
- Troubleshooting (common errors, socket cleanup)
- Namespace reference (pre-populated variables and imports)

### CLI inline help

`qt-ai-dev-tools eval --help` should include a brief "Bridge required" note:

```
Execute Python code inside a running Qt app.

Requires an active bridge. Start one by adding to your app:
  from qt_ai_dev_tools.bridge import start; start()

Or inject into a running Python 3.14+ app:
  qt-ai-dev-tools bridge inject --pid <PID>
```

### Error messages as documentation

Every error message from the bridge detection flow (see above) contains the diagnosis
and the fix. The agent should never need to consult external docs to recover from a
bridge connection failure.

### Skills update

The `qt-widget-patterns` skill should be updated to include eval-based recipes alongside
AT-SPI ones. For example, "find all password fields" could show both the AT-SPI approach
(filter by role and attributes) and the bridge approach (`findChildren(QLineEdit)` with
echo mode check).

### Sample app

`app/main.py` should demonstrate bridge integration:

```python
from qt_ai_dev_tools.bridge import start

def main() -> None:
    app = QApplication(sys.argv)
    # ... setup widgets ...

    # Enable bridge in dev mode (requires QT_AI_DEV_TOOLS_BRIDGE=1)
    start()

    sys.exit(app.exec())
```

---

## Open Questions

### 1. Namespace persistence

Should the eval namespace persist across calls? Persistent namespace enables multi-step
workflows (`x = find(QComboBox, 'country')` then `x.setCurrentIndex(3)`). But it
accumulates state and can lead to stale widget references.

**Current leaning:** Persist by default, offer `--fresh` flag. Stale references are the
agent's problem — same as in Chrome DevTools where `$0` can become stale.

### 2. Return value serialization

`repr()` is safe and universal but not structured. `json.dumps()` gives structured data
but fails on most Qt objects.

**Current leaning:** `repr()` by default. The agent can use `json.dumps()` explicitly
inside eval code when it needs structured output.

### 3. Binary/large data

What happens when the agent evals something that returns a large object (e.g., screenshot
bytes, model with 10k rows)? `repr()` of large objects is unwieldy.

**Current leaning:** Truncate `repr()` output at a reasonable limit (e.g., 64KB) with a
note: `"[truncated, 245KB total]"`. For intentionally large data, the agent should write
to a file inside the eval code.

### 4. Multiple Qt apps

If multiple Qt apps are running in the VM, the agent needs to target a specific one.
Auto-discovery should list all bridge sockets and let the agent choose.

**Current leaning:** `qt-ai-dev-tools bridge status` lists all active bridges. `eval`
auto-connects if exactly one bridge exists, requires `--pid` if multiple exist.

### 5. Bridge lifecycle

Should the bridge auto-shutdown? Or persist until the app exits?

**Current leaning:** Persist until app exit. The daemon thread dies with the process.
Socket file gets cleaned up via `atexit` handler. Stale socket files (app crashed) are
detected by failed connect attempts and can be cleaned up by the CLI.

### 6. Security beyond env var

Is the env var gate sufficient? The Unix socket already provides filesystem-level
permission control (only same-user can connect). In the VM environment, security is
minimal concern. For future host/container usage, we might want a shared secret or
token — but that is over-engineering for current needs.

**Current leaning:** Env var gate + Unix socket permissions. Revisit for Phase 8
(host/container support).

### 7. Async eval

Should the bridge support `await` expressions? Some Qt operations are async (network
requests via QNetworkAccessManager, async slots). Supporting async eval would require
running an event loop iteration or using `qasync`.

**Current leaning:** Not for v1. Synchronous eval covers 95% of use cases. Async can be
added later if needed.

---

## Relationship to Existing Commands

The bridge does not replace AT-SPI-based commands — it complements them.

| Task | AT-SPI (existing) | Bridge (new) |
|------|-------------------|--------------|
| Find visible widgets | `qt-ai-dev-tools find` | `eval "findall(QPushButton)"` |
| Click a button | `qt-ai-dev-tools click` | `eval "widgets['save'].click()"` |
| Read label text | `qt-ai-dev-tools find --role label` | `eval "widgets['status'].text()"` |
| Type text | `qt-ai-dev-tools type "hello"` | `eval "widgets['input'].setText('hello')"` |
| Read hidden property | Not possible | `eval "widgets['x'].property('errorCode')"` |
| Access model data | Not possible | `eval "model.data(model.index(0, 0))"` |
| Call app method | Not possible | `eval "ctrl.resetState()"` |
| Screenshot | `qt-ai-dev-tools screenshot` | Not applicable (use existing) |

AT-SPI commands are simpler, more declarative, and work without any bridge setup. The
bridge is for when AT-SPI is not enough. The `qt-widget-patterns` skill should guide
agents on when to use which approach.

---

## Implementation Sketch

This is not a detailed implementation plan — just enough to validate that the design
is feasible.

### Phase 1: Core bridge (MVP)

1. `bridge.py` — server with Unix socket, eval/exec engine, namespace
2. `bridge_client.py` — client for CLI
3. `cli.py` — add `eval` and `bridge status` commands
4. `app/main.py` — add `bridge.start()` call
5. Dev mode gate (env var check)

### Phase 2: sys.remote_exec injection

1. Bootstrap script generation
2. `bridge inject` CLI command
3. Auto-injection in `eval` when no socket found
4. Python version detection
5. VM provision.sh: set ptrace_scope

### Phase 3: Polish

1. Namespace persistence with `--fresh`
2. Output truncation for large results
3. Multiple bridge discovery
4. Timeout handling and deadlock mitigation
5. Skills and documentation updates

---

## Prior Art

- **Chrome DevTools Protocol** — `Runtime.evaluate` sends JS to the browser. Our bridge
  is the direct equivalent for Qt/Python.
- **PyDev debugger** — attaches to running Python processes, but designed for interactive
  debugging, not programmatic agent use.
- **rpyc** — remote Python call library. More general than we need, and adds a dependency.
  Our protocol is simpler (eval code strings, return JSON).
- **Playwright** — browser automation with `page.evaluate()`. Similar eval-over-protocol
  pattern. Their API design (especially the serialization choices) is worth studying.
- **sys.remote_exec (PEP 768)** — the mechanism that makes zero-setup injection possible.
  Landed in Python 3.14.

---

## Summary

The bridge fills the gap between "inspect the accessibility layer" and "full programmatic
access to the running app." Two bootstrap mechanisms (app-installed and sys.remote_exec)
cover all Python versions. The protocol is simple (JSON over Unix socket), the eval engine
follows REPL conventions (eval then exec), and the namespace is pre-populated for
convenience. Dev mode enforcement via env var keeps production safe.

The biggest design risks are thread safety (main thread dispatch, deadlock) and namespace
management (persistence, stale references). Both are manageable with the approaches
outlined above.

Next step: implement Phase 1 (core bridge MVP) and validate the design against real
agent workflows with the sample todo app.
