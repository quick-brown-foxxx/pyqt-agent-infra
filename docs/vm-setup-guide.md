# VM setup guide

qt-ai-dev-tools uses a Vagrant VM as its primary environment. The VM provides full OS isolation with Xvfb, AT-SPI, xdotool, and all dependencies pre-configured.

## Quick setup

```bash
qt-ai-dev-tools workspace init --path . --provider libvirt
qt-ai-dev-tools vm up
qt-ai-dev-tools vm status
```

First boot takes ~10 minutes (box download + provisioning). Subsequent boots are fast.

## Supported providers

### libvirt (primary)

Used on Fedora, RHEL, and immutable desktops (Silverblue, Kinoite). Requires QEMU/KVM.

**Install the vagrant-libvirt plugin:**

```bash
vagrant plugin install vagrant-libvirt
```

**DHCP bug workaround:** vagrant-libvirt creates the `vagrant-libvirt` network with a DHCP range starting at `.1`, which collides with the host bridge IP. dnsmasq cannot allocate addresses, causing DHCP timeouts on `vm up`.

Fix: pre-create the network with a corrected DHCP range:

```bash
cat > /tmp/vagrant-libvirt-net.xml << 'EOF'
<network>
  <name>vagrant-libvirt</name>
  <forward mode='nat'/>
  <bridge name='virbr1' stp='on' delay='0'/>
  <ip address='192.168.121.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.121.2' end='192.168.121.254'/>
    </dhcp>
  </ip>
</network>
EOF

virsh -c qemu:///system net-define /tmp/vagrant-libvirt-net.xml
virsh -c qemu:///system net-start vagrant-libvirt
virsh -c qemu:///system net-autostart vagrant-libvirt
```

Alternatively, use a static IP in your workspace config to bypass DHCP entirely (see VM resources section).

### VirtualBox (secondary)

Cross-platform. Install VirtualBox from your package manager or https://www.virtualbox.org/. No special network workarounds needed.

```bash
qt-ai-dev-tools workspace init --path . --provider virtualbox
qt-ai-dev-tools vm up
```

## VM resources

Defaults: 4 GB RAM, 4 CPUs. Customize at workspace init time:

```bash
qt-ai-dev-tools workspace init --memory 8192 --cpus 8
```

When to increase resources:
- Large Qt applications with many widgets
- Running multiple Qt apps simultaneously
- Running the full test suite inside the VM

## Provisioned environment

The VM is provisioned with everything needed for headless Qt interaction:

| Component | Purpose |
|-----------|---------|
| **Xvfb :99** | Virtual X11 framebuffer (1920x1080x24). All tools use `DISPLAY=:99`. |
| **Openbox** | Window manager. Required for correct xdotool coordinates and `_NET_ACTIVE_WINDOW` support. |
| **AT-SPI** | Accessibility bus via D-Bus session. Provides the widget tree (roles, names, coords). |
| **xdotool** | Mouse/keyboard input via X11 events. Used for clicks by coordinate and text input. |
| **scrot** | Screenshot capture. Output is ~14-22 KB PNG. |
| **PySide6** | Qt framework. Pre-installed in the VM. |
| **pytest, pytest-qt** | Test frameworks. |

Services auto-start on boot:
- `xvfb.service` (system) -- starts Xvfb on display :99
- `desktop-session.service` (user) -- starts openbox + at-spi-bus-launcher

## Troubleshooting

### VM won't start

- Verify the provider is installed: `vagrant plugin list` (libvirt) or `VBoxManage --version` (VirtualBox).
- For libvirt: confirm QEMU/KVM is available: `virsh -c qemu:///system list`.
- Check that the base box is compatible with your provider.

### DHCP timeout on `vm up` (libvirt)

The vagrant-libvirt DHCP bug. Either:
1. Pre-create the network with corrected range (see libvirt section above).
2. Use a static IP in workspace config to bypass DHCP.

### AT-SPI not seeing the app

- The app must run on the same display (`DISPLAY=:99`).
- The D-Bus session bus must be active. Check with: `qt-ai-dev-tools vm run "dbus-monitor --session"`.
- Verify AT-SPI is running: `qt-ai-dev-tools vm run "ps aux | grep at-spi"`.

### Screenshots are blank

- Xvfb must be running: `qt-ai-dev-tools vm run "ps aux | grep Xvfb"`.
- Openbox must be running: `qt-ai-dev-tools vm run "ps aux | grep openbox"`.
- An application must be launched and visible on display :99.

### xdotool reports wrong coordinates

- Openbox must be running. Without a window manager, `xdotool mousemove --window` uses incorrect coordinates and `windowactivate` fails.
- Verify with: `qt-ai-dev-tools vm run "pgrep openbox"`.

### Slow file sync

- Run `qt-ai-dev-tools vm sync` to manually rsync files.
- For continuous sync during development, run `vagrant rsync-auto` in a background terminal.
