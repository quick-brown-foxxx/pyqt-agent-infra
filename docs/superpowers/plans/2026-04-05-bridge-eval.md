# Bridge Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Chrome DevTools `evaluate_script` equivalent for Qt apps -- let AI agents execute arbitrary Python code inside a running Qt/PySide app via a Unix socket bridge.

**Architecture:** Unix domain socket bridge server runs on a daemon thread inside the target Qt app. Code execution requests are dispatched to the Qt main thread via `QMetaObject.invokeMethod` with `BlockingQueuedConnection`. JSON-over-socket protocol. Two bootstrap methods: app-installed (`bridge.start()`) and auto-injected (`sys.remote_exec` for Python 3.14+).

**Tech Stack:** Python 3.12+, PySide6 (QMetaObject, QObject, Slot), stdlib sockets, JSON, threading

---

## File Structure

### New files (bridge package)

```
src/qt_ai_dev_tools/bridge/
    __init__.py         # Public API: start(), stop()
    _protocol.py        # EvalRequest, EvalResponse dataclasses, JSON codec
    _eval.py            # eval/exec engine, namespace builder, stdout capture
    _server.py          # Unix socket server, BridgeExecutor QObject, main-thread dispatch
    _client.py          # Socket client: connect, send code, read response
    _bootstrap.py       # sys.remote_exec bootstrap script generation
```

### Modified files

- `src/qt_ai_dev_tools/cli.py` -- add `eval` command and `bridge` subcommand group
- `app/main.py` -- add `bridge.start()` call
- `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` -- add `QT_AI_DEV_TOOLS_BRIDGE=1` env var

### Test files

```
tests/unit/test_bridge_protocol.py   # EvalRequest/EvalResponse serialization
tests/unit/test_bridge_eval.py       # eval/exec engine, namespace, stdout capture
tests/unit/test_bridge_client.py     # Client socket connection (mock server)
tests/integration/test_bridge.py     # Full bridge lifecycle: start, eval, stop
```

---

## Task 1: Protocol Data Types (`_protocol.py`)

**Files:**
- Create: `src/qt_ai_dev_tools/bridge/__init__.py` (empty, enables package)
- Create: `src/qt_ai_dev_tools/bridge/_protocol.py`
- Test: `tests/unit/test_bridge_protocol.py`

Dataclasses for the JSON wire protocol. No Qt dependency -- pure Python.

### Types

```python
@dataclass(slots=True)
class EvalRequest:
    code: str
    mode: str = "auto"  # "auto" | "eval" | "exec"

@dataclass(slots=True)
class EvalResponse:
    ok: bool
    result: str | None = None
    type_name: str | None = None
    stdout: str = ""
    error: str | None = None
    traceback: str | None = None
    duration_ms: int = 0
```

Plus `encode_request()`, `decode_request()`, `encode_response()`, `decode_response()` functions using `json.dumps`/`json.loads`. Newline-delimited JSON (each message is one line).

---

## Task 2: Eval Engine (`_eval.py`)

**Files:**
- Create: `src/qt_ai_dev_tools/bridge/_eval.py`
- Test: `tests/unit/test_bridge_eval.py`

Pure Python eval/exec engine. No Qt dependency -- receives a namespace dict.

### Functions

- `execute(code: str, namespace: dict[str, object]) -> EvalResponse` -- tries eval first, falls back to exec on SyntaxError. Captures stdout. Catches all exceptions. Uses `repr()` for result serialization. Truncates at 64KB.
- `build_namespace() -> dict[str, object]` -- builds the pre-populated namespace with Qt imports, `app`, `widgets`, `find`, `findall`, `_`. This one needs Qt but is called lazily in the server.

### Key behaviors

- `eval` mode: expression only, error if SyntaxError
- `exec` mode: statement only, captures stdout, result is None
- `auto` mode: try eval, fall back to exec on SyntaxError
- All exceptions caught and returned as EvalResponse with ok=False
- `repr()` output truncated at 64KB with `[truncated, NNkB total]` suffix
- Timing via `time.perf_counter_ns()`

---

## Task 3: Bridge Server (`_server.py`)

**Files:**
- Create: `src/qt_ai_dev_tools/bridge/_server.py`
- Modify: `src/qt_ai_dev_tools/bridge/__init__.py` (add public API)

The Unix socket server that runs inside the target Qt app.

### Components

1. **`BridgeExecutor(QObject)`** -- lives on the main thread. Has a `Slot(str)` method `execute_code` that calls `_eval.execute()`. Stores result for retrieval.

2. **`BridgeServer`** -- daemon thread running `socket.socket(AF_UNIX)` accept loop. On each connection: read line, decode EvalRequest, dispatch to BridgeExecutor via `QMetaObject.invokeMethod` with `BlockingQueuedConnection`, encode EvalResponse, write back.

3. **Socket path:** `/tmp/qt-ai-dev-tools-bridge-{pid}.sock`

4. **Cleanup:** `atexit` handler removes socket file. Server has `stop()` method.

5. **Serialization lock:** `threading.Lock` ensures one eval at a time.

### Public API (`__init__.py`)

```python
def start(*, force: bool = False) -> None:
    """Start bridge server if QT_AI_DEV_TOOLS_BRIDGE=1 (or force=True)."""

def stop() -> None:
    """Stop bridge server and clean up socket."""

def socket_path(pid: int | None = None) -> Path:
    """Return socket path for given PID (default: current process)."""
```

---

## Task 4: Bridge Client (`_client.py`)

**Files:**
- Create: `src/qt_ai_dev_tools/bridge/_client.py`
- Test: `tests/unit/test_bridge_client.py`

Client-side socket connection used by the CLI.

### Functions

- `find_bridge_socket(pid: int | None = None) -> Path | None` -- if pid given, check that specific socket. Otherwise glob `/tmp/qt-ai-dev-tools-bridge-*.sock`, return if exactly one. None if zero, raise if multiple (with list).
- `eval_code(socket_path: Path, code: str, mode: str = "auto", timeout: float = 30.0) -> EvalResponse` -- connect, send request, read response with timeout.
- `bridge_status() -> list[dict[str, object]]` -- list all active bridge sockets with PID info.

---

## Task 5: CLI Commands (`eval`, `bridge`)

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`

### `eval` command

```bash
qt-ai-dev-tools eval "app.windowTitle()"
qt-ai-dev-tools eval --file script.py
qt-ai-dev-tools eval --file -              # stdin
qt-ai-dev-tools eval --pid 1234 "code"
qt-ai-dev-tools eval --json "widgets.keys()"
```

Auto-proxies to VM like other commands. Detection flow:
1. Find socket (by --pid or auto-discover)
2. If found, connect and eval
3. If not found, attempt sys.remote_exec injection (3.14+)
4. If can't inject, fail with setup instructions

### `bridge` subcommand group

```bash
qt-ai-dev-tools bridge status              # list active bridges
qt-ai-dev-tools bridge inject --pid 1234   # inject into process
qt-ai-dev-tools bridge inject              # auto-discover Qt process
```

---

## Task 6: sys.remote_exec Bootstrap (`_bootstrap.py`)

**Files:**
- Create: `src/qt_ai_dev_tools/bridge/_bootstrap.py`

### Functions

- `can_remote_exec() -> bool` -- check if Python 3.14+ (has sys.remote_exec)
- `detect_python_version(pid: int) -> tuple[int, int]` -- read `/proc/{pid}/exe`, run `--version`
- `inject_bridge(pid: int, package_path: str) -> Path` -- write bootstrap script to `/tmp/qt-ai-dev-tools-bootstrap-{pid}.py`, call `sys.remote_exec(pid, path)`, return socket path
- `wait_for_socket(pid: int, timeout: float = 5.0) -> Path` -- poll for socket file

---

## Task 7: Update Sample App and Provisioning

**Files:**
- Modify: `app/main.py` -- add `from qt_ai_dev_tools.bridge import start; start()` before `app.exec()`
- Modify: `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` -- add `QT_AI_DEV_TOOLS_BRIDGE=1` to environment

---

## Task 8: Integration Tests

**Files:**
- Create: `tests/integration/test_bridge.py`

Test the full bridge lifecycle using the sample app (or a minimal Qt app fixture). These tests need PySide6 available.

### Test cases

- Bridge start/stop lifecycle
- Eval expression returns result
- Exec statement captures stdout
- Auto mode fallback
- Error handling (syntax error, runtime error)
- Namespace has `app`, `widgets`, `find`, `findall`
- Namespace persistence across calls (the `_` variable)
- Large output truncation
- Socket cleanup on stop
- Multiple connections sequential

---

## Task 9: Documentation

**Files:**
- Create: `docs/bridge-guide.md`
- Modify: `CLAUDE.md` -- add bridge section to quick orientation and key technical facts
- Modify: `docs/ROADMAP.md` -- update Phase 6.0 status
