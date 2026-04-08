# qt-ai-dev-tools roadmap

**Goal:** Give AI agents first-class access to Qt/PySide apps — inspect widgets, interact, take screenshots, read state — with the same ease as Chrome DevTools MCP but with typed widget access via AT-SPI.

**Primary user:** AI coding agents (Claude Code, etc.) working on PySide/PyQt projects.

## Design principles

1. **Composable over monolithic.** 80% of use cases should be one-liners (`qt-ai-dev-tools tree`, `qt-ai-dev-tools click "Save"`). The remaining 20% use the Python library directly. No "super-tool" that tries to do everything.
2. **Agent-scriptable.** The agent can write small Python scripts using `qt_ai_dev_tools` as a library when the CLI isn't enough. Primitives are always exposed.
3. **Drop-in portable.** Works in any PySide6/PyQt6 project. `uvx qt-ai-dev-tools install-and-own` copies the full toolkit into the project — source, templates, skills, config. Agent owns the code, can read and extend it. No global install required, only `uv`.
4. **VM-first.** Vagrant VM is the primary environment — it gives full OS isolation and access to Linux subsystems (D-Bus, audio, system tray). Container/host support comes later as a lighter-weight option for UI-only workflows.
5. **Feedback-rich.** Every action returns enough context for the agent to know what happened — widget state after click, screenshot after interaction, error messages with available alternatives.

## Workflow rules

Rules that apply to every phase of work:

1. **Clean up before proceeding.** Fix all important code issues and tech debt from the code quality backlog before starting a new phase. Don't carry known bugs forward.
2. **Clean worktree at phase end.** Commit and push all changes, or explicitly discard uncommitted work. The worktree must be clean at the end of every phase.
3. **Quality gate after every phase.** Run quality validator agents after completing each phase:
   - Run separate code analyzer subagents checking alignment with `writing-python-code`, `testing-python`, and architecture skill rules
   - Bugs found → fix immediately
   - Non-critical issues → add to code quality backlog in this roadmap
   - Phase is not "done" until the quality gate passes

## Delivery shape

The final product is a **composable toolkit**, not a single binary:

| Layer | What | How agents use it |
|-------|------|-------------------|
| **Python library** (`qt_ai_dev_tools`) | AT-SPI + xdotool primitives | `from qt_ai_dev_tools import QtPilot` in custom scripts |
| **CLI** (`qt-ai-dev-tools`) | One-liner commands | `qt-ai-dev-tools tree`, `qt-ai-dev-tools click "Save"`, `qt-ai-dev-tools screenshot` |
| **AI skills** | Workflow guidance | Teach agents the inspect→interact→verify loop |
| **VM environment** | Vagrant + Xvfb + AT-SPI setup | Scripts that create and manage the headless Qt environment |
| **Docker environment** | Lightweight container alternative (upcoming, Phase 5) | Xvfb + AT-SPI in a container — faster startup, fewer resources, UI-only workflows |

Distribution: `uvx qt-ai-dev-tools install-and-own --yes-I-will-maintain-it` — copies full toolkit (source, templates, skills, config) into the project directory. Agent owns the code, can read and extend it. Skills: installed via skills tooling (`npx -y skills add ...`) or bundled with the toolkit copy.

---

## Task type legend

| Tag | Meaning |
|-----|---------|
| **explore** | Research options, constraints, trade-offs. Output: findings doc. |
| **brainstorm** | Explore requirements, design space, trade-offs before implementation. Output: design doc or decision record. |
| **prototype** | Build quick throwaway to validate an idea. May be discarded. |
| **implement** | Add to the real codebase. Tested, documented. |
| **test** | Verify a feature works. May be automated or manual. |
| **doc** | Persist knowledge: usage, caveats, patterns. |

---

## Completed phases

### Phase 1: Proof of Concept

Vagrant VM with Xvfb + openbox + AT-SPI + xdotool + scrot. Sample PySide6 app, 8 passing tests, RESULTS.md documenting what works and what doesn't.

Key learnings: AT-SPI + xdotool + scrot = full Chrome DevTools equivalent for Qt. `gi.repository.Atspi` works on Python 3.12 (`pyatspi` does not). Openbox required for correct xdotool coordinates. AT-SPI `editable_text.insert_text()` doesn't work with Qt — must use xdotool.

### Phase 2: MVP

Package structure (`src/qt_ai_dev_tools/`), Typer CLI with one-liner commands, JSON output mode, typed AT-SPI wrapper (`_atspi.py`) confining all `# type: ignore` to one module, strict basedpyright project-wide. Vagrant templates (Jinja2) with multi-provider support, `workspace init` command, VM lifecycle commands (`up`/`status`/`ssh`/`sync`/`destroy`/`run`), host/VM command parity, auto-sync via `rsync-auto`, static IP option. Distribution: `uvx qt-ai-dev-tools` + `install-and-own` (shadcn-style local copy), self-update mechanism, AI skills bundled.

### Phase 3: Advanced Capabilities

Agent skills (setup + interaction workflows), compound commands (`fill`, `do`). Bridge eval — runtime code execution inside Qt apps via Unix socket (`evaluate_script` equivalent), with `sys.remote_exec` injection for Python 3.14+. Five Linux subsystem modules: clipboard (xsel/xclip), file dialogs (AT-SPI automation), system tray (D-Bus SNI), notifications (D-Bus monitoring), audio (PipeWire virtual mic, recording, verification). Complex widget helpers (combo box, tabs, table, slider, checkbox, menu). Tree snapshot/diff. Project hygiene: pre-commit hooks, pytest markers, expanded test coverage (unit + e2e + CLI integration). Published v0.5.0 on PyPI.

---

## Phase 4: Architecture & Foundations Rewrite

**Status:** Not started — requires brainstorming before implementation.

The codebase has one hardcoded path: Vagrant + X11. This phase designs and implements the abstraction layer that enables everything else — multiple backends, display protocols, configuration, clean error handling. These concerns are deeply intertwined and must be brainstormed together.

### 4.0 — [brainstorm] Architecture design

Define the full abstraction model:

| Area | Key Questions |
|---|---|
| **Backend abstraction** | Naming/terms: what is a "backend" vs "provider" vs "engine" vs "mode"? What's composed, what's isolated? E.g., `vagrant` is a provider, `x11` is a display protocol, `click` is reusable across X11 engines, `systemd` commands are VM-only today but may support containers later. Composition over inheritance. Runtime capability matrix with validation. |
| **CLI API redesign** | Make the CLI more logical and structured. Runtime dispatch based on active backend config. Universal vs backend-specific commands. Global options (`-v`, `--dry-run`) anywhere in the command. Whether `-v` vs `-vv` distinction is needed. `--dry-run` auto-enables `-v`. |
| **Configuration system** | Env vars, config files (TOML), CLI flags — priority chain. Persistent vs per-invocation settings. Config validates against backend capabilities (e.g., systemd commands valid in VM but not container). |
| **Error handling migration** | Migrate from exceptions to `Result[T, E]` at domain boundaries. Define error boundary layers. Fits naturally with the abstraction rewrite since every boundary is being redesigned. |
| **Test restructuring** | Move test orchestration from Makefile to pytest/config. Single pytest run with unified summary (not multiple runs with logs on top of each other). Reusable test suites (X11 interaction tests run against any X11 backend) + backend-specific suites. Marker-based selection. |
| **Provisioning** | Decouple and compose provisioning logic. Vagrant provisioning, Docker entrypoint, and potential future backends share common setup steps (D-Bus, AT-SPI, Xvfb, openbox) but differ in lifecycle and service management. |

**Output:** Design doc defining all abstractions, naming, composition patterns, and a task breakdown for implementation. After brainstorming, many implementation tasks will be added to this phase.

### 4.1+ — Implementation tasks

TBD after brainstorming. Expected areas:
- Backend abstraction layer implementation
- CLI rewrite
- Config system
- Error handling migration
- Test restructuring
- Provisioning refactor

---

## Phase 5: Docker Environment

**Status:** Research complete. Ready for autonomous implementation.
**Research:** [`docs/backlog/docker-environment.md`](backlog/docker-environment.md)
**Depends on:** Phase 4 (backend abstraction). Prototyping (5.1) can start in parallel with Phase 4.

Research showed Docker handles **95%** of features without `--privileged`. The entire VM service tree collapses to ~15 lines of entrypoint script. Only real systemd and real audio hardware need a VM — neither of which this project requires.

### 5.1 — [prototype] Docker container with full stack

Build and verify: Xvfb + openbox + D-Bus session bus + AT-SPI + xdotool + scrot + PipeWire + dunst + snixembed + stalonetray. All in userspace, no systemd. Test all subsystems. Works on Linux, macOS Docker Desktop, Windows Docker Desktop, and CI.

### 5.2 — [implement] Docker backend integration

Plug into Phase 4 backend abstraction. Dockerfile, entrypoint script, CLI support (e.g., `qt-ai-dev-tools env up --mode container`).

### 5.3 — [implement] Devcontainer support

`.devcontainer/` configuration for IDE integration.

### 5.4 — [test] Cross-environment tests

Same test suite runs on Vagrant VM + Docker. Document feature gaps (if any remain).

### 5.5 — [doc] Environment comparison guide

When to use VM vs container vs host. Feature matrix.

---

## Phase 6: Real-World Validation

**Status:** Complete (three rounds). 27 issues found and fixed, 5 deferred.

Validated against 4 real Qt apps: SpeedCrunch (Qt 5.15), KeePassXC (Qt 5.15), qBittorrent (Qt 6.4), VLC (Qt 5.15). Three rounds of testing, each building on the last. Key outcomes:

- Visibility filter upgraded from coordinate heuristic to AT-SPI `STATE_SHOWING` — 93% noise reduction on menu-heavy apps
- All CLI commands now have consistent `--app` targeting, `--visible` defaults, screenshot transfer
- 40+ tests added (unit + e2e) for previously untested modules and new features
- Qt6 confirmed working identically to Qt5

**Remaining deferred:** 5 issues (ISSUE-007/008/011/018/024). See `docs/real-apps-validation/issues.md`.

**App setup reference:** `docs/real-apps-validation/process.md` — install/launch/kill for all 4 apps.

---

## Skills Refresh

**Status:** Complete.

Rewrote all AI skills to be self-contained single SKILL.md files covering all current CLI features:

- **Rewrote 2 existing skills:** `qt-dev-tools-setup`, `qt-app-interaction` — updated for current CLI flags, subsystem commands, host/VM parity language, `.qt-ai-dev-tools/` workspace directory, `install-and-own` command.
- **Created 3 new skills:** `qt-form-and-input` (form filling, complex widgets), `qt-desktop-integration` (clipboard, file dialogs, tray, notifications, audio), `qt-runtime-eval` (bridge eval, script execution, namespace).
- Deleted all old `references/` directories — skills are fully self-contained now.
- Added skill references to all CLI `--help` epilogs.

---

## Phase 7: Installer & Distribution Overhaul

**Status:** Partially complete. 7.1, 7.4, 7.7, 7.8, 7.9 done. 7.0 brainstorm and 7.2, 7.3, 7.5 still needed. 7.6 skipped.

### 7.0 — [brainstorm] Distribution philosophy

Key design questions: how should skills auto-bundle on local installation? Integration with `npx skills`? Symlinks to global skill locations?

### 7.1 — [implement] `uvx` as sole recommended install, drop `pip` from primary docs — DONE

### 7.2 — [implement] Update-available warning

Check PyPI version, print warning at top of CLI output when a newer version exists.

### 7.3 — [implement] Bake version/commit hash on publish

Build system stamps version and git commit into the package at publish time.

### 7.4 — [implement] Rename `init` → `install-and-own` with `--yes-I-will-maintain-it` confirmation — DONE

### 7.5 — [implement] Auto-bundle skills on local installation

Design and implement automatic skill bundling. May involve symlinks, directory conventions, or integration with external skill managers.

### 7.6 — [implement] Override command name in skills on local installation — SKIPPED

Skipped per user decision.

### 7.7 — [implement] Highlight Vagrantfile editing in setup skill and workspace init output — DONE

### 7.8 — [implement] Default workspace directory `.qt-ai-dev-tools/`, `--path` option removed — DONE

### 7.9 — [implement] VM installation logic fix — DONE

Centralized env var registry (`_env.py`), VM tool readiness check (`_vm_tool.py`), provisioning template cleanup. Key changes: template never runs `uv sync` on user's project, PyPI install version-pinned, install-and-own auto-rebuilds on staleness with gi re-link. Design: `docs/superpowers/specs/2026-04-08-vm-installation-logic-design.md`.

---

## Phase 8: E2E Testing as First-Class Use Case

**Status:** Needs brainstorming. May expand into multiple sub-phases.

The tool isn't only for AI agents — it can serve as a Playwright-for-Qt for any developer writing e2e/UI tests. This phase explores and builds that story.

### 8.0 — [brainstorm] E2E testing vision

What does a pytest + qt-ai-dev-tools e2e test look like? What fixtures, helpers, and assertions are needed? How does reproducibility work? Cleanup? How does this compare to existing Qt testing tools?

### 8.1 — [implement] Pytest fixtures and helpers

### 8.2 — [doc] E2E testing guide and skill

### 8.3 — [doc] Update README to highlight e2e testing use case

---

## Phase 9: Rename to qt-dev-tools

**Status:** Ready to implement. No production users — free to rename everything.
**Timing:** After Phase 4 stabilizes (avoid renaming during heavy refactoring).

### 9.1 — [implement] Rename package, imports, CLI entrypoint, pyproject.toml

### 9.2 — [implement] Rename GitHub repository

### 9.3 — [implement] Publish under new name on PyPI, deprecate old package

### 9.4 — [implement] Update all docs, skills, CLAUDE.md

### 9.5 — [test] Full test suite passes under new name

---

## Phase 10: Screen Recording & Live Demo

**Status:** Needs brainstorm for simple solutions.

Valuable as a promotional feature — show the tool in action with a real app.

### 10.1 — [brainstorm] Evaluate recording approaches

ffmpeg + Xvfb screen capture, VNC viewer, GIF generation. What's simplest and most portable?

### 10.2 — [implement] Minimal recording command

E.g., `qt-dev-tools record start/stop` wrapping ffmpeg.

### 10.3 — [doc] Create demo workflow and GIF/video for README

---

## Phase 11: Alternative VM Backends

**Status:** Research complete. **Requires pair-programming with user** — not autonomous.
**Research:** [`docs/backlog/vm_backends_research.md`](backlog/vm_backends_research.md)
**Depends on:** Phase 4 (backend abstraction), Phase 5 (Docker informs container-like backend gaps).

Research recommends: abstract backend first (Phase 4) → test systemd-nspawn → then Firecracker if gaps remain.

### 11.1 — [prototype] systemd-nspawn with full test suite (pair-program with user)

### 11.2 — [prototype] Firecracker microVM if nspawn has gaps (pair-program with user)

### 11.3 — [implement] Integrate viable backends via Phase 4 abstraction

### 11.4 — [test] Cross-backend compatibility

---

## Phase 12: Wayland Support — DEFERRED

**Status:** Research complete. High complexity, low current value. Deferred indefinitely.
**Research:** [`docs/backlog/wayland-support.md`](backlog/wayland-support.md)
**Depends on:** Phase 4 (display protocol abstraction), Phase 5 (Docker).
**Unblocked when:** Actual demand from users on Wayland-only environments.

Dual-backend approach: X11 + Wayland. Easy wins (clipboard via `wl-clipboard`, screenshots via `grim`). Hard part: input automation (`ydotool` + `swaymsg`), AT-SPI coordinate translation on Wayland. VM infra change: Xvfb + openbox → sway headless.

---

## Standalone tasks

Independent of phases. Can be picked up anytime.

| ID | Size | Task | Status |
|---|---|---|---|
| S-1 | small | Docs: mark X11-only, Python+Qt focus, clean up excessive "transparent proxy" mentions | Done |
| S-2 | small | `--dry-run` auto-enables `-v` | Done |
| S-3 | medium | Print helper instructions after key commands (e.g., `workspace init` → suggest editing Vagrantfile) | Partial — `workspace init` and `install-and-own` done, other commands not yet |
| S-4 | medium | CLI version update warning (check PyPI, print at top of output) | Ready |
| S-5 | small | Add skill references to all CLI `--help` epilogs | Done |
| S-6 | large | E2E tests for VM tool installation process (both PyPI and install-and-own modes, version mismatch detection, staleness rebuild). Requires spinning up full environments — deferred until Docker backend is ready (Phase 5). | Deferred |

---

## Dependency map

```
Phase 4: Architecture Rewrite  ◄── everything depends on this
  ├── Phase 5: Docker ──────────── prototyping can overlap
  ├── Phase 9: Rename ─────────── after Phase 4 stabilizes
  ├── Phase 11: VM Backends ────── needs abstraction layer
  └── Phase 12: Wayland ────────── DEFERRED

Phase 6: Real-World Validation ── independent, anytime
Phase 7: Installer Overhaul ───── mostly independent
Phase 8: E2E Testing Framework ── mostly independent
Phase 10: Screen Recording ────── independent

Standalone tasks (S-1..S-6) ───── independent, anytime
```

---

## How this roadmap evolves

This is not a waterfall plan. Phases overlap. Tasks get added, removed, or reordered based on:
- What the agent (primary user) actually needs when using the tool
- What breaks or is painful in practice
- What the environment constraints turn out to be

After completing any task, update this roadmap with findings and adjust priorities.
