# Phase 4 & 5: VM Improvements + Agent Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the VM workflow robust and ergonomic (Phase 4), then build agent integration — skills, compound commands, and workflow docs (Phase 5). Also fix code quality backlog items from Phase 2-3.

**Architecture:** Incremental improvements to existing package. No new modules — extend `vm.py`, `workspace.py`, `cli.py`, templates. Skills go in `skills/` at repo root. Compound commands add to `cli.py`.

**Tech Stack:** Python 3.12, typer, Jinja2, colorlog, basedpyright strict, pytest

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/qt_ai_dev_tools/vagrant/vm.py` | Modify | Add auto-sync, fix hardcoded DISPLAY |
| `src/qt_ai_dev_tools/vagrant/workspace.py` | Modify | Add static_ip field, provider-specific config |
| `src/qt_ai_dev_tools/vagrant/templates/Vagrantfile.j2` | Modify | Multi-provider, static IP support |
| `src/qt_ai_dev_tools/interact.py` | Modify | Configurable DISPLAY |
| `src/qt_ai_dev_tools/screenshot.py` | Modify | Replace print with logging, configurable DISPLAY |
| `src/qt_ai_dev_tools/pilot.py` | Modify | Replace print with logging |
| `src/qt_ai_dev_tools/cli.py` | Modify | Add compound commands (fill, do), auto-sync cmd |
| `Makefile` | Modify | Fix broken script references |
| `README.md` | Rewrite | English, current structure |
| `skills/install-qt-ai-dev-tools/SKILL.md` | Create | Setup skill |
| `skills/qt-inspect-interact-verify/SKILL.md` | Create | Core workflow skill |
| `skills/qt-widget-patterns/SKILL.md` | Create | Widget identification patterns |
| `pyproject.toml` | Modify | Add pytest markers |
| `tests/unit/test_vm.py` | Modify | Fix after vm.py changes |
| `docs/vm-setup-guide.md` | Create | VM setup documentation |

---

## Task 0: Code Quality Cleanup (CQ-1, CQ-6, CQ-2)

**Files:**
- Modify: `src/qt_ai_dev_tools/screenshot.py`
- Modify: `src/qt_ai_dev_tools/pilot.py`
- Modify: `src/qt_ai_dev_tools/interact.py`
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py`
- Modify: `pyproject.toml`

- [ ] **Step 1:** Replace `print()` in `screenshot.py` line 19 with `logger.info(...)` using colorlog. Add module-level logger.
- [ ] **Step 2:** Replace `print(text)` in `pilot.py` line 95 (`dump_tree`) with `logger.info(...)`. Add module-level logger.
- [ ] **Step 3:** Add `display` parameter to `_xdotool_env()` in `interact.py` (default `:99` from env or param). Same for `screenshot.py`.
- [ ] **Step 4:** Fix `vm_run()` fallback in `vm.py` to read display from workspace config or accept as param.
- [ ] **Step 5:** Add pytest markers `unit` and `integration` to `pyproject.toml` `[tool.pytest.ini_options]`.
- [ ] **Step 6:** Run `make lint` and fix issues. Commit.

## Task 1: Multi-provider Vagrantfile (Phase 4.3)

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/templates/Vagrantfile.j2`
- Modify: `src/qt_ai_dev_tools/vagrant/workspace.py` (add provider-specific fields)
- Test: `tests/unit/test_workspace.py`

- [ ] **Step 1:** Update `Vagrantfile.j2` to support both libvirt and virtualbox providers with conditional config blocks.
- [ ] **Step 2:** Update `WorkspaceConfig` if new fields needed.
- [ ] **Step 3:** Update workspace tests to verify both provider outputs.
- [ ] **Step 4:** Run tests, commit.

## Task 2: Static IP Support (Phase 4.4)

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/workspace.py` — add `static_ip` field
- Modify: `src/qt_ai_dev_tools/vagrant/templates/Vagrantfile.j2` — use static_ip when set
- Modify: `src/qt_ai_dev_tools/cli.py` — add `--static-ip` to workspace init
- Test: `tests/unit/test_workspace.py`

- [ ] **Step 1:** Add `static_ip: str = ""` to `WorkspaceConfig`.
- [ ] **Step 2:** Update `Vagrantfile.j2` with conditional static IP block.
- [ ] **Step 3:** Add `--static-ip` CLI option to `workspace init`.
- [ ] **Step 4:** Add test for static IP rendering.
- [ ] **Step 5:** Run tests, commit.

## Task 3: Auto-sync Command (Phase 4.2)

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py` — add `vm_sync_auto()`
- Modify: `src/qt_ai_dev_tools/cli.py` — add `vm sync-auto` command
- Test: `tests/unit/test_vm.py`

- [ ] **Step 1:** Add `vm_sync_auto()` to `vm.py` — runs `vagrant rsync-auto` in background.
- [ ] **Step 2:** Add `vm sync-auto` CLI command.
- [ ] **Step 3:** Add test for sync-auto function.
- [ ] **Step 4:** Run tests, commit.

## Task 4: Fix Makefile + Rewrite README

**Files:**
- Modify: `Makefile`
- Rewrite: `README.md`

- [ ] **Step 1:** Fix Makefile targets that reference `./scripts/vm-run.sh` — add workspace-init check or use CLI commands.
- [ ] **Step 2:** Rewrite README.md in English with current project structure, CLI usage, quick start.
- [ ] **Step 3:** Commit.

## Task 5: Compound Commands (Phase 5.2)

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`
- Modify: `src/qt_ai_dev_tools/pilot.py` (add fill method)

- [ ] **Step 1:** Add `fill` command — focus + clear + type. `qt-ai-dev-tools fill --role text --name email --value "test@example.com"`
- [ ] **Step 2:** Add `do` command — click + optional verify. `qt-ai-dev-tools do click "Save" --verify "status contains 'Saved'"`
- [ ] **Step 3:** Add `fill()` method to `QtPilot` class.
- [ ] **Step 4:** Run lint, commit.

## Task 6: AI Skills (Phase 5.1)

**Files:**
- Create: `skills/install-qt-ai-dev-tools/SKILL.md`
- Create: `skills/qt-inspect-interact-verify/SKILL.md`
- Create: `skills/qt-widget-patterns/SKILL.md`

- [ ] **Step 1:** Write install skill — autonomous setup instructions for agents.
- [ ] **Step 2:** Write inspect-interact-verify skill — core workflow loop.
- [ ] **Step 3:** Write widget patterns skill — identification strategies, common recipes.
- [ ] **Step 4:** Commit.

## Task 7: VM Setup Guide + Agent Workflow Docs (Phase 4.6, 5.6)

**Files:**
- Create: `docs/vm-setup-guide.md`
- Create: `docs/agent-workflow.md`

- [ ] **Step 1:** Write VM setup guide — providers, known issues, DHCP workaround, troubleshooting.
- [ ] **Step 2:** Write agent workflow doc — recommended patterns, common sequences, error recovery.
- [ ] **Step 3:** Commit.

## Task 8: Update CLAUDE.md + Roadmap

**Files:**
- Modify: `AGENTS.md` (which is CLAUDE.md)
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1:** Update roadmap — mark Phase 4 and 5 as done, update status lines.
- [ ] **Step 2:** Update CLAUDE.md with new commands, skills references, Phase 4-5 completion.
- [ ] **Step 3:** Commit.

## Task 9: Manual Testing

- [ ] **Step 1:** Run subagent in isolated /tmp dir to test workspace init + verify output.
- [ ] **Step 2:** Run subagent to test CLI help, compound commands, skill file validity.
- [ ] **Step 3:** Fix any issues found.
- [ ] **Step 4:** Final lint + test run, commit.
