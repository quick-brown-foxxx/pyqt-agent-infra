---
name: qt-dev-tools-setup
description: >
  Set up qt-ai-dev-tools for AI-driven Qt/PySide app interaction.
  Use when asked to "set up qt-ai-dev-tools", "initialize workspace",
  "configure VM for Qt testing", or when starting a new project that
  needs headless Qt UI testing. Covers installation, workspace init,
  VM boot, and environment verification.
---

# Set up qt-ai-dev-tools

Follow these steps in order. Each step must succeed before proceeding.

## Step 1: Install the toolkit

qt-ai-dev-tools is not on PyPI. Install by copying the package source into your project.

Clone or download from GitHub, then copy the package into a `qt-ai-dev-tools/` subdirectory of your project:

```bash
git clone https://github.com/quick-brown-foxxx/qt-ai-dev-tools.git /tmp/qt-ai-dev-tools
cp -r /tmp/qt-ai-dev-tools/src /tmp/qt-ai-dev-tools/pyproject.toml ./qt-ai-dev-tools/
```

Verify the CLI works:

```bash
cd qt-ai-dev-tools
uv sync
uv run qt-ai-dev-tools --help
```

Expected: help text listing available commands (tree, click, type, screenshot, vm, workspace, etc.).

**Prerequisites:** Linux host, `uv` installed, Vagrant with libvirt provider (vagrant-libvirt plugin + QEMU/KVM).

> **Note:** All commands below assume you are inside the `qt-ai-dev-tools/` directory and use `uv run` to execute. If you set up a shell alias (`alias qt-ai-dev-tools='uv run qt-ai-dev-tools'`), you can omit the `uv run` prefix.

## Step 2: Initialize workspace

Generate Vagrantfile and provision.sh from templates:

```bash
uv run qt-ai-dev-tools workspace init --path ..
```

The `--path` flag points to where Vagrantfile and provision.sh will be created -- typically the project root. Since you are inside `qt-ai-dev-tools/`, `..` refers to the project root.

Options:
- `--memory N` -- VM RAM in MB (default: 4096)
- `--cpus N` -- VM CPU count (default: 4)
- `--provider libvirt|virtualbox` -- VM provider (default: libvirt; only libvirt is tested)
- `--static-ip IP` -- static IP to bypass DHCP (avoids libvirt DHCP bug)

This creates two files in the target directory:
- `Vagrantfile` -- Ubuntu 24.04 VM with Xvfb, openbox, AT-SPI
- `provision.sh` -- installs PySide6, pytest, AT-SPI dependencies

## Step 3: Start the VM

```bash
uv run qt-ai-dev-tools vm up
```

First boot: ~10 minutes (box download + provisioning). Subsequent boots: ~30 seconds.

If the VM hangs at "Waiting for machine to get an IP address...", see `references/vm-troubleshooting.md`.

## Step 4: Verify environment

Run three checks. All must pass.

**Check 1 -- Services:**

```bash
uv run qt-ai-dev-tools vm status
```

Expected: Xvfb, openbox, and AT-SPI services listed as running.
Failure: see `references/vm-troubleshooting.md`.

**Check 2 -- AT-SPI bus:**

```bash
uv run qt-ai-dev-tools apps
```

Expected: command succeeds without errors. No apps listed is fine -- it means no Qt app is running yet.
Failure: AT-SPI bus is not accessible. See `references/vm-troubleshooting.md`.

**Check 3 -- Display:**

```bash
uv run qt-ai-dev-tools screenshot -o /tmp/test.png
```

Expected: PNG file created showing the openbox desktop.
Failure: blank or missing file means Xvfb is not running. See `references/vm-troubleshooting.md`.

## Step 5: Launch target app

Sync project files to the VM, start the app, and wait for it to register on the AT-SPI bus:

```bash
uv run qt-ai-dev-tools vm sync
uv run qt-ai-dev-tools vm run "python3 /vagrant/app/main.py &"
uv run qt-ai-dev-tools wait --app main.py --timeout 15
```

Vagrant mounts the project root as `/vagrant` inside the VM. Your app files are at `/vagrant/` plus their path relative to the project root.

Key concept: `vm run` is for arbitrary commands inside the VM. All qt-ai-dev-tools UI commands (tree, click, type, screenshot, etc.) auto-proxy to the VM -- no wrapping needed.

If the app exits immediately, run it in the foreground to see errors:

```bash
uv run qt-ai-dev-tools vm run "python3 /vagrant/app/main.py"
```

## Step 6: Confirm interaction

Verify the app is visible to AT-SPI:

```bash
uv run qt-ai-dev-tools tree
```

Expected output:

```
[application] "main.py"
  [frame] "My App" @(720,387 480x320)
    [filler] ""
      [label] "Ready" @(736,403 448x14)
      [push button] "Save" @(1104,429 80x22)
```

Take a screenshot to visually confirm:

```bash
uv run qt-ai-dev-tools screenshot -o /tmp/verify.png
```

Setup is complete when both `tree` and `screenshot` show the running app.

## File sync

Keep host files in sync with the VM:

- **Manual:** `uv run qt-ai-dev-tools vm sync` -- run before each test cycle
- **Automatic:** `uv run qt-ai-dev-tools vm sync-auto` -- watches for changes in background

## References

Detailed guides available in `references/`. Load these when you need deeper information.

- **[references/vm-troubleshooting.md](references/vm-troubleshooting.md)** -- VM and environment troubleshooting: DHCP timeout, VM won't start, PySide6 import errors, AT-SPI not seeing apps, blank screenshots, xdotool coordinate issues, slow file sync.

## Next step

Setup complete. Use the `qt-app-interaction` skill for the inspect->interact->verify workflow.
