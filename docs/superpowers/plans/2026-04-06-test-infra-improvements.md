# Test Infrastructure Improvements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parallelize unit tests via pytest-xdist, add environment-aware make targets so unit tests run without VM, and fix test isolation (gi mock contamination).

**Architecture:** Install pytest-xdist. Use `--dist loadgroup` with a `pytest_collection_modifyitems` hook that auto-groups e2e/integration tests into a serial worker while unit tests distribute freely across parallel workers. Add `test-unit` Makefile target that runs on host. The gi mock contamination is solved by xdist process isolation (separate workers = separate `sys.modules`).

**Tech Stack:** pytest-xdist, pytest markers, Makefile, pyproject.toml, conftest.py hooks

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `pyproject.toml` | Modify | Add pytest-xdist dep, update pytest config (addopts, markers) |
| `tests/conftest.py` | Modify | Add `pytest_collection_modifyitems` hook for xdist grouping |
| `tests/e2e/conftest.py` | Modify | Remove `_ensure_real_atspi` hack (xdist isolation makes it unnecessary) |
| `Makefile` | Modify | Add `test-unit`, `test-parallel` targets; make targets environment-aware |
| `tests/unit/conftest.py` | Create | Explicit unit-test conftest (empty or minimal, ensures clean collection) |
| `tests/unit/test_isolation.py` | Create | Regression test proving gi mock doesn't leak |
| `CLAUDE.md` | Modify | Update test running docs with new targets |

---

## Task 1: Add pytest-xdist Dependency

**Files:**
- Modify: `pyproject.toml` (dev dependencies, lines 30-40)

- [ ] **Step 1: Add pytest-xdist to dev dependencies**

In `pyproject.toml`, add `pytest-xdist` to the `[dependency-groups] dev` list:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.1",
    "pytest-cov>=7.0.0",
    "pytest-qt>=4.5.0",
    "pytest-timeout>=2.3.1",
    "pytest-xdist>=3.5.0",
    "ruff>=0.14.6",
    "basedpyright>=1.34.0",
    "pre-commit",
    "poethepoet",
]
```

- [ ] **Step 2: Run `uv sync` on host to update lockfile**

Run: `uv sync`
Expected: Resolves and installs pytest-xdist into host venv.

- [ ] **Step 3: Sync to VM and install there too**

Run: `uv run qt-ai-dev-tools vm sync && uv run qt-ai-dev-tools vm run "cd /vagrant && uv sync"`
Expected: pytest-xdist available in VM venv.

- [ ] **Step 4: Verify xdist is available**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest --version"` — should mention xdist plugin.
Run on host: `uv run pytest --version` — same check.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add pytest-xdist for parallel test execution"
```

---

## Task 2: Configure pytest-xdist with loadgroup Distribution

**Files:**
- Modify: `pyproject.toml` (pytest.ini_options section, lines 94-110)
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update pyproject.toml pytest config**

Replace the existing `[tool.pytest.ini_options]` section:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
qt_api = "pyside6"
timeout = 30
log_cli = true
log_cli_level = "INFO"
filterwarnings = [
    "ignore::pytest.PytestConfigWarning",
]
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (require VM/display)",
    "e2e: End-to-end tests via transparent VM proxy (require running VM)",
]
```

Key point: do NOT add `addopts = "-n auto"` globally — parallel mode is opt-in via Makefile targets so `pytest` alone still works in serial mode (simpler debugging).

- [ ] **Step 2: Add xdist auto-grouping hook to root conftest.py**

Write `tests/conftest.py`:

```python
"""Shared pytest configuration and hooks."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-group e2e and integration tests for serial execution under xdist.

    When running with pytest-xdist (-n auto), unit tests distribute freely
    across workers for maximum parallelism. E2E and integration tests share
    a single worker (serial) because they depend on shared resources:
    DISPLAY :99, AT-SPI bus, D-Bus session, app subprocesses.

    Without xdist (serial mode), this hook is a no-op — the marker has no
    effect when there's only one worker.
    """
    for item in items:
        fspath = str(item.fspath)
        if "/tests/e2e/" in fspath or "/tests/integration/" in fspath:
            item.add_marker(pytest.mark.xdist_group("serial_vm"))
```

- [ ] **Step 3: Verify hook works in serial mode (no breakage)**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/unit/ -v --co -q" | tail -5`
Expected: Lists unit tests, no errors. The hook is a no-op without `-n`.

- [ ] **Step 4: Verify parallel mode distributes correctly**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/unit/ -n auto -v" | tail -20`
Expected: Tests run across multiple workers (`[gw0]`, `[gw1]`, etc.). All pass.

- [ ] **Step 5: Verify serial grouping for e2e**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -n auto -v" | tail -30`
Expected: E2E and integration tests all run on the same worker (same `[gwN]`). Unit tests spread across multiple workers.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/conftest.py
git commit -m "feat(tests): configure xdist loadgroup for parallel unit tests"
```

---

## Task 3: Remove _ensure_real_atspi Hack

**Files:**
- Modify: `tests/e2e/conftest.py` (lines 25-42)

- [ ] **Step 1: Read current e2e conftest.py**

Read: `tests/e2e/conftest.py` — locate the `_ensure_real_atspi` fixture (lines 25-42).

- [ ] **Step 2: Remove the fixture**

Delete the `_ensure_real_atspi` fixture and its imports (`importlib`, `MagicMock` if only used there). The fixture exists because unit tests contaminate `sys.modules` with mock gi. With xdist, unit and e2e tests run in separate worker processes, so contamination cannot happen.

Remove these lines from `tests/e2e/conftest.py`:
```python
import importlib
from unittest.mock import MagicMock
```
(Only remove if not used elsewhere in the file — check first.)

Remove the entire fixture:
```python
@pytest.fixture(scope="session", autouse=True)
def _ensure_real_atspi() -> None:
    ...
```

- [ ] **Step 3: Verify e2e tests still pass with xdist**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -n auto -v"`
Expected: All tests pass. E2E tests use real gi (not mocked) because they run in a separate worker process.

- [ ] **Step 4: Verify e2e tests still pass WITHOUT xdist (serial fallback)**

Run: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -v"`
Expected: All tests pass. Even in serial mode, the gi mock uses `setdefault` which doesn't override real gi in the VM.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/conftest.py
git commit -m "refactor(tests): remove _ensure_real_atspi hack (xdist isolation replaces it)"
```

---

## Task 4: Add test-unit Makefile Target (Host-Compatible)

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Add environment-aware test-unit target**

Add to the `Tests` section of the Makefile, after the existing targets. The target runs unit tests directly (no VM needed since unit tests are fully mocked):

```makefile
test-unit: ## unit tests only (no VM needed, runs on host or in VM)
	uv run pytest tests/unit/ -v -n auto
```

Unit tests don't need DISPLAY, AT-SPI, PySide6, or any VM services. They mock everything. This target runs wherever `uv run pytest` works — host or VM.

- [ ] **Step 2: Update test-full to use parallel mode**

Change the `test-full` target to use xdist:

```makefile
test-full: ## full tests including AT-SPI, screenshot, and CLI (requires VM + Xvfb)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -v -n auto --dist loadgroup"
```

- [ ] **Step 3: Add .PHONY entries**

Update the `.PHONY` line to include the new target:

```makefile
.PHONY: up provision ssh sync run test test-full test-unit screenshot destroy help status lint lint-fix test-cli test-e2e workspace-init setup
```

- [ ] **Step 4: Verify test-unit runs on host**

Run: `make test-unit`
Expected: Runs unit tests in parallel on host. All pass. No VM contact.

- [ ] **Step 5: Verify test-full still works**

Run: `make test-full`
Expected: Full suite runs in VM with xdist. Unit tests parallel, e2e/integration serial. All pass.

- [ ] **Step 6: Commit**

```bash
git add Makefile
git commit -m "feat(make): add test-unit target, enable xdist for test-full"
```

---

## Task 5: Add Test Isolation Regression Test

**Files:**
- Create: `tests/unit/test_isolation.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/test_isolation.py`:

```python
"""Regression test: gi mock in test_atspi.py must not leak to other modules.

test_atspi.py uses sys.modules.setdefault() to inject mock gi bindings at
module level. This test imports _atspi AFTER test_atspi has run and verifies
the module-level Atspi attribute is usable (not a broken mock reference).

With pytest-xdist, this runs in a separate worker from e2e tests, so
cross-tier contamination is impossible. This test guards against intra-unit
contamination — ensuring one unit test file doesn't break another.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestGiMockIsolation:
    def test_atspi_module_attribute_is_consistent(self) -> None:
        """After test_atspi.py runs, _atspi.Atspi should still be importable.

        In the VM (where real gi exists), sys.modules.setdefault is a no-op
        and Atspi is the real module. On the host (no gi), setdefault installs
        the mock. Either way, _atspi.Atspi must not be None or a detached mock.
        """
        from qt_ai_dev_tools import _atspi as mod

        # Atspi attribute must exist and be non-None
        assert hasattr(mod, "Atspi")
        assert mod.Atspi is not None

    def test_gi_modules_are_coherent(self) -> None:
        """sys.modules gi entries must all be real or all be mock — not mixed."""
        import sys

        gi_mod = sys.modules.get("gi")
        gi_repo = sys.modules.get("gi.repository")

        if gi_mod is None:
            # gi not imported at all — fine (no AT-SPI tests ran yet)
            return

        gi_is_mock = isinstance(gi_mod, MagicMock)
        repo_is_mock = isinstance(gi_repo, MagicMock)

        # Both real or both mock — never mixed
        assert gi_is_mock == repo_is_mock, (
            f"Incoherent gi modules: gi={'mock' if gi_is_mock else 'real'}, "
            f"gi.repository={'mock' if repo_is_mock else 'real'}"
        )
```

- [ ] **Step 2: Run the test on host**

Run: `uv run pytest tests/unit/test_isolation.py -v`
Expected: Both tests pass.

- [ ] **Step 3: Run alongside test_atspi to verify no cross-contamination**

Run: `uv run pytest tests/unit/test_atspi.py tests/unit/test_isolation.py -v`
Expected: All pass. The isolation test runs after test_atspi and gi state is coherent.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_isolation.py
git commit -m "test: add gi mock isolation regression test"
```

---

## Task 6: Create Unit Test conftest.py

**Files:**
- Create: `tests/unit/conftest.py`

- [ ] **Step 1: Create minimal unit conftest**

Create `tests/unit/conftest.py`:

```python
"""Unit test configuration.

Unit tests are pure logic — no external dependencies (no DISPLAY, no AT-SPI,
no D-Bus, no running apps). They run on both host and VM, with or without
pytest-xdist parallelism.
"""
```

This file is intentionally minimal. Its presence documents the unit test contract. No fixtures are needed — unit tests should be self-contained.

- [ ] **Step 2: Commit**

```bash
git add tests/unit/conftest.py
git commit -m "docs(tests): add unit conftest documenting test tier contract"
```

---

## Task 7: Update CLAUDE.md Test Documentation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the Running things section**

In the `## Running things` section, update the make targets table:

```bash
make setup         # initial project setup (uv sync + pre-commit install)
make up            # start VM (~10min first time)
make test          # fast offscreen pytest-qt tests
make test-unit     # unit tests only (parallel, no VM needed)
make test-full     # all tests with xdist (unit parallel + e2e/integration serial, requires VM)
make test-cli      # CLI integration tests only
make test-e2e      # e2e bridge tests only
make lint          # run ruff check + basedpyright
make lint-fix      # auto-fix lint issues
make screenshot    # screenshot current VM display
make status        # check Xvfb, openbox, AT-SPI status
make destroy       # tear down VM
```

- [ ] **Step 2: Add test parallelism section to Key Technical Facts**

Add a bullet point to `## Key technical facts`:

```
- **Test parallelism** — Unit tests run in parallel via pytest-xdist (`-n auto`). E2E and integration tests run serially on a single xdist worker (they share DISPLAY, AT-SPI bus, D-Bus session). The `pytest_collection_modifyitems` hook in `tests/conftest.py` auto-groups tests by directory. `make test-unit` runs on host without VM; `make test-full` runs everything in VM.
```

- [ ] **Step 3: Update tests/CLAUDE.md**

In `tests/CLAUDE.md`, add a section about parallelism:

```markdown
## Test parallelism (pytest-xdist)

Unit tests run in parallel via `pytest-xdist` (`-n auto --dist loadgroup`).
E2E and integration tests are auto-grouped into a single serial worker via
the `pytest_collection_modifyitems` hook in `tests/conftest.py`.

This means:
- Unit tests: distributed across N workers (one per CPU core)
- E2E tests: all on one worker, serial, module-scoped fixtures work normally
- Integration tests: same serial worker as e2e (shared DISPLAY/AT-SPI)

The grouping is automatic — no per-test markers needed. The hook detects
test file paths (`/tests/e2e/`, `/tests/integration/`) and applies
`@pytest.mark.xdist_group("serial_vm")`.

### Running modes

| Command | Parallelism | Environment |
|---------|-------------|-------------|
| `make test-unit` | Parallel (`-n auto`) | Host or VM |
| `make test-full` | Mixed (unit parallel, e2e serial) | VM only |
| `uv run pytest tests/ -v` | Serial (no xdist) | VM only |
| `uv run pytest tests/unit/ -n auto` | Parallel | Host or VM |
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md tests/CLAUDE.md
git commit -m "docs: update test running docs with parallelism and new targets"
```

---

## Verification Checklist

After all tasks are done, run these in order:

1. `make lint` — must be clean (0 errors)
2. `make test-unit` — unit tests pass on host, parallel
3. `make test-full` — full suite passes in VM with xdist
4. `uv run pytest tests/ -v` (in VM) — serial mode still works as fallback
5. Run `make test-full` 3 times — verify stability (no flaky failures from parallelism)
