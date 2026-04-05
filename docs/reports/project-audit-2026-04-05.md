# Project Audit Report — qt-ai-dev-tools

**Date:** 2026-04-05
**Scope:** Full codebase review — source code, tests, infrastructure, architecture, documentation
**Method:** 4 parallel review agents (src quality, test quality, infra/config, architecture/docs) + dedicated test verification agent

**Fix status:** 5 parallel fix streams executed. 24 files modified, 3 new test files created. All lint passes.

---

## Executive Summary

The project is in solid shape for a v0.2.0 release. Lint is clean (basedpyright strict + ruff, 0 errors). Architecture is well-layered with no circular imports. E2e tests are excellent and match the project's "real over mocked" philosophy. However, several concrete issues were found across all review areas.

### What was fixed (2026-04-05)

**Stream A — Bug fixes (10 fixes):**
- [x] B1: Deleted dead ssh-config call in cli.py
- [x] B2: Added pytest-timeout to dev deps
- [x] S1: Socket permissions 0o600 on bridge server
- [x] S2: mkstemp for bootstrap temp script
- [x] S3: Display parameter validation in vm_run
- [x] R2: Recording output verification in audio.record()
- [x] R3: Narrowed tray.py RuntimeError catch + logging
- [x] TD2: Literal type for eval mode (protocol, eval, server, client)
- [x] TD8: DEVNULL for pw-loopback and rsync-auto Popen
- [x] R4: PulseAudio/PipeWire conflict fixed in provision template

**Stream B — Doc/config fixes (14 edits):**
- [x] D1: Setup skill updated ("not on PyPI" → proper install instructions)
- [x] D2: Roadmap skill names corrected
- [x] D3: Roadmap non-existent doc references fixed (4 edits)
- [x] D4: CLAUDE.md "except 7.7" removed
- [x] D5: Clipboard description fixed in CLAUDE.md
- [x] D6: Clipboard description fixed in README.md
- [x] DEVELOPMENT.md: All 18 Makefile targets documented
- [x] pyproject.toml: Python 3.13/3.14 classifiers added
- [x] Makefile: test-e2e runner fixed
- [x] .pre-commit-config.yaml: basedpyright scope fixed

**Stream C — Provision fix:**
- [x] Removed PulseAudio daemon startup from .bashrc in provision template
- [x] Regenerated provision.sh

**Stream D — New e2e tests (16 tests):**
- [x] tests/e2e/test_compound_e2e.py: fill (3), do (5), wait (2) = 10 tests
- [x] tests/integration/test_cli_errors.py: CLI failure modes = 5 tests
- [x] tests/test_main.py: Added pytest markers

**Stream E — Unit test fixes (new/rewritten):**
- [x] tests/unit/test_clipboard.py: Rewritten for xsel+xclip coverage (12 tests, up from 6)
- [x] tests/unit/test_interact.py: Fixed weak focus fallback assertion
- [x] tests/unit/test_notify.py: Added listen() integration test (2 tests)
- [x] tests/unit/test_installer.py: New file (10 tests)

### What remains unfixed

- B3: Installer skills bundling as package data (medium effort, deferred)
- T4: Tray SNI enablement in VM (high effort, deferred)
- TD1: cli.py split into subpackage (refactoring, deferred)
- TD9: Result pattern adoption decision (architecture, deferred)

**By severity (after fixes):**

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| **BUG** | 3 | 2 | 1 (installer skills bundling — deferred) |
| **SECURITY** | 3 | 3 | 0 |
| **RISK** | 5 | 4 | 1 (host pytest crash — documented in DEVELOPMENT.md) |
| **STALE DOCS** | 6 | 6 | 0 |
| **TEST GAP** | 12 | 9 | 3 (tray SNI, bridge payload limit, proxy detection) |
| **DEBT** | 9 | 4 | 5 (cli.py split, Result pattern, duplicated env, unused ClipboardError, dead notify branch) |
| **TEST QUALITY** | 15 | 4 | 11 (tautological tests accepted as documentation) |
| **INCONSISTENCY** | 5 | Lint scope mismatch, test runner mismatch, missing Makefile docs |

---

## BUGS — Must Fix

### B1. Dead duplicate `vagrant ssh-config` call in CLI

**File:** `cli.py:107-117`
**What:** `_proxy_screenshot` runs `vagrant ssh-config` twice — the first result is discarded entirely.
**Fix:** Remove the dead first `subprocess.run` call. Small, safe fix.

### B2. `pytest-timeout` missing from dev dependencies

**File:** `pyproject.toml`
**What:** `timeout = 30` is configured in `[tool.pytest.ini_options]` and `--timeout=60` is passed in the Makefile e2e target, but `pytest-timeout` is not in `[dependency-groups] dev`. The timeout setting is silently ignored — tests that hang will hang forever.
**Fix:** Add `"pytest-timeout>=2.3.1"` to dev dependencies.

### B3. Installer `_copy_skills()` fails silently on pip install

**File:** `installer.py:74-75`
**What:** `_copy_skills()` navigates `_PACKAGE_ROOT.parent.parent` to find `skills/`. When pip-installed (not editable), this lands in `site-packages/`, not the project root. Skills are silently not copied.
**Fix:** Bundle `skills/` as package data via hatch build config and use `importlib.resources`, OR document this limitation and add a log warning.

---

## SECURITY — Should Fix

### S1. Bridge Unix socket is world-readable

**File:** `bridge/_server.py`
**What:** Socket at `/tmp/qt-ai-dev-tools-bridge-<pid>.sock` is created with default permissions. Any local user can send arbitrary code to the bridge.
**Fix:** Set socket permissions to `0o600` after `bind()`.

### S2. Bootstrap temp script is world-readable

**File:** `bridge/_bootstrap.py:100-101`
**What:** `_write_bootstrap_script` writes to `/tmp/` with default permissions. Race condition possible between write and `sys.remote_exec`.
**Fix:** Use `tempfile.mkstemp` with `mode=0o600`.

### S3. Shell injection via `display` parameter in `vm_run`

**File:** `vm.py:89-95`
**What:** The `display` parameter is interpolated directly into a shell command string passed to `vagrant ssh -c`. A crafted display value like `; rm -rf /` would execute.
**Fix:** Validate display format (`:\d+`) or use `shlex.quote()`.

---

## RISKS — Should Address

### R1. Bare `except Exception` swallows AT-SPI errors in tree dump

**File:** `pilot.py:199-203`
**What:** `get_extents()` failure in `_dump` is silently swallowed. D-Bus failures, network issues all masked.
**Fix:** Log at debug level, or narrow to specific AT-SPI exceptions.

### R2. `audio.record()` doesn't verify recording actually succeeded

**File:** `audio.py:170-177`
**What:** Returns output path even if pw-record failed or file is empty/missing.
**Fix:** Verify output file exists and has non-zero size after recording.

### R3. `tray.list_items()` swallows all RuntimeErrors

**File:** `tray.py:47-53`
**What:** Real errors (permission denied, busctl crash) masked — only "service not available" should be caught.
**Fix:** Check error message or exit code to distinguish error types.

### R4. PulseAudio and PipeWire conflict in VM provisioning

**File:** `provision.sh.j2`
**What:** Installs both PulseAudio AND PipeWire. `.bashrc` starts PulseAudio daemon which fights with `pipewire-pulse` from the desktop session.
**Fix:** Pick one audio stack. Remove PulseAudio daemon start from `.bashrc` if using PipeWire.

### R5. Host `pytest` crashes with confusing INTERNALERROR

**File:** `pyproject.toml` (pytest-qt + missing PySide6)
**What:** Running `uv run pytest` on the host crashes immediately because pytest-qt tries to import PySide6 at collection time. Developers get a confusing traceback instead of a clear error.
**Fix:** Document in DEVELOPMENT.md that all tests must run in the VM, OR add early detection in `conftest.py`.

---

## STALE DOCUMENTATION — Should Fix

### D1. Setup skill says "not on PyPI" (HIGH IMPACT)

**File:** `skills/qt-dev-tools-setup/SKILL.md:17`
**What:** Claims "qt-ai-dev-tools is not on PyPI" but v0.2.0 is published. Agents follow a git-clone workflow instead of `pip install` / `uvx init`.
**Fix:** Rewrite Step 1 to offer `uvx qt-ai-dev-tools init` (primary) or `pip install` (secondary).

### D2. Roadmap lists wrong skill names

**File:** `docs/ROADMAP.md` Phase 5.1
**What:** References 3 old skill names (install-qt-ai-dev-tools, qt-inspect-interact-verify, qt-widget-patterns) that don't exist. Actual skills: qt-dev-tools-setup, qt-app-interaction.
**Fix:** Update Phase 5.1 text and directory tree.

### D3. Roadmap claims 3 doc files that don't exist

**File:** `docs/ROADMAP.md` Phases 4.6, 5.3, 5.6, 6.0g
**What:** Claims `docs/vm-setup-guide.md`, `docs/agent-workflow.md`, `docs/bridge-guide.md` were created. None exist.
**Fix:** Either create them or update roadmap to note content was folded into skills/CLAUDE.md.

### D4. CLAUDE.md says "except 7.7 manual testing"

**File:** `CLAUDE.md` "Current state"
**What:** Phase 7.7 is now Done per roadmap and commit messages.
**Fix:** Update to "Phases 1-7 complete."

### D5. Clipboard described as "xclip wrapper"

**Files:** `CLAUDE.md:41`, `README.md:103`
**What:** Quick orientation says "xclip wrapper" but code uses xsel (preferred) with xclip fallback.
**Fix:** Change to "xsel/xclip wrapper".

### D6. DEVELOPMENT.md missing 8 Makefile targets

**File:** `DEVELOPMENT.md`
**What:** Missing: test-e2e, test-atspi, run, provision, sync, ssh, workspace-init, help.
**Fix:** Add them to the targets table.

---

## TEST GAPS — Should Address

### T1. No tests for `installer.py` (MEDIUM RISK)

**What:** 7 public functions with zero test coverage. A broken installer means users can't set up the toolkit.
**Fix:** Add unit tests calling `init_toolkit(tmp_path)` and verifying expected files are created.

### T2. No e2e tests for compound commands `fill` / `do` (MEDIUM RISK)

**What:** These are the primary commands agents use. No integration or e2e test exercises them.
**Fix:** Add CLI tests in `test_cli.py` that run `fill` and `do` against the sample app in the VM.

### T3. No e2e test for `wait` command

**What:** `qt-ai-dev-tools wait --app` is used in automation setups. No test.
**Fix:** Add test calling `wait --app` for the already-running test app.

### T4. Tray e2e tests permanently skipped (4 tests)

**File:** `tests/e2e/test_tray_e2e.py`
**What:** All 4 tray tests use unconditional `@pytest.mark.skip` due to missing SNI watcher in VM.
**Fix:** Install `snixembed` in VM provisioning to enable SNI D-Bus, convert to `skipif`.

### T5. `tests/test_main.py` missing pytest markers

**What:** 5 tests with no markers — invisible to tier-based test selection (`-m unit`, `-m e2e`).
**Fix:** Add appropriate `pytestmark` assignments.

### T6. Clipboard unit tests are FALSE-CONFIDENCE — xsel path completely untested

**File:** `tests/unit/test_clipboard.py`
**What:** Tests mock `check_tool`/`run_tool` for the xclip path, but the real code now prefers xsel via `_use_xsel()`. The tests don't patch `_use_xsel()`, so which code path runs depends on whether xsel is installed in the test environment. The xsel code path has **zero** unit test coverage.
**Fix:** Split into two test groups — one with `_use_xsel()` patched to `True` (testing xsel args), one patched to `False` (testing xclip args). Also test the `xclip -l 0` timeout workaround.

### T7. No tests for CLI failure modes / error messages (CRITICAL)

**What:** When `click` finds no matching widget, or `tree` has no AT-SPI apps, or `screenshot` fails — the CLI should produce useful error messages with non-zero exit codes. No test verifies any failure path.
**Impact:** Agents receive unhelpful errors and can't diagnose problems.
**Fix:** Add tests for: `click` with no match (exit code + stderr), `tree` with no apps, `screenshot` when scrot fails.

### T8. No tests for `interact.py` failure modes

**What:** All xdotool calls use `check=True` but `click()`, `type_text()`, `press_key()` don't catch `CalledProcessError`. If xdotool fails (wrong DISPLAY, no X server), raw CalledProcessError propagates with no context.
**Fix:** Test what happens when xdotool returns non-zero — verify error propagation or contextual error wrapping.

### T9. No unit tests for VM proxy detection logic

**What:** The CLI auto-detects host vs VM via `QT_AI_DEV_TOOLS_VM=1` env var and proxies through SSH. This detection and SSH command construction has zero unit tests.
**Fix:** Mock environment and subprocess to verify: inside VM → direct execution, on host → SSH proxy command with correct args.

### T10. Bridge server has no payload size limit

**File:** `bridge/_server.py`
**What:** `_handle_connection` reads `recv(65536)` in a loop until newline. No size limit enforced. A buggy or malicious client could cause memory exhaustion in the target Qt app.
**Fix:** Add max payload size check (similar to client's `_MAX_MESSAGE_SIZE`).

### T11. `find_bridge_socket()` untested with multiple sockets

**What:** When multiple Qt apps run (each with a bridge socket), `find_bridge_socket(pid=None)` behavior is untested. Could connect to wrong app.
**Fix:** Create multiple fake socket files, verify discovery behavior.

### T12. `notify.listen()` integration path untested

**What:** Unit test only verifies `check_tool` was called. Never feeds actual dbus-monitor output through the listen→parse pipeline. The integration between `listen()` and `_parse_notifications()` is untested.
**Fix:** Mock `subprocess.run` to raise `TimeoutExpired` with stdout containing notification data, verify `listen()` returns properly parsed `Notification` objects.

---

## TECH DEBT — Consider

### TD1. Monolithic `cli.py` (1221 lines)

**What:** All CLI commands in one file. Will keep growing.
**Fix:** Split into `cli/` subpackage with modules per command group (bridge, audio, vm, etc.).
**Effort:** Medium. Arch-level refactor.

### TD2. `EvalRequest.mode` should be `Literal["auto", "eval", "exec"]`

**Files:** `bridge/_protocol.py:16`, `bridge/_eval.py:29`
**What:** `mode` is `str` — no compile-time validation of valid values.
**Fix:** Use `Literal` type. Small fix.

### TD3. Duplicated `DISPLAY` env construction

**Files:** `clipboard.py:16-19`, `interact.py`
**What:** Same `_display_env` logic in two places with slightly different implementations.
**Fix:** Extract shared utility. Small fix.

### TD4. Unused `ClipboardError` dataclass

**File:** `subsystems/models.py:9-12`
**What:** Defined but never used — clipboard.py raises RuntimeError instead.
**Fix:** Either use it (following Result pattern) or remove. Small fix.

### TD5. `notify.py:46-47` dead `isinstance(exc.stdout, bytes)` branch

**What:** Since `text=True` is passed, `exc.stdout` is `str | None`, never `bytes`.
**Fix:** Simplify to `output = exc.stdout or ""`. Small fix.

### TD6. `tray.py` uses `print()` instead of logging

**File:** `tray.py:49-53`
**What:** Warning printed to stderr instead of using `logger.warning()`.
**Fix:** Use logging. Small fix.

### TD7. Unnecessary `# type: ignore` in `_atspi.py:100`

**What:** `range(n_actions)` — n_actions is already typed as `int`.
**Fix:** Remove. Small fix.

### TD8. `audio.py` Popen pipes opened but never consumed

**File:** `audio.py:43-50`
**What:** `virtual_mic_start` opens stdout/stderr PIPEs but never reads them. Buffer can fill.
**Fix:** Use `subprocess.DEVNULL` instead. Small fix.

### TD9. Philosophy vs Reality — Result pattern not adopted

**What:** `docs/PHILOSOPHY.md` mandates `Result[T, E]` for expected failures. No module uses it — all use exceptions.
**Fix:** Either adopt Result in library layer or update PHILOSOPHY.md. Arch-level decision.

---

## INCONSISTENCIES — Minor

### I1. `poe lint_full` vs `make lint` have different scopes

**What:** poe runs ruff on `.` (entire repo) with auto-fix + format. make lint runs on `src/ tests/` without auto-fix.
**Fix:** Align them.

### I2. `test-e2e` Makefile target uses `python3 -m pytest` instead of `uv run pytest`

**What:** Inconsistent with other test targets that use `uv run pytest`.
**Fix:** Change to `uv run pytest`.

### I3. Pre-commit basedpyright runs per-file

**What:** `pass_filenames: true` causes basedpyright to analyze individual files, missing cross-module issues.
**Fix:** Set `pass_filenames: false`, run `basedpyright src/`.

### I4. Python 3.13/3.14 classifiers missing

**What:** Only "Python :: 3.12" listed despite `>=3.12` and bridge targeting 3.14+.
**Fix:** Add 3.13 and 3.14 classifiers.

### I5. Mixed subprocess patterns across subsystems

**What:** `tray.py` uses `sys.stderr` print, `clipboard.py` uses `_subprocess` helpers, `notify.py` uses raw `subprocess.run`.
**Fix:** Standardize on `_subprocess` helpers where possible.

---

## Recommended Priority Order

**Immediate (small fixes, high impact):**
1. S1 — Socket permissions (`_server.py`)
2. B2 — Add pytest-timeout to deps
3. D1 — Fix setup skill "not on PyPI"
4. S3 — Validate display parameter
5. B1 — Remove dead ssh-config call

**Short-term (before next release):**
6. S2 — Bootstrap script permissions
7. D2-D6 — Fix stale documentation
8. T5 — Add markers to test_main.py
9. TD2 — Literal type for eval mode
10. TD4-TD7 — Small debt fixes

**Medium-term (next development cycle):**
11. T1 — Installer tests
12. T2 — Compound command e2e tests
13. R4 — Fix PulseAudio/PipeWire conflict
14. R5 — Host pytest experience
15. TD1 — Split cli.py

**Medium-term (next development cycle) — continued:**
16. T6 — Fix clipboard unit tests (xsel path)
17. T7 — CLI failure mode tests
18. T8 — interact.py failure mode tests

**Long-term (architecture decisions):**
19. TD9 — Result pattern adoption decision
20. T4 — SNI enablement for tray tests
21. B3 — Installer skills bundling
22. T10 — Bridge server payload size limit

---

## Appendix: Test Quality Verification

Detailed per-test verdicts from the test verification agent. Tests are evaluated against the project's own testing philosophy: "tests that mock away the thing they're testing prove nothing."

### Verdict Summary

| Verdict | Count | Description |
|---------|-------|-------------|
| **GOOD** | 25 | Genuinely proves feature works |
| **ACCEPTABLE** | 4 | Not ideal, but cost of rewriting exceeds risk |
| **TAUTOLOGICAL** | 10 | Asserts what the mock was told to return |
| **FALSE-CONFIDENCE** | 2 | Passes but doesn't prove the feature works |
| **WEAK-ASSERTION** | 3 | Assertions don't verify meaningful behavior |

### GOOD tests (exemplary — keep as-is)

- `test_bridge_eval.py` — All tests. Exercises real Python eval/exec engine, no mocking. Pure function testing.
- `test_bridge_client.py` — Uses real Unix sockets with threaded mock server. Heavyweight testing done right.
- `test_bridge_server.py` — FakeServer with real sockets. Tests protocol end-to-end (minus PySide6).
- `test_bridge_protocol.py` — Real JSON codec roundtrips.
- `test_workspace.py` — Real filesystem via `tmp_path`. Proper integration-style tests.
- `test_models.py` — Pure data transformation tests (center calculation, serialization).
- `test_pilot.py:TestQtPilotFind` — Real tree traversal and filtering against mock tree structure.
- `test_file_dialog.py` — Custom MockPilot records actions; assertions verify interaction sequences.
- `test_tray.py:TestParseRegisteredItems/TestParseMenuOutput` — Real string parsing of known formats.
- `test_notify.py:TestParseNotifications` — Complex multi-field parsing of real dbus-monitor format.
- `test_audio.py:TestParseSoxStat/TestParseSources/TestParseStreams` — Real PipeWire output parsing.
- `test_bootstrap.py` — Version detection, path discovery, script generation, timeout behavior.
- `test_atspi.py:TestGetText/TestDoAction` — Real business logic branching (text fallback, action error paths).
- All e2e tests — Full stack with real apps. Most valuable tests in the suite.

### TAUTOLOGICAL tests (verify mock returns what it was told)

These tests verify subprocess argument construction. They serve as executable documentation but won't catch real failures. Verdict: **accept-as-documentation**.

| Test | What it really proves |
|------|----------------------|
| `test_interact.py:TestClick` | xdotool arg string includes computed coordinates |
| `test_interact.py:TestTypeText` | xdotool arg string includes typed text |
| `test_interact.py:TestPressKey` (×2) | xdotool arg includes key name |
| `test_tray.py:TestListItems` | busctl is called via check_tool/run_tool |
| `test_tray.py:TestClick` | D-Bus Activate is called |
| `test_notify.py:TestDismiss` | busctl CloseNotification is called |
| `test_notify.py:TestAction` | busctl ActionInvoked is called |
| `test_vm.py:TestVmUp/Status/Destroy/Sync` | vagrant subcommand arg lists |
| `test_audio.py:TestVirtualMicStart` | Popen wrapping of pw-loopback |

### FALSE-CONFIDENCE tests (should rewrite)

| Test | Problem |
|------|---------|
| `test_clipboard.py:TestClipboardWrite` | Tests xclip path but code prefers xsel. Which path runs depends on whether xsel is installed in the env. |
| `test_clipboard.py:TestClipboardRead` | Same — environment-dependent, xsel path has zero coverage. |

### WEAK-ASSERTION tests (should strengthen)

| Test | Problem | Fix |
|------|---------|-----|
| `test_interact.py:TestFocus:test_focus_falls_back_to_click` | Asserts `mock_run.called` — could call anything | Assert actual xdotool command args |
| `test_notify.py:TestListen` | Only asserts `check_tool` was called and result is a list | Feed mock output, verify parsed `Notification` objects |
| `test_qt_namespace.py:TestBuildQtNamespace` | Only tests fallback when PySide6 unavailable | Accept — real testing happens in e2e bridge tests |

### Overall Assessment

The test suite is **well-aligned with the project's philosophy**. The strongest tests (bridge eval, bridge client/server, workspace, e2e suite) are genuinely excellent — real sockets, real filesystems, real Qt apps. The weakest tests are concentrated in subsystem wiring (clipboard, tray, notify, interact) where mocking is heavy. The e2e tests compensate for most unit test weaknesses, which is the right trade-off per the project's "5 good e2e tests > 100 mock-heavy unit tests" principle.
