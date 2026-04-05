# Docker as VM Replacement

**Status:** research complete, not yet implemented
**Phase:** 8 (container & host support)
**Date:** 2026-04-06

## Summary

Every subsystem used by qt-ai-dev-tools can run in a Docker container **without `--privileged`**, without systemd, and without host hardware. The entire stack (Xvfb + openbox + D-Bus session bus + AT-SPI + xdotool + scrot + PipeWire + dunst + snixembed + stalonetray) runs in userspace with only a session bus.

Key insight: the initial roadmap assumed Docker could only handle ~80% of features (UI-only). Research shows it's closer to **95%** — the only things requiring a VM are real systemd or real audio hardware, neither of which this project needs.

## Complexity Tiers

### Trivial — just apt install + start

| Subsystem | Notes |
|---|---|
| Xvfb + openbox | `Xvfb :99 &` + `openbox &`. Works everywhere incl. macOS/Windows Docker Desktop |
| xdotool + scrot | Standard apt packages |
| Clipboard (xsel) | Standard apt package |
| dunst (notifications) | `DISPLAY=:99 dunst &` — needs only session bus |

### Medium — needs careful startup ordering, but proven

| Subsystem | Notes |
|---|---|
| D-Bus session bus | `dbus-launch` or `dbus-run-session`. Use filesystem sockets (not abstract). Run as non-root to avoid `AT_SECURE` |
| AT-SPI | `at-spi-bus-launcher --launch-immediately &`. Must start after D-Bus, before Qt app. Needs `QT_ACCESSIBILITY=1` |
| PipeWire (in-container) | `pipewire &` → `wireplumber &` → `pipewire-pulse &`. Needs D-Bus session bus. Set `DISABLE_RTKIT=y`. Virtual sinks/mics work with no hardware |
| SNI tray (snixembed) | `stalonetray &` + `snixembed --fork &`. snixembed built from source (not in Ubuntu repos). All session-bus |

### Hard — but NOT needed

| Subsystem | Why hard | Why skip |
|---|---|---|
| systemd | Needs cgroup access, Podman-only or `--privileged` | Shell entrypoint replaces it entirely |
| D-Bus system bus | Needs root | Every subsystem works on session bus alone |

## Portability

| Host OS | Core (X11+AT-SPI+xdotool) | Audio (PipeWire) | Tray+Notify |
|---|---|---|---|
| Linux Docker | ✅ | ✅ in-container or host socket | ✅ |
| macOS Docker Desktop | ✅ | ✅ in-container only | ✅ |
| Windows Docker Desktop | ✅ | ✅ in-container only | ✅ |
| CI (GitHub Actions) | ✅ | ✅ virtual devices only | ✅ |

Everything runs inside the container's virtual framebuffer and session bus — host OS doesn't matter.

## Entrypoint Script Sketch

The entire VM's systemd service tree collapses to ~15 lines:

```bash
#!/bin/bash
eval $(dbus-launch --sh-syntax)
/usr/libexec/at-spi-bus-launcher --launch-immediately &
Xvfb :99 -screen 0 1280x1024x24 -ac &
sleep 0.5
DISPLAY=:99 openbox &
DISPLAY=:99 stalonetray --kludges=force_icons_size -i 24 &
snixembed --fork &
DISPLAY=:99 dunst &
DISABLE_RTKIT=y pipewire & sleep 0.3; wireplumber & sleep 0.3; pipewire-pulse &
export DISPLAY=:99
export QT_ACCESSIBILITY=1
exec "$@"
```

## Devcontainer Ecosystem

- `desktop-lite` feature provides TigerVNC + Fluxbox + D-Bus + AT-SPI — useful reference but missing openbox, xdotool, scrot, PipeWire, tray, notifications
- No official systemd, audio, or accessibility-testing features exist
- Custom Dockerfile is the right approach, using `desktop-lite` as inspiration

## Benefits Over VM

- **Startup:** seconds vs ~10 minutes
- **Portability:** macOS + Windows + CI without libvirt/QEMU
- **Layer caching:** rebuild only what changed
- **No Vagrant dependency:** simplifies host requirements
- **Devcontainer integration:** IDE support out of the box

## Implementation Notes

- Startup order matters: D-Bus → AT-SPI → Xvfb → openbox → desktop services → app
- Use `dbus-run-session` (cleaner cleanup) over `dbus-launch` where possible
- snixembed must be built from source during Docker build (same as current VM provisioning)
- `DISABLE_RTKIT=y` required for PipeWire (rtkit needs system bus)
- Consider supervisord or s6-overlay if entrypoint script becomes fragile

## References

- [devcontainers/features desktop-lite](https://github.com/devcontainers/features/tree/main/src/desktop-lite)
- [Docker-Virtual-XVFB-pipewire](https://github.com/louisoutin/Docker-Virtual-XVFB-pipewire)
- [PipeWire in Docker (Walker Griggs)](https://walkergriggs.com/2022/12/03/pipewire_in_docker/)
- [snixembed](https://sr.ht/~steef/snixembed/)
- [GNOME AT-SPI2-Core bus launcher](https://github.com/GNOME/at-spi2-core/blob/main/bus/README.md)
