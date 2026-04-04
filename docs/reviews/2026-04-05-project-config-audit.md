# Project Configuration Audit — 2026-04-05

Full audit of pyproject.toml, basedpyright, pre-commit, git hooks, test structure, and type safety.

---

## basedpyright — Excellent

- Strict mode, `reportAny=error`, 0 errors across 19 files
- Zero `typing.cast()`, zero raw `Any`
- 80 `type: ignore` comments, all with specific error codes + rationales
- `reportUnnecessaryTypeIgnoreComment=error` prevents dead suppressions
- Relaxations (`reportImplicitStringConcatenation`, `reportUnusedCallResult`, `reportUnnecessaryIsInstance` set to none) are appropriate

## Type-ignore boundaries — Clean architecture, needs doc update

Two isolated boundaries:

1. **AT-SPI** (`_atspi.py`): 24 ignores — typed `AtspiNode` wrapper
2. **PySide6** (bridge modules): 54 ignores — `_qt_namespace.py` (40), `_server.py` (12), `_eval.py` (1), `_protocol.py` (1), `_bootstrap.py` (1)

PySide6 wrapper pattern was investigated and ruled out:

- 48/54 ignores are PySide6 missing stubs (not architecture issues)
- `_qt_namespace.py` must export raw classes for eval() — wrapping defeats purpose
- `_server.py` inherits QObject, uses Signal — can't wrap around
- Only real fix is upstream PySide6 stubs

One fixable: `_bootstrap.py` sys.remote_exec ignore can use `sys.version_info` guard.

**Action:** Update CLAUDE.md to acknowledge bridge as second type-ignore boundary.

## Build system — Correct

- Hatchling build backend, src layout
- Entry point: `qt-ai-dev-tools = "qt_ai_dev_tools.cli:app"`
- Dev deps all present and current

## Ruff — Comprehensive

- Rules: E, F, W, I, N, UP, ASYNC, S, B, A, C4, SIM, PT, PERF, RUF
- Covers black + isort + flake8 + bandit
- Missing `[tool.ruff.lint.isort]` section (runs with defaults — acceptable)

## Pre-commit — Not installed as git hook

- `.pre-commit-config.yaml` exists with ruff check, ruff format, basedpyright, uv-sync
- But `.git/hooks/pre-commit` does not exist — hooks never run on commit
- Missing standard hooks: trailing-whitespace, end-of-file-fixer, check-yaml
- No setup script or `make setup` target

**Action:** Create setup script, add `make setup`, reference in DEVELOPMENT.md.

## Lint scope inconsistency — Minor

- `poe lint_full` runs on `.` (correct, should be default)
- `make lint` runs on `src/ tests/` (inconsistent)

**Action:** Makefile should use `.` to match poe task.

## PEP 561 — Missing py.typed

No `src/qt_ai_dev_tools/py.typed` marker file.

**Action:** Add empty py.typed file.

## Pytest markers — Defined but unused

Markers `unit`, `integration`, `e2e` defined in pyproject.toml but:

- `@pytest.mark.unit` — 0 uses
- `@pytest.mark.integration` — 0 uses
- `@pytest.mark.e2e` — 1 use

**Action:** Apply markers to all existing tests.

## Test structure — Good with gaps

Directory structure is proper (unit/, integration/, e2e/). Test quality is good — real sockets, real filesystems, real Qt widgets.

Coverage gaps (11 modules untested):

- `bridge/_bootstrap.py` (210 LOC) — zero coverage, e2e can't reach (needs 3.14)
- `bridge/_server.py` (204 LOC) — only e2e coverage via real Qt app
- `bridge/_qt_namespace.py` (131 LOC) — only e2e coverage
- `pilot.py` (209 LOC) — find/find_one logic untested
- `interact.py` (56 LOC) — thin wrapper, only focus() has branching
- `screenshot.py` (24 LOC) — thin wrapper, skip
- `state.py` (32 LOC) — trivial delegation, skip

## Test plan — 21 new tests

| File | Tests | Priority |
|------|-------|----------|
| `tests/unit/test_bootstrap.py` | 8 | High — zero coverage, real logic, e2e can't reach |
| `tests/unit/test_pilot.py` | 6 | High — find/find_one edge cases, init retry |
| `tests/unit/test_bridge_server.py` | 5 | Medium — socket protocol without Qt/VM |
| `tests/unit/test_qt_namespace.py` | 1 | Low — PySide6-unavailable fallback only |
| `tests/unit/test_interact.py` | 1 | Low — focus() fallback logic only |

Skip: screenshot.py (5-line wrapper), state.py (delegation to tested AtspiNode).

### test_bootstrap.py (8 tests)

1. `can_remote_exec` returns False on Python < 3.14 (monkeypatch sys.version_info)
2. `detect_python_version` parses valid "Python 3.14.1" output (mock-binary or patch)
3. `detect_python_version` raises for non-existent PID
4. `_write_bootstrap_script` creates file with correct content
5. `wait_for_socket` returns path when socket exists immediately
6. `wait_for_socket` times out when socket never appears
7. `_discover_qt_process` finds process from socket glob
8. `_discover_qt_process` raises when no sockets exist

### test_pilot.py (6 tests)

1. `find` returns matching widgets by role (mock AtspiNode tree)
2. `find` returns matching widgets by name substring
3. `find_one` raises LookupError when 0 matches
4. `find_one` raises LookupError when >1 matches
5. `__init__` raises RuntimeError when app not found (retries=1, delay=0)
6. `dump_tree` produces correct indentation with max_depth

### test_bridge_server.py (5 tests)

1. Start/stop lifecycle: socket file created and cleaned up (mock executor)
2. Valid eval request returns response (real socket)
3. Invalid JSON returns error response
4. Client disconnect mid-read doesn't crash server
5. `stop()` is idempotent

### test_qt_namespace.py (1 test)

1. `build_qt_namespace` returns dict with `_` key when PySide6 unavailable

### test_interact.py (1 test)

1. `focus` falls back to click when SetFocus raises
