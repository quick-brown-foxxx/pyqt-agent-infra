# CLI & Docs Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Batch of 9 independent improvements: rename init command, change workspace default directory, add helper instructions, dry-run auto-enables verbose, skill references in --help, docs cleanups, and uvx-first docs.

**Architecture:** All changes are independent and touch separate areas. Most modify `cli.py` + tests. Docs tasks modify skills/README only. Each task produces a working commit. Use `writing-python-code` and `testing-python` skills for all Python changes.

**Tech Stack:** Python 3.12+, typer CLI, pytest, markdown

**Key context for the implementer:**
- Use the `writing-python-code` skill when writing/editing Python code.
- Use the `testing-python` skill when writing tests.
- Read `CLAUDE.md` for project conventions and `docs/PHILOSOPHY.md` for foundational principles.
- Unit tests run on host: `uv run pytest tests/unit/ -v` (use `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to prevent pytest-qt crash).
- Integration tests run in VM: `uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/integration/ -v"`.
- All Python code must pass `uv run poe lint_full` (basedpyright strict + ruff).
- No backwards compatibility needed — alpha with 0 users.

---

## File Structure

```
src/qt_ai_dev_tools/
├── cli.py                          # MODIFY — rename init, workspace init path, epilogs, dry-run
├── installer.py                    # MODIFY — rename init_toolkit function
├── vagrant/
│   ├── vm.py                       # MODIFY — find_workspace looks for .qt-ai-dev-tools/
│   └── workspace.py                # MODIFY — remove path param, hardcode .qt-ai-dev-tools/

tests/
├── unit/
│   ├── test_installer.py           # MODIFY — update for renamed function
│   ├── test_workspace.py           # MODIFY — update for new default path
│   ├── test_run.py                 # MODIFY — add dry-run auto-verbose test
│   └── test_vm.py                  # MODIFY — update find_workspace tests
├── integration/
│   └── test_verbose_dryrun.py      # MODIFY — add dry-run auto-verbose integration test

skills/
├── qt-dev-tools-setup/SKILL.md     # MODIFY — uvx-first, Vagrantfile warning, install-and-own
├── qt-app-interaction/SKILL.md     # MODIFY — clean up proxy language
├── qt-form-and-input/SKILL.md      # MODIFY — clean up proxy language
├── qt-desktop-integration/SKILL.md # MODIFY — clean up proxy language
├── qt-runtime-eval/SKILL.md        # MODIFY — clean up proxy language

README.md                           # MODIFY — uvx-first, X11-only, proxy cleanup
CLAUDE.md                           # MODIFY — proxy language, .qt-ai-dev-tools path
```

---

### Task 1: Rename `init` → `install-and-own` with confirmation flag

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:180-199`
- Modify: `src/qt_ai_dev_tools/installer.py` (rename `init_toolkit` → `install_and_own`)
- Modify: `tests/unit/test_installer.py`

- [ ] **Step 1: Read current code**

Read `src/qt_ai_dev_tools/installer.py` and `src/qt_ai_dev_tools/cli.py:180-219` and `tests/unit/test_installer.py`.

- [ ] **Step 2: Update tests for renamed function and confirmation flag**

In `tests/unit/test_installer.py`, rename all `init_toolkit` references to `install_and_own`. The function signature stays the same except the name.

```python
# In every test method, change:
from qt_ai_dev_tools.installer import init_toolkit
# to:
from qt_ai_dev_tools.installer import install_and_own
```

Also rename `TestInitToolkit` → `TestInstallAndOwn`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_installer.py -v -p xdist -p timeout`
Expected: ImportError — `install_and_own` not found.

- [ ] **Step 4: Rename function in installer.py**

In `src/qt_ai_dev_tools/installer.py`, rename `def init_toolkit(` → `def install_and_own(`. Keep the body identical. No other changes to installer.py.

- [ ] **Step 5: Update CLI command**

In `src/qt_ai_dev_tools/cli.py`, replace the `init_command` function (lines 180-199):

```python
@app.command(name="install-and-own")
def install_and_own_command(
    path: typing.Annotated[Path, typer.Argument(help="Target directory")] = Path("./qt-ai-dev-tools"),
    memory: typing.Annotated[int, typer.Option(help="VM memory MB")] = 4096,
    cpus: typing.Annotated[int, typer.Option(help="VM CPUs")] = 4,
    confirm: typing.Annotated[
        bool,
        typer.Option(
            "--yes-I-will-maintain-it",
            help="Confirm you accept responsibility for maintaining this local copy.",
        ),
    ] = False,
) -> None:
    """Copy the full qt-ai-dev-tools toolkit into your project (shadcn-style).

    This creates a local copy of the entire toolkit that YOU own and maintain.
    Updates won't apply automatically — use self-update to pull new versions.
    """
    if not confirm:
        typer.echo("This command copies the full qt-ai-dev-tools source into your project.")
        typer.echo("You will own and maintain this copy. Updates require running self-update.")
        typer.echo("")
        typer.echo("If you understand, re-run with: --yes-I-will-maintain-it")
        raise typer.Exit(code=1)

    from qt_ai_dev_tools.installer import install_and_own

    target = path.resolve()
    try:
        created = install_and_own(target, memory=memory, cpus=cpus)
    except OSError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for entry in created:
        typer.echo(f"  {entry}")
    typer.echo(f"\nToolkit installed to {target}")
    typer.echo(f"→ Run: cd {target} && uv sync")
    typer.echo("→ Run: qt-ai-dev-tools workspace init")
    typer.echo("→ Load the qt-dev-tools-setup skill for full setup guidance.")
```

Also update `self_update_command` to import from renamed function — but `self_update` function name in installer.py stays the same, only `init_toolkit` was renamed. So self_update_command only needs its internal call `init_toolkit` changed if self_update() calls init_toolkit(). Check: `self_update()` in installer.py calls `init_toolkit()` internally — rename that call too.

- [ ] **Step 6: Run tests**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_installer.py -v -p xdist -p timeout`
Expected: All tests pass.

- [ ] **Step 7: Run linter**

Run: `uv run poe lint_full`
Expected: No errors.

- [ ] **Step 8: Commit**

```bash
git add src/qt_ai_dev_tools/installer.py src/qt_ai_dev_tools/cli.py tests/unit/test_installer.py
git commit -m "feat: rename init → install-and-own with --yes-I-will-maintain-it confirmation"
```

---

### Task 2: Default workspace directory → `.qt-ai-dev-tools/`

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:584-626` (workspace_init command)
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py` (find_workspace function)
- Modify: `src/qt_ai_dev_tools/vagrant/workspace.py` (render_workspace — no changes needed, it takes target path)
- Modify: `tests/unit/test_workspace.py`
- Modify: `tests/unit/test_vm.py`

- [ ] **Step 1: Read current code**

Read `src/qt_ai_dev_tools/vagrant/vm.py` (specifically `find_workspace` function), `src/qt_ai_dev_tools/cli.py:584-626`, `tests/unit/test_workspace.py`, `tests/unit/test_vm.py`.

- [ ] **Step 2: Update find_workspace in vm.py**

The current `find_workspace()` walks up from cwd looking for a directory containing `Vagrantfile`. Change it to look for `.qt-ai-dev-tools/Vagrantfile` instead:

```python
_WORKSPACE_DIR = ".qt-ai-dev-tools"


def find_workspace(workspace: Path | None = None) -> Path:
    """Find workspace directory containing Vagrantfile.

    If workspace is given, use it. Otherwise walk up from cwd looking for
    a .qt-ai-dev-tools/ directory containing Vagrantfile.
    """
    if workspace is not None:
        vf = workspace / "Vagrantfile"
        if not vf.exists():
            msg = f"No Vagrantfile in {workspace}"
            raise FileNotFoundError(msg)
        return workspace

    current = Path.cwd()
    while True:
        candidate = current / _WORKSPACE_DIR
        if (candidate / "Vagrantfile").exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    msg = f"No {_WORKSPACE_DIR}/Vagrantfile found in {Path.cwd()} or parent directories"
    raise FileNotFoundError(msg)
```

- [ ] **Step 3: Update workspace_init in cli.py**

Remove the `--path` option. Hardcode `.qt-ai-dev-tools/` as the target. Keep all other options (box, provider, memory, cpus, hostname, display, resolution, static-ip, management-network-*):

```python
@workspace_app.command(name="init")
def workspace_init(
    box: typing.Annotated[str, typer.Option(help="Vagrant box")] = "bento/ubuntu-24.04",
    provider: typing.Annotated[str, typer.Option(help="Vagrant provider")] = "libvirt",
    memory: typing.Annotated[int, typer.Option(help="VM memory in MB")] = 4096,
    cpus: typing.Annotated[int, typer.Option(help="VM CPUs")] = 4,
    hostname: typing.Annotated[str, typer.Option(help="VM hostname")] = "qt-dev",
    display: typing.Annotated[str, typer.Option(help="X display")] = ":99",
    resolution: typing.Annotated[str, typer.Option(help="Display resolution")] = "1920x1080x24",
    static_ip: typing.Annotated[str, typer.Option("--static-ip", help="Static IP for VM")] = "",
    management_network_name: typing.Annotated[str, typer.Option(help="Libvirt management network name")] = "default",
    management_network_address: typing.Annotated[
        str, typer.Option(help="Libvirt management network subnet (CIDR)")
    ] = "192.168.122.0/24",
) -> None:
    """Initialize workspace in .qt-ai-dev-tools/ with Vagrantfile and provision.sh."""
    from qt_ai_dev_tools.vagrant.workspace import WorkspaceConfig, render_workspace

    if provider == "virtualbox":
        typer.echo("WARNING: VirtualBox provider is NOT TESTED. Only libvirt has been verified.", err=True)

    target = Path(".qt-ai-dev-tools")

    config = WorkspaceConfig(
        box=box,
        provider=provider,
        memory=memory,
        cpus=cpus,
        hostname=hostname,
        management_network_name=management_network_name,
        management_network_address=management_network_address,
        static_ip=static_ip,
        display=display,
        resolution=resolution,
    )
    created = render_workspace(target, config)
    for f in created:
        typer.echo(f"  Created: {f}")
    typer.echo(f"\nWorkspace initialized in {target}/")
    typer.echo("→ Review Vagrantfile for your network setup (static IP, DHCP range).")
    typer.echo("→ Add .qt-ai-dev-tools/ to .gitignore if this is a personal/local setup.")
    typer.echo("→ Run: qt-ai-dev-tools vm up")
```

- [ ] **Step 4: Update tests**

In `tests/unit/test_vm.py`, update `find_workspace` tests to look for `.qt-ai-dev-tools/Vagrantfile` instead of just `Vagrantfile`. Read the current tests first to understand what to change.

In `tests/unit/test_workspace.py`, tests pass `tmp_path` to `render_workspace()` — these don't need changes since `render_workspace()` itself isn't changing (it takes any target path).

- [ ] **Step 5: Run tests**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_vm.py tests/unit/test_workspace.py -v -p xdist -p timeout`
Expected: All tests pass.

- [ ] **Step 6: Run linter**

Run: `uv run poe lint_full`

- [ ] **Step 7: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py src/qt_ai_dev_tools/vagrant/vm.py tests/unit/test_vm.py
git commit -m "feat: change workspace directory to .qt-ai-dev-tools/, remove --path option"
```

---

### Task 3: `--dry-run` auto-enables `-v`

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py:30-77` (main_callback)
- Modify: `tests/integration/test_verbose_dryrun.py`

- [ ] **Step 1: Read current code**

Read `src/qt_ai_dev_tools/cli.py:30-77` and `tests/integration/test_verbose_dryrun.py`.

- [ ] **Step 2: Add integration test**

In `tests/integration/test_verbose_dryrun.py`, add a test to the `TestDryRunPreventsExecution` class:

```python
def test_dry_run_auto_enables_verbose(self) -> None:
    """--dry-run without -v should still show command on stderr."""
    result = subprocess.run(
        ["uv", "run", "qt-ai-dev-tools", "--dry-run", "vm", "status"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # --dry-run should auto-enable -v, so stderr should show the command
    assert "[dry-run]" in result.stderr or "dry-run" in result.stderr.lower()
```

- [ ] **Step 3: Implement in main_callback**

In `src/qt_ai_dev_tools/cli.py`, in the `main_callback` function, add auto-verbose logic after the existing code. Insert these lines after `if dry_run:` block:

```python
    if dry_run:
        set_dry_run(enabled=True)
        if verbose == 0:
            verbose = 1
            setup_stderr_logging(level=logging.INFO)
```

This replaces the current separate blocks. The full logic becomes:

```python
    # Stderr logging only when -v/-vv is given (or auto-enabled by --dry-run)
    if dry_run and verbose == 0:
        verbose = 1  # --dry-run auto-enables -v

    if verbose >= 2:
        setup_stderr_logging(level=logging.DEBUG)
    elif verbose >= 1:
        setup_stderr_logging(level=logging.INFO)

    if dry_run:
        set_dry_run(enabled=True)

    if silent:
        set_silent(enabled=True)
```

- [ ] **Step 4: Run tests**

Run integration tests (these need DISPLAY but can run in VM):
`uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/integration/test_verbose_dryrun.py -v"`

Or run unit tests for the run module:
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_run.py -v -p xdist -p timeout`

- [ ] **Step 5: Run linter**

Run: `uv run poe lint_full`

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py tests/integration/test_verbose_dryrun.py
git commit -m "feat: --dry-run auto-enables -v for command visibility"
```

---

### Task 4: Skill references in `--help` epilogs

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py` (multiple Typer instances)

- [ ] **Step 1: Read current Typer definitions**

Read `src/qt_ai_dev_tools/cli.py` and find all `typer.Typer(` calls and `app.add_typer(` calls. Note the current `help=` text for each.

- [ ] **Step 2: Add epilog to top-level app**

Change the top-level app definition:

```python
app = typer.Typer(
    name="qt-ai-dev-tools",
    help="AI agent tools for Qt/PySide app interaction via AT-SPI.",
    no_args_is_help=True,
    context_settings=_CONTEXT,
    epilog="Skills: qt-dev-tools-setup, qt-app-interaction, qt-form-and-input, "
    "qt-desktop-integration, qt-runtime-eval. "
    "Install: npx -y skills add quick-brown-foxxx/qt-ai-dev-tools",
)
```

- [ ] **Step 3: Add epilog to sub-command groups**

Update each Typer sub-app with a relevant skill reference:

```python
workspace_app = typer.Typer(
    help="Manage qt-ai-dev-tools workspaces.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-dev-tools-setup",
)

vm_app = typer.Typer(
    help="Manage Vagrant VM lifecycle.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-dev-tools-setup",
)

bridge_app = typer.Typer(
    help="Manage bridge lifecycle.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-runtime-eval",
)

clipboard_app = typer.Typer(
    help="Clipboard operations.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-form-and-input",
)

file_dialog_app = typer.Typer(
    help="File dialog automation.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-form-and-input",
)

tray_app_cli = typer.Typer(
    help="System tray interaction.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-desktop-integration",
)

notify_app_cli = typer.Typer(
    help="Desktop notification interaction.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-desktop-integration",
)

audio_app_cli = typer.Typer(
    help="PipeWire audio interaction.",
    context_settings=_CONTEXT,
    epilog="More info in skill: qt-desktop-integration",
)
```

Also add epilog to the `eval` command itself (it's a top-level command, not a sub-app):

In the `@app.command(name="eval")` decorator, add `epilog` — but typer commands don't support `epilog` on `@app.command()`. Instead, append to the docstring:

```python
@app.command(name="eval")
def eval_cmd(...) -> None:
    """Evaluate Python code inside a running Qt app via the bridge.

    More info in skill: qt-runtime-eval
    """
```

- [ ] **Step 4: Run linter**

Run: `uv run poe lint_full`

- [ ] **Step 5: Verify --help output manually**

```bash
uv run qt-ai-dev-tools --help
uv run qt-ai-dev-tools vm --help
uv run qt-ai-dev-tools clipboard --help
```

Confirm epilog appears at bottom of each help output.

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "feat: add skill references to CLI --help epilogs"
```

---

### Task 5: Helper instructions after `workspace init`

Already implemented in Task 2 (the workspace_init function prints helper instructions). This task is a no-op — skip it.

---

### Task 6: Docs — X11-only, Python+Qt focus, host/VM command parity

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Read current README and CLAUDE.md**

Read `README.md` and `CLAUDE.md` to find places to add X11/platform notes.

- [ ] **Step 2: Update README**

In the intro paragraph ("Chrome Dev Tools but for..."), add "X11" specificity:

```markdown
Chrome Dev Tools but for Linux Qt desktop apps — give your AI agent eyes and hands to inspect, click, type, and screenshot any Qt/PySide application on Linux (X11).
```

In the "How it works" section, after the architecture diagram, replace:

```markdown
CLI allows to execute any commands in VM, simplifying ssh connection.
```

with:

```markdown
Most CLI commands work identically from the host or inside the VM — no SSH wrapping needed. Use `vm run` only for arbitrary commands (pytest, systemctl, etc.).

**Note:** This toolkit targets X11 applications. Wayland is not supported. All interaction happens inside the VM where Xvfb provides the X11 display server, so the host's display server doesn't matter.
```

- [ ] **Step 3: Update CLAUDE.md**

In the "Key technical facts" section, find the bullet about "Transparent VM proxy" and replace it. Change:

```markdown
- **Transparent VM proxy** — UI commands (tree, click, type, screenshot, etc.) auto-detect host vs VM via the `QT_AI_DEV_TOOLS_VM=1` env var (set inside the VM). On the host, they proxy through SSH to the VM. No `vm run` wrapping needed for qt-ai-dev-tools commands. Use `vm run` only for arbitrary commands (pytest, systemctl, etc.).
```

to:

```markdown
- **Host/VM command parity** — UI commands (tree, click, type, screenshot, etc.) work identically from the host or inside the VM. On the host, they execute via SSH automatically. No `vm run` wrapping needed for qt-ai-dev-tools commands. Use `vm run` only for arbitrary commands (pytest, systemctl, etc.). Detection is via `QT_AI_DEV_TOOLS_VM=1` env var set inside the VM.
- **X11-only** — The toolkit targets X11 applications via Xvfb in the VM. Wayland is not supported. The host's display server doesn't matter — everything runs in the VM's virtual X11 display.
```

Also in the CLI usage section, replace "UI commands auto-detect host vs VM and proxy transparently" with "UI commands work the same from host or VM — no SSH wrapping needed".

Also update the workspace/VM path references to use `.qt-ai-dev-tools/` directory if Task 2 has been completed.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: add X11-only note, replace 'transparent proxy' with simpler language"
```

---

### Task 7: Clean up "transparent proxy" in skills

**Files:**
- Modify: `skills/qt-dev-tools-setup/SKILL.md`
- Modify: `skills/qt-app-interaction/SKILL.md`
- Modify: `skills/qt-form-and-input/SKILL.md`
- Modify: `skills/qt-desktop-integration/SKILL.md`
- Modify: `skills/qt-runtime-eval/SKILL.md`

- [ ] **Step 1: Search for proxy language across all skills**

Grep for "proxy", "auto-detect", "auto-proxy", "transparent" across all skill files.

- [ ] **Step 2: Replace with simpler language**

In every skill file, replace mentions of "auto-proxy", "transparent proxy", "auto-detect host vs VM" with:

**Standard replacement phrase:** "Commands work the same from host and VM — no SSH wrapping needed. Use `vm run` only for arbitrary commands (pytest, systemctl, etc.)."

Or shorter where inline: "works from host or VM".

- [ ] **Step 3: Commit**

```bash
git add skills/
git commit -m "docs(skills): replace 'transparent proxy' with simpler host/VM parity language"
```

---

### Task 8: Update skills/README for uvx-first, install-and-own

**Files:**
- Modify: `README.md`
- Modify: `skills/qt-dev-tools-setup/SKILL.md`

- [ ] **Step 1: Read current README manual installation section and setup skill Step 1**

- [ ] **Step 2: Update README manual installation**

Replace the manual installation section. Drop pip entirely:

```markdown
### Manual installation

**Recommended — use via uvx** (no installation needed):
```bash
uvx qt-ai-dev-tools workspace init
```

**Advanced — local copy** (you own and maintain the code):
```bash
uvx qt-ai-dev-tools install-and-own ./qt-ai-dev-tools --yes-I-will-maintain-it
```
```

- [ ] **Step 3: Update README project status distribution line**

Change:

```markdown
- Distribution — `uvx qt-ai-dev-tools <any-command>` without install, `uvx qt-ai-dev-tools init` (shadcn-style), five AI skills
```

to:

```markdown
- Distribution — `uvx qt-ai-dev-tools <any-command>` without installation, `install-and-own` for local copies, five AI skills
```

- [ ] **Step 4: Update setup skill Step 1**

In `skills/qt-dev-tools-setup/SKILL.md`, update the installation step to lead with uvx, position install-and-own as advanced:

```markdown
## Step 1: Install the toolkit

**Option A — use via uvx** (recommended, no installation needed):
```bash
uvx qt-ai-dev-tools workspace init
```
This runs directly without installing anything. All `qt-ai-dev-tools` commands work via `uvx qt-ai-dev-tools <command>`.

**Option B — local copy** (advanced, you own the code):
```bash
uvx qt-ai-dev-tools install-and-own ./qt-ai-dev-tools --yes-I-will-maintain-it
cd qt-ai-dev-tools
uv sync
```
This copies the full toolkit source into your project. You own and maintain it.
```

Remove any `pip install qt-ai-dev-tools` references.

- [ ] **Step 5: Commit**

```bash
git add README.md skills/qt-dev-tools-setup/SKILL.md
git commit -m "docs: uvx-first installation, drop pip, introduce install-and-own"
```

---

### Task 9: Vagrantfile editing warning in setup skill

**Files:**
- Modify: `skills/qt-dev-tools-setup/SKILL.md`

- [ ] **Step 1: Read current Step 2 of setup skill**

- [ ] **Step 2: Add Vagrantfile review warning**

In `skills/qt-dev-tools-setup/SKILL.md`, in Step 2 (Initialize workspace), add a prominent warning after the command:

```markdown
## Step 2: Initialize workspace

Generate Vagrantfile and provision.sh:

```bash
qt-ai-dev-tools workspace init
```

This creates `.qt-ai-dev-tools/Vagrantfile` and `.qt-ai-dev-tools/provision.sh`.

**⚠ Review the Vagrantfile before proceeding.** You may need to adjust:
- `--static-ip` if DHCP is unreliable on your network (common with libvirt)
- `--memory` and `--cpus` for your machine's resources
- Network configuration for your libvirt setup

If this is a personal/local setup (not shared across the team), add `.qt-ai-dev-tools/` to `.gitignore`.
```

- [ ] **Step 3: Commit**

```bash
git add skills/qt-dev-tools-setup/SKILL.md
git commit -m "docs(skills): add Vagrantfile review warning to setup skill Step 2"
```

---

## Execution Notes

- **Task dependencies:** Task 1 (rename) and Task 2 (workspace dir) should run first — Tasks 6, 7, 8, 9 reference the new names and paths. Task 3 and Task 4 are fully independent.
- **Parallel groups:**
  - Group A (run first): Tasks 1, 2, 3, 4 — all modify different parts of cli.py but Task 1 and 2 both touch cli.py so run them sequentially.
  - Group B (after Group A): Tasks 6, 7, 8, 9 — docs only, can run in parallel.
- **Task 5 is a no-op** — workspace init helper instructions are in Task 2.
- **Lint after every code task** — `uv run poe lint_full` must pass.
- **Unit tests run on host** — use `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/ -v -p xdist -p timeout`.
