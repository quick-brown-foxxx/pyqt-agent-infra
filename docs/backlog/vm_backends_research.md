# VM Backend Research — qt-ai-dev-tools

> **Context:** `qt-ai-dev-tools` launches Qt apps inside a VM and exposes the AT-SPI accessibility layer via a Chrome DevTools–style MCP interface. Currently hardcoded to Vagrant + libvirt + QEMU on the host. This doc evaluates alternatives.

---

## Framing: The Real Problem

"No host dependencies" is a false goal. Any VM or container approach needs *some* kernel interface:

- `/dev/kvm` for hardware-accelerated VMs (unavoidable for real isolation)
- Namespace/cgroup syscalls for containers (unavoidable for any container)

The actual problem with the current stack is **two separate things** that should not be conflated:

1. **Vagrant + libvirt is heavy** — daemon dependency (`libvirtd`), Ruby runtime, full guest images, complex provisioning lifecycle
2. **The VM backend is not abstracted** — swapping it requires touching many call sites

Fix (2) first. Then (1) becomes a one-class substitution.

---

## Critical Unknown: What Is the Actual Docker Gap?

The "80% works in Docker" estimate is unvalidated and should not drive architecture decisions until the 20% is precisely characterized.

For this specific project the missing 20% is likely load-bearing:

- **AT-SPI registry** behavior differs between container and VM — the `at-spi-bus-launcher` and D-Bus session bus isolation are non-trivial to replicate in Docker
- **X11 socket passthrough** works in containers but with host display coupling — behavior under `Xvfb` inside a container vs. a VM guest differs
- **D-Bus session isolation** — Docker shares the host kernel's IPC namespace by default; you may be silently depending on host D-Bus leaking in

**Action:** Run the full test suite under rootless Podman, collect exact failure modes, then decide.

---

## Options Evaluated

### ✅ Firecracker (microVM) — Recommended

| Property | Value |
|---|---|
| Distribution | Single static Go binary |
| Host deps | `/dev/kvm` only |
| Interface | REST API over Unix socket |
| Boot time | ~125ms |
| Maintenance | Active (AWS-backed) |
| Isolation | Full kernel (real VM) |

Firecracker runs a real Linux kernel in a stripped-down VM with no PCI bus, no USB, no legacy devices — exactly what this project needs. The REST API is simple enough that a Python wrapper is ~200–300 lines.

```python
import subprocess
import requests_unixsocket  # pip install requests-unixsocket

class FirecrackerBackend:
    def __init__(self, sock="/tmp/fc.sock", binary="firecracker"):
        self.sock = sock
        self.proc = subprocess.Popen([binary, "--api-sock", sock])
        self.session = requests_unixsocket.Session()
        self._base = f"http+unix://{sock.replace('/', '%2F')}"

    def _put(self, path, body):
        return self.session.put(f"{self._base}/{path}", json=body)

    def configure_boot(self, kernel, initrd=None):
        self._put("boot-source", {"kernel_image_path": kernel})

    def start(self):
        self._put("actions", {"action_type": "InstanceStart"})
```

> ⚠️ `firecracker-python-sdk` on PyPI is abandoned. DIY wrapper is better.

**Caveats:**
- No GPU passthrough, no USB — irrelevant for AT-SPI/X11 use case
- Requires a pre-built rootfs (kernel + minimal userspace); manageable with a Makefile or build script checked into the repo

---

### ✅ systemd-nspawn — Underrated, Worth Testing First

Already installed on any systemd host (Fedora, Ubuntu, Debian). Not a new dependency.

```bash
systemd-nspawn -D /path/to/rootfs \
  --bind /tmp/.X11-unix \
  --setenv=DISPLAY=:0 \
  --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  --private-network \
  -- python3 app_under_test.py
```

Key properties relevant to this project:
- Proper D-Bus session isolation (unlike Docker)
- X11 socket passthrough via `--bind`
- No daemon required — pure subprocess call
- Rootless mode available with `--user`

This may close the Docker gap without reaching for a microVM at all. **Test this before Firecracker.**

Python wrapper: `subprocess.run(["systemd-nspawn", ...], check=True)` — trivially abstractable.

---

### ⚠️ QEMU `-M microvm` — Incremental Improvement Only

If QEMU is already installed, the `microvm` machine type strips out PCI, ACPI, and legacy devices for faster boots and lower overhead. Manageable via QMP socket from Python.

This is an improvement over the current setup without introducing new binaries, but it still requires QEMU installed on the host. Not meaningfully more portable than the current stack.

---

### ❌ Lima

macOS-first. Linux support is an afterthought. Skip.

### ❌ Multipass

Ubuntu-centric, requires a Canonical daemon. Adds a heavy dep without solving the portability problem. Skip.

### ❌ Ignite (Firecracker + containerd)

Designed for Kubernetes-adjacent workflows. Brings in containerd as a hard dep. Overkill for this use case. Skip.

### ❌ Cloud Hypervisor

Similar to Firecracker but less adoption and documentation. No meaningful advantage for this use case. Skip unless Firecracker has a specific gap.

---

## Recommended Architecture

### Backend abstraction (do this first)

```python
from abc import ABC, abstractmethod

class VMBackend(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def run_command(self, cmd: list[str]) -> tuple[int, str, str]: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def get_display(self) -> str: ...  # returns DISPLAY value

class VagrantBackend(VMBackend): ...      # current implementation
class FirecrackerBackend(VMBackend): ...  # new implementation
class NspawnBackend(VMBackend): ...       # worth testing
```

The backend is injected at startup (env var or config file). No other code changes.

### Evaluation path

```
1. Characterize Docker gap precisely
       ↓
2. Test systemd-nspawn against full test suite
       ↓ (if gap remains)
3. Prototype Firecracker backend with minimal Alpine rootfs
       ↓
4. Keep Vagrant backend behind the abstraction as fallback
```

---

## Dependency Matrix

| Backend | New binary? | Daemon? | `/dev/kvm`? | D-Bus isolation | Real kernel |
|---|---|---|---|---|---|
| Vagrant + libvirt | No | Yes (libvirtd) | Yes | ✅ | ✅ |
| Firecracker | Yes (static) | No | Yes | ✅ | ✅ |
| systemd-nspawn | No (preinstalled) | No | No | ✅ | ❌ |
| Docker/Podman | No (usually present) | Rootless: No | No | ⚠️ | ❌ |
| QEMU microvm | No (if QEMU present) | No | Yes | ✅ | ✅ |

---

## Open Questions

- [ ] What exactly fails in Docker? Run suite under `podman run --privileged` with D-Bus socket mounted and record failures
- [ ] Does `systemd-nspawn` cover the D-Bus/AT-SPI gap?
- [ ] Is `/dev/kvm` available in the CI environment? (Firecracker is a no-op without it)
- [ ] What is the minimum rootfs for the test workload? (Firecracker rootfs build time is a maintenance cost)
- [ ] Should the rootfs be pre-built and distributed, or built from a Makefile per-host?
