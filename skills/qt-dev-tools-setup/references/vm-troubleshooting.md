# VM troubleshooting

Each entry: symptom, cause, fix.

## DHCP timeout / VM won't get IP

**Symptom:** `vm up` hangs at "Waiting for machine to get an IP address..."

**Cause:** vagrant-libvirt creates the `vagrant-libvirt` network with DHCP range starting at `.1`, which collides with the host bridge IP.

**Fix:** Recreate the network with a corrected DHCP range, then retry:

```bash
virsh -c qemu:///system net-destroy vagrant-libvirt 2>/dev/null
virsh -c qemu:///system net-undefine vagrant-libvirt 2>/dev/null

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
virsh -c qemu:///system net-autostart vagrant-libvirt

qt-ai-dev-tools vm destroy
qt-ai-dev-tools vm up
```

Alternative: use `workspace init --static-ip 192.168.121.100` to bypass DHCP entirely.

## VM won't start

**Symptom:** `vm up` fails immediately with provider errors.

**Cause:** Provider not installed or QEMU/KVM not available.

**Fix:**
- Verify plugin: `vagrant plugin list` (look for `vagrant-libvirt`)
- Verify KVM: `virsh -c qemu:///system list` (should not error)
- Install if missing: `vagrant plugin install vagrant-libvirt`

## PySide6 import error

**Symptom:** `ImportError: libEGL.so.1: cannot open shared object file`

**Cause:** Missing system libraries in the VM.

**Fix:**
```bash
qt-ai-dev-tools vm run "sudo apt-get install -y libegl1 libxkbcommon0"
```

## AT-SPI not seeing the app

**Symptom:** `tree` shows nothing or errors.

**Causes and fixes:**
- **App not running:** Launch it and wait: `vm run "python3 /vagrant/app.py &"` then `wait --app app.py`
- **Xvfb down:** Check `vm run "pgrep Xvfb"`. Restart: `vm run "sudo systemctl start xvfb"`
- **D-Bus inactive:** Check `vm run "pgrep at-spi"`. Restart: `vm run "systemctl --user restart desktop-session"`
- **Wrong DISPLAY:** App must run on `:99`. The VM sets this automatically; custom scripts may need `DISPLAY=:99`

## App crashes silently

**Symptom:** App starts but immediately exits with no output.

**Fix:** Run in foreground to see errors:
```bash
qt-ai-dev-tools vm run "python3 /vagrant/your_app.py"
```

## Screenshots blank

**Symptom:** Screenshot shows nothing or only the desktop background.

**Fix:** Verify both services are running:
```bash
qt-ai-dev-tools vm run "pgrep Xvfb"
qt-ai-dev-tools vm run "pgrep openbox"
```

If either is missing, restart:
```bash
qt-ai-dev-tools vm run "sudo systemctl start xvfb"
qt-ai-dev-tools vm run "systemctl --user restart desktop-session"
```

## xdotool wrong coordinates

**Symptom:** Clicks land in the wrong location.

**Cause:** Openbox window manager is not running. Without it, xdotool cannot resolve window-relative coordinates.

**Fix:**
```bash
qt-ai-dev-tools vm run "pgrep openbox"
qt-ai-dev-tools vm run "systemctl --user restart desktop-session"
```

## Slow file sync

**Symptom:** Changes on host not reflected in VM.

**Fix:**
- Manual sync: `qt-ai-dev-tools vm sync`
- Automatic sync: `qt-ai-dev-tools vm sync-auto` (runs in background, watches for changes)
