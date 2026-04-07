# Real-World Qt App Validation: Setup Reference

Quick reference for installing and testing real Qt apps in the VM.

## AT-SPI Bus Setup (Required for Qt5)

Qt5 apps need the `AT_SPI_BUS` X root window property. Qt6 (PySide6) does not. Set once per Xvfb session:

```bash
ATSPI_ADDR=$(dbus-send --session --dest=org.a11y.Bus --print-reply \
  /org/a11y/bus org.a11y.Bus.GetAddress 2>/dev/null | \
  grep 'string "' | sed 's/.*string "//;s/"//')
xprop -root -f AT_SPI_BUS 8s -set AT_SPI_BUS "$ATSPI_ADDR"
```

**Note:** This is now handled automatically by the VM provisioning script (ISSUE-014 fix).

## SpeedCrunch

```bash
# Install
sudo apt-get update && sudo apt-get install -y speedcrunch

# Launch
nohup speedcrunch &>/dev/null &

# AT-SPI app name: "SpeedCrunch" (Qt 5.15.13)

# Kill
pkill speedcrunch
```

## KeePassXC

```bash
# Install
sudo apt-get update && sudo apt-get install -y keepassxc

# Launch
nohup keepassxc &>/dev/null &

# AT-SPI app name: "KeePassXC" (Qt 5.15.13, version 2.7.6)

# Kill
pkill keepassxc
```

## Environment Notes

- No extra env vars needed beyond what `vm run` provides (`DISPLAY=:99`, `QT_ACCESSIBILITY=1`, `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1`, `DBUS_SESSION_BUS_ADDRESS`)
- Both apps are Qt5 (5.15.13) -- typical for packaged Ubuntu 24.04 apps
- AT-SPI registration takes ~2-3 seconds after launch
- Use `qt-ai-dev-tools apps` to verify app visibility
- Use `qt-ai-dev-tools tree --app <name>` to inspect widget hierarchy
