# Test Failure Report — 2026-04-05

**Before:** `make test-full` → 43 failed, 16 errors, 256 passed, 4 skipped (127s)
**After:** `make test-full` → 0 failed, 0 errors, 313 passed, 4 skipped (76s) ✅

## Resolution Summary

All 59 failures fixed across 6 root causes. No feature regressions found — all issues were stale tests and VM environment drift. Files changed:

| File | Change |
|---|---|
| `tests/unit/test_vm.py` | Mock `run_command` instead of `subprocess.run` |
| `tests/unit/test_interact.py` | Mock `run_command` instead of `subprocess.run` |
| `tests/unit/test_audio.py` | Mock `run_command` instead of `subprocess.run` |
| `tests/unit/test_bootstrap.py` | Mock `run_command` instead of `subprocess.run` |
| `tests/unit/test_atspi.py` | Mock `Atspi.Text` via `patch.object` on actual module |
| `tests/unit/test_file_dialog.py` | Rewrite tests for keyboard-based accept/cancel |
| `tests/unit/test_workspace.py` | Update default assertions (mac_address, rsync_excludes) |
| `tests/e2e/conftest.py` | Fix fixture search terms (script filename vs window title), add `_ensure_real_atspi` fixture |
| `tests/e2e/test_compound_e2e.py` | Add `--app main.py`, fix AT-SPI names, use fill instead of bridge setText |
| `tests/e2e/test_clipboard_e2e.py` | Use `windowfocus` for reliable keyboard events |
| `tests/e2e/test_file_dialog_e2e.py` | Fix app_name to include `.py` extension |
| `tests/integration/conftest.py` | New: session-scoped sample app fixture |
| `tests/integration/test_cli.py` | Add `--app main.py` to find commands |
| `src/qt_ai_dev_tools/cli.py` | `find` returns exit 0 for no results |
| `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2` | Fix `gi` symlink detection |
| `provision.sh` | Regenerated from template |

---

## Original Analysis

All 59 failures (43 FAILED + 16 ERROR) trace to **3 root causes**. No feature regressions — the source code is correct, but tests and VM environment are stale.

| Root Cause | Tests Affected | Category | Fix Complexity |
|---|---|---|---|
| 1. `subprocess.run` → `subprocess.Popen` mock mismatch | 19 unit tests | Tests stale | Medium — update mock targets |
| 2. Source changes without test updates | 8 unit tests | Tests stale | Easy — update assertions |
| 3. `gi` module not importable in CLI subprocess | 33 e2e/integration | VM environment | Easy — re-provision or fix symlink |
| 4. xdotool keyboard focus issue | 2 e2e | VM environment | Easy — add window focus before key events |

**Total: 62 test issues from just 4 root causes.**

---

## Root Cause 1: `subprocess.run` → `subprocess.Popen` Mock Mismatch (19 tests)

### What happened

Commit `2459fa4` ("fix(cli): add Ctrl+C handling to kill hung subprocesses") rewrote `run_command()` in `src/qt_ai_dev_tools/run.py` from `subprocess.run()` to `subprocess.Popen()` + `proc.communicate()`. This enables proper Ctrl+C handling with process group termination via `start_new_session=True`.

Commit `ef516fd` (14 minutes earlier) had also added stream mode using `subprocess.call()`, which was then also replaced with `Popen` in `2459fa4`.

**Neither commit updated the tests.**

### Why tests fail

All affected tests mock `qt_ai_dev_tools.run.subprocess.run` (or `.call`). Since `run_command()` now calls `subprocess.Popen()`, the mocks have no effect — the real `Popen` executes, tries to run `vagrant`/`xdotool`/`sox`/etc., and fails with `RuntimeError: Command not found`.

### Affected tests

| File | Tests | Old Mock Target |
|---|---|---|
| `tests/unit/test_vm.py` | 8 tests (all) | `subprocess.run`, `subprocess.call` |
| `tests/unit/test_interact.py` | 5 tests | `subprocess.run` |
| `tests/unit/test_audio.py` | 1 test (`test_verify_calls_sox`) | `subprocess.run` |
| `tests/unit/test_bootstrap.py` | 1 test (`test_parse_version_output`) | `subprocess.run` |

### Fix direction

**Option A (recommended):** Mock `qt_ai_dev_tools.run.run_command` directly instead of mocking subprocess internals. This makes tests resilient to future implementation changes.

**Option B:** Change mock targets from `subprocess.run` → `subprocess.Popen` and update return values to mock Popen objects (with `.communicate()`, `.wait()`, `.pid`, `.returncode`).

### Note on philosophy

Per `docs/PHILOSOPHY.md` §5: "Real over mocked. When mocking is necessary, build real-like custom implementations rather than monkey-patching runtime." Option A (mocking `run_command`) is more aligned — it mocks the project's own API boundary rather than stdlib internals.

---

## Root Cause 2: Source Changes Without Test Updates (8 tests)

### 2a. `_atspi.py` — `get_text()` changed to class method call (1 test)

**Commit:** `3993b3b`
**File:** `tests/unit/test_atspi.py::TestGetText::test_returns_text_from_text_iface`

Old code: `iface.get_text(0, iface.get_character_count())`
New code: `Atspi.Text.get_text(iface, 0, Atspi.Text.get_character_count(iface))`

Test mocks the instance method on `text_iface`, but code now calls the class method on the `Atspi` module.

**Fix:** Mock `Atspi.Text.get_text` and `Atspi.Text.get_character_count` instead.

### 2b. `file_dialog.py` — fill/accept/cancel rewritten (6 tests)

**Commit:** `3993b3b`
**File:** `tests/unit/test_file_dialog.py` (TestFill: 2, TestAccept: 2, TestCancel: 2)

Changes:
- `fill()` now calls `_find_dialog_root()` first — MockPilot lacks dialog-role nodes
- `accept()` now presses Enter instead of clicking the Open/Save button
- `cancel()` now presses Escape instead of clicking the Cancel button

| Test | Expects | Actual |
|---|---|---|
| `test_fill_types_path_into_filename_field` | Finds text field directly | `_find_dialog_root()` raises — no dialog node in mock |
| `test_fill_raises_when_no_field` | "No filename text field" error | "No file dialog found" from `_find_dialog_root()` |
| `test_accept_clicks_open_button` | `pilot.clicked` has 1 entry | `accept()` presses Enter, never clicks |
| `test_accept_raises_when_no_button` | `LookupError` raised | `accept()` always succeeds (presses Enter) |
| `test_cancel_clicks_cancel_button` | `pilot.clicked` has 1 entry | `cancel()` presses Escape, never clicks |
| `test_cancel_raises_when_no_button` | `LookupError` raised | `cancel()` always succeeds (presses Escape) |

**Fix:** Rewrite tests:
- Add dialog-role `MockNode` to fixtures
- Assert `pilot.keys_pressed` contains "Return"/"Escape" instead of checking `pilot.clicked`
- Remove "raises when no button" tests (accept/cancel no longer raise)

### 2c. `workspace.py` — default `mac_address` changed (1 test)

**Commit:** `2a387f1`
**File:** `tests/unit/test_workspace.py::TestDefaultConfig::test_returns_expected_defaults`

Test expects `config.mac_address == "52:54:00:AB:CD:EF"`, code returns `""`.

**Fix:** Update assertion to `assert config.mac_address == ""`.

---

## Root Cause 3: `gi` Module Not Importable in CLI Subprocess (33 tests)

### What's happening

When `qt-ai-dev-tools` (or `python3 -m qt_ai_dev_tools`) runs as a **subprocess**, it crashes at:
```
ModuleNotFoundError: No module named 'gi'
```

But tests that import `gi` **directly within the pytest process** work fine (e.g., `test_main.py::test_atspi_accessibility_tree` passes).

### Why it matters

The `gi` (GObject Introspection) module is a system package symlinked into the project venv during VM provisioning. The subprocess likely resolves to a different Python or venv where the symlink is broken.

### Affected tests

| Category | File | Tests |
|---|---|---|
| E2E fixture ERRORs | `test_audio_e2e.py` | 5 |
| E2E fixture ERRORs | `test_file_dialog_e2e.py` | 3 |
| E2E fixture ERRORs | `test_stt_e2e.py` | 3 |
| E2E fixture ERRORs | `test_tray_e2e.py` | 5 |
| E2E failures | `test_compound_e2e.py` | 9 |
| Integration failures | `test_cli.py` | 7 |
| Integration failures | `test_cli_errors.py` | 1 |

All 16 ERRORs are cascade failures — the `_wait_for_app_window` fixture calls `qt-ai-dev-tools apps`/`tree` as a subprocess, which crashes on `gi` import. The app itself starts fine, but the fixture can't detect it.

### Diagnosis steps

```bash
# Inside the VM:
which python3
python3 -c "import gi; print(gi.__file__)"
qt-ai-dev-tools apps  # should fail with ModuleNotFoundError
# Check the entry point shebang:
head -1 $(which qt-ai-dev-tools)
# Check the venv symlinks:
ls -la ~/.venv-qt-ai-dev-tools/lib/python3.12/site-packages/gi
```

### Fix direction

Re-provision the VM (`make destroy && make up`) or manually fix the `gi` symlink:
```bash
# Inside VM:
VENV_SITE=~/.venv-qt-ai-dev-tools/lib/python3.12/site-packages
SYS_SITE=/usr/lib/python3/dist-packages  # or wherever gi lives
ln -sf $SYS_SITE/gi $VENV_SITE/gi
ln -sf $SYS_SITE/pygtkcompat $VENV_SITE/pygtkcompat
ln -sf $SYS_SITE/_gi*.so $VENV_SITE/
```

---

## Root Cause 4: xdotool Keyboard Focus (2 tests)

**File:** `tests/e2e/test_clipboard_e2e.py`

- Test 1: Writes to clipboard via `xsel`, pastes via `xdotool key ctrl+v` — paste doesn't reach the app (field stays empty)
- Test 2: Copies via `xdotool key ctrl+c` — clipboard still has stale value from test 1

**Root cause:** Qt app window may not have keyboard focus when xdotool sends key events.

**Fix:** Add explicit window focus via `xdotool windowactivate` before keyboard shortcuts, or add a brief delay after `setFocus()` bridge call.

---

## Fix Priority

1. **Re-provision VM** (fixes 33 tests) — `make destroy && make up`
2. **Update mock targets** in unit tests (fixes 19 tests) — change from `subprocess.run` to `run_command` mocking
3. **Update stale test assertions** (fixes 8 tests) — file_dialog, atspi, workspace
4. **Fix clipboard focus** (fixes 2 tests) — add window activation before key events

---

## Responsible Commits

| Commit | Description | Tests Broken |
|---|---|---|
| `2459fa4` | Ctrl+C handling — subprocess.run → Popen | 19 unit tests (mock target mismatch) |
| `3993b3b` | Fix E2E failures — file_dialog/atspi rewrite | 7 unit tests (stale assertions) |
| `2a387f1` | Vagrant workspace defaults | 1 unit test (mac_address) |
| VM state drift | gi symlink broken | 33 e2e/integration |
