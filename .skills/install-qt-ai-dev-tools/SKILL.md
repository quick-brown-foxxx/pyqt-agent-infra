---
name: install-qt-ai-dev-tools
description: Set up qt-ai-dev-tools in a Qt/PySide project for agent-driven UI interaction
---

# Installing qt-ai-dev-tools

## When to use

You are working on a Qt/PySide6 project and need to inspect, interact with, or test the UI programmatically. You want an AI agent (yourself) to be able to see the widget tree, click buttons, type text, read labels, and take screenshots -- the equivalent of Chrome DevTools but for Qt desktop apps.

## Prerequisites

- **Linux host** (Fedora, Ubuntu, Arch, etc.). This tool uses AT-SPI and xdotool which are Linux-only.
- **uv** package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Vagrant** installed with either **libvirt** (recommended on Linux) or **VirtualBox** as the provider.
  - For libvirt: `vagrant`, `vagrant-libvirt`, `qemu`, `libvirt` packages.
  - For VirtualBox: `vagrant`, `virtualbox` packages.
- The Qt/PySide6 project you want to test.

## Setup steps

### Step 1: Install the toolkit

Install qt-ai-dev-tools as a CLI tool:

```bash
pip install qt-ai-dev-tools
```

Or use uvx to run without installing:

```bash
uvx qt-ai-dev-tools --help
```

### Step 2: Initialize workspace

Run `workspace init` inside your project directory. This generates a Vagrantfile, provision.sh, and helper scripts from templates.

Default configuration (4GB RAM, 4 CPUs, libvirt):

```bash
qt-ai-dev-tools workspace init --path .
```

Custom VM resources:

```bash
qt-ai-dev-tools workspace init --path . --memory 8192 --cpus 8
```

VirtualBox instead of libvirt:

```bash
qt-ai-dev-tools workspace init --path . --provider virtualbox
```

With a static IP (avoids DHCP issues on libvirt):

```bash
qt-ai-dev-tools workspace init --path . --static-ip 192.168.121.100
```

This creates:
- `Vagrantfile` -- VM definition (Ubuntu 24.04, Xvfb, openbox, AT-SPI)
- `provision.sh` -- VM setup script (installs PySide6, pytest, AT-SPI deps)
- `scripts/vm-run.sh` -- run commands inside the VM
- `scripts/screenshot.sh` -- take screenshots and copy to host

### Step 3: Fix libvirt DHCP (libvirt only, one-time)

The vagrant-libvirt plugin has a known bug where the default network DHCP range starts at .1 (the host bridge IP), causing dnsmasq to fail. Fix this before first `vm up`:

```bash
# Check if the network already exists with correct config
virsh -c qemu:///system net-dumpxml vagrant-libvirt 2>/dev/null

# If it doesn't exist or has wrong DHCP range, recreate:
cat > /tmp/vagrant-libvirt-net.xml << 'EOF'
<network>
  <name>vagrant-libvirt</name>
  <forward mode="nat"/>
  <bridge name="virbr1" stp="on" delay="0"/>
  <ip address="192.168.121.1" netmask="255.255.255.0">
    <dhcp>
      <range start="192.168.121.2" end="192.168.121.254"/>
    </dhcp>
  </ip>
</network>
EOF
virsh -c qemu:///system net-define /tmp/vagrant-libvirt-net.xml
virsh -c qemu:///system net-start vagrant-libvirt
```

Skip this step if using VirtualBox.

### Step 4: Start the VM

```bash
qt-ai-dev-tools vm up
```

First boot takes ~10 minutes (box download + provisioning). Subsequent boots are ~30 seconds.

Monitor progress -- provisioning installs Xvfb, openbox, AT-SPI, PySide6, and configures systemd services.

### Step 5: Verify the environment

Check that all services are running:

```bash
qt-ai-dev-tools vm status
```

Check that AT-SPI bus is accessible:

```bash
qt-ai-dev-tools vm run "qt-ai-dev-tools apps"
```

This should list AT-SPI applications on the bus. If no apps are listed, that is OK -- it just means no Qt app is running yet. The important thing is that the command succeeds without errors.

Take a test screenshot to verify Xvfb display:

```bash
qt-ai-dev-tools vm run "qt-ai-dev-tools screenshot -o /tmp/test.png"
```

### Step 6: Launch your Qt app

Sync your project files to the VM and start your app:

```bash
# Sync files
qt-ai-dev-tools vm sync

# Start the app in the background
qt-ai-dev-tools vm run "python3 /vagrant/your_app.py &"

# Wait for it to appear on AT-SPI bus
qt-ai-dev-tools vm run "qt-ai-dev-tools wait --app your_app.py --timeout 15"
```

### Step 7: Confirm interaction works

Dump the widget tree to verify the app is visible to AT-SPI:

```bash
qt-ai-dev-tools vm run "qt-ai-dev-tools tree"
```

You should see output like:

```
[application] "your_app.py"
  [frame] "My App" @(720,387 480x320)
    [filler] ""
      [label] "Ready" @(736,403 448x14)
      [push button] "Save" @(1104,429 80x22)
```

Take a screenshot to visually confirm:

```bash
qt-ai-dev-tools vm run "qt-ai-dev-tools screenshot -o /tmp/verify.png"
```

## Verification checklist

After setup, confirm ALL of these work:

1. `qt-ai-dev-tools vm status` -- shows VM running
2. `qt-ai-dev-tools vm run "qt-ai-dev-tools apps"` -- executes without error
3. `qt-ai-dev-tools vm run "qt-ai-dev-tools screenshot"` -- produces a PNG file
4. After launching your app: `qt-ai-dev-tools vm run "qt-ai-dev-tools tree"` -- shows widget tree
5. After launching your app: `qt-ai-dev-tools vm run "qt-ai-dev-tools click --role 'push button' --name 'YourButton'"` -- clicks a button

## Keeping files in sync

When you edit source files on the host, sync them to the VM before running:

```bash
qt-ai-dev-tools vm sync
```

For automatic sync (watches for file changes):

```bash
qt-ai-dev-tools vm sync-auto
```

## Running commands inside the VM

All qt-ai-dev-tools CLI commands that inspect or interact with the UI must run inside the VM. Use `vm run`:

```bash
qt-ai-dev-tools vm run "qt-ai-dev-tools tree"
qt-ai-dev-tools vm run "qt-ai-dev-tools click --role 'push button' --name 'Save'"
qt-ai-dev-tools vm run "qt-ai-dev-tools screenshot -o /tmp/shot.png"
qt-ai-dev-tools vm run "pytest /vagrant/tests/ -v"
```

Workspace management commands (`workspace init`, `vm up`, `vm status`, `vm sync`) run on the host.

## Troubleshooting

### DHCP timeout / VM won't get an IP address

**Symptom:** `vm up` hangs at "Waiting for machine to get an IP address..."

**Fix:** The vagrant-libvirt DHCP bug. Follow Step 3 above to recreate the network with correct DHCP range. Then destroy and recreate the VM:

```bash
qt-ai-dev-tools vm destroy
qt-ai-dev-tools vm up
```

### PySide6 import error in VM

**Symptom:** `ImportError: libEGL.so.1: cannot open shared object file`

**Fix:** Provision may have missed a dependency. SSH in and install:

```bash
qt-ai-dev-tools vm ssh
sudo apt-get install -y libegl1 libxkbcommon0
```

### AT-SPI not seeing the app

**Symptom:** `qt-ai-dev-tools tree` shows nothing or "App not found"

**Causes and fixes:**
- **App not running:** Launch it with `vm run "python3 /vagrant/app.py &"` and wait: `vm run "qt-ai-dev-tools wait --app app.py"`
- **Xvfb not running:** Check with `vm run "pgrep Xvfb"`. If not running: `vm run "sudo systemctl start xvfb"`
- **AT-SPI bus not active:** Check with `vm run "pgrep at-spi"`. Restart the desktop session: `vm run "systemctl --user restart desktop-session"`
- **Wrong DISPLAY:** Ensure the app runs on `:99`. The VM environment sets this automatically but custom scripts may need `DISPLAY=:99`

### App crashes silently in VM

**Symptom:** App seems to start but immediately exits.

**Debug:** Run the app in foreground to see errors:

```bash
qt-ai-dev-tools vm run "DISPLAY=:99 python3 /vagrant/your_app.py"
```

### Screenshot is blank or shows only desktop

**Symptom:** Screenshot shows openbox desktop but no app window.

**Fix:** The app window may not be focused or may be minimized. Try:

```bash
qt-ai-dev-tools vm run "qt-ai-dev-tools tree"  # check if app is in the tree
qt-ai-dev-tools vm run "xdotool search --name 'YourAppTitle' windowactivate"
```

## Teardown

When done with the VM:

```bash
qt-ai-dev-tools vm destroy
```

This removes the VM completely. To just stop it (preserving state):

```bash
qt-ai-dev-tools vm run "sudo shutdown -h now"
```
