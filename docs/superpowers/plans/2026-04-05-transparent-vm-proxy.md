# Transparent VM Proxy Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate the double-API (`vm run "qt-ai-dev-tools tree"`) by making UI commands auto-detect host vs VM and transparently proxy through SSH. Also remove redundant shell script templates.

**Architecture:** Add a `_proxy_to_vm()` check at the start of every UI command. If running on host (no DISPLAY with Xvfb, or explicit env var), reconstruct the CLI invocation from `sys.argv` and execute via `vm_run()`. Screenshot command gets special handling to SCP the file back. Remove `vm-run.sh.j2` and `screenshot.sh.j2` templates since `vm_run()` fallback path handles everything.

**Tech Stack:** Python 3.12, typer, basedpyright strict

---

## Design

### Detection: Am I in the VM?

Simple env var check. The provision.sh.j2 template already sets env vars in `.bashrc`. We add one more: `QT_AI_DEV_TOOLS_VM=1`. The `vm_run()` fallback path also sets this in its env_prefix.

```python
def _is_in_vm() -> bool:
    return os.environ.get("QT_AI_DEV_TOOLS_VM") == "1"
```

### Proxy mechanism

A function called at the top of each UI command. Uses `sys.argv` to reconstruct the command:

```python
def _proxy_to_vm(workspace: Path | None = None) -> None:
    """If on host, re-run this command inside the VM and exit."""
    if _is_in_vm():
        return  # Already in VM, proceed normally
    
    from qt_ai_dev_tools.vagrant.vm import vm_run
    cmd = "qt-ai-dev-tools " + " ".join(shlex.quote(a) for a in sys.argv[1:])
    result = vm_run(cmd, workspace)
    if result.stdout:
        typer.echo(result.stdout, nl=False)
    if result.returncode != 0 and result.stderr:
        typer.echo(result.stderr, err=True, nl=False)
    raise typer.Exit(code=result.returncode)
```

### Screenshot special case

Screenshot needs to:
1. Run scrot in VM (saves to a temp path in VM)
2. SCP the file back to host
3. Move to user-requested path

Approach: proxy runs screenshot in VM to a known temp path, then uses `vagrant scp` or `scp -F` to copy it back.

### Commands that proxy vs don't

**Proxy (13 UI commands):** tree, find, click, type, key, focus, state, text, screenshot, apps, wait, fill, do

**Don't proxy (8 infra commands):** workspace init, vm up/status/ssh/destroy/sync/sync-auto/run

---

## Task 0: Add VM detection env var to templates

**Files:**
- Modify: `src/qt_ai_dev_tools/vagrant/templates/provision.sh.j2`
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py`

- [ ] Add `export QT_AI_DEV_TOOLS_VM=1` to the .bashrc block in provision.sh.j2
- [ ] Add `QT_AI_DEV_TOOLS_VM=1` to the env_prefix in vm_run() fallback path

## Task 1: Add proxy infrastructure to cli.py

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`

- [ ] Add imports: `sys`, `shlex`, `os`
- [ ] Add `_is_in_vm()` function
- [ ] Add `_proxy_to_vm(workspace=None)` function
- [ ] Add `_proxy_screenshot(output, workspace=None)` function for screenshot special case

## Task 2: Wire up proxy to all 13 UI commands

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`

- [ ] Add `_proxy_to_vm()` as first line of: tree, find, click, type_cmd, key, focus_cmd, state, text_cmd, apps, wait_cmd, fill, do_action
- [ ] For screenshot: use `_proxy_screenshot(output)` instead

## Task 3: Remove redundant templates

**Files:**
- Delete: `src/qt_ai_dev_tools/vagrant/templates/vm-run.sh.j2`
- Delete: `src/qt_ai_dev_tools/vagrant/templates/screenshot.sh.j2`
- Modify: `src/qt_ai_dev_tools/vagrant/workspace.py` — remove from _TEMPLATES and _SHELL_SCRIPTS
- Modify: `src/qt_ai_dev_tools/vagrant/vm.py` — remove vm-run.sh script check path (always use fallback)

## Task 4: Update Makefile

**Files:**
- Modify: `Makefile`

- [ ] Remove VM_RUN and SCREENSHOT variables
- [ ] Remove check_scripts function
- [ ] Replace all `$(VM_RUN) "..."` with `uv run qt-ai-dev-tools vm run "..."`
- [ ] Replace screenshot target with `uv run qt-ai-dev-tools screenshot`
- [ ] Actually: since UI commands now auto-proxy, Makefile can use `uv run qt-ai-dev-tools tree` directly

## Task 5: Update tests

**Files:**
- Modify: `tests/unit/test_vm.py` — remove test for vm-run.sh script path
- Modify: `tests/unit/test_workspace.py` — update to expect 2 files instead of 4

## Task 6: Update docs

**Files:**
- Modify: `AGENTS.md`, `README.md`, `docs/agent-workflow.md`, skills
- [ ] Show simple commands (`qt-ai-dev-tools tree`) not wrapped in `vm run`
- [ ] Document the auto-proxy behavior
- [ ] Note: `vm run` still works for arbitrary commands
