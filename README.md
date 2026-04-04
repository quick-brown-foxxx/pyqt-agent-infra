# qt-ai-dev-tools

Chrome DevTools for Qt desktop apps — give your AI agent eyes and hands to inspect, click, type, and screenshot any Qt/PySide application on Linux.

## The problem

AI coding agents can build Qt apps, but they can't see or interact with them. There's no equivalent of Chrome DevTools for desktop applications. When your agent writes UI code, it's flying blind — no way to verify layouts, click buttons, fill forms, or confirm that changes actually work.

## What this gives your agent

qt-ai-dev-tools bridges that gap. Your AI agent can:

- **See the full widget tree** — every button, label, text field, menu, and dialog, with roles, names, and coordinates, via the AT-SPI accessibility protocol
- **Interact with the app** — click buttons, type into fields, press keys, fill forms, navigate menus — all through real X11 input events
- **Take screenshots** — visual verification after any interaction (~14-22 KB PNG, cheap to send to an LLM)
- **Run in an isolated VM** — Vagrant VM with Xvfb, window manager, and AT-SPI pre-configured. No host contamination, reproducible environment

The agent never modifies or instruments the target app. It uses the same accessibility tree that screen readers use, from the outside.

## How it works

```
  AI Agent (Claude Code, etc.)
       |
       |  shell commands
       v
  qt-ai-dev-tools CLI
       |
       |  auto-detects host vs VM
       |  (proxies through SSH when on host)
       |
       +---> AT-SPI (widget tree: roles, names, coords, text)
       +---> xdotool (clicks, keystrokes, text input)
       +---> scrot (screenshots)
       |
  [ Vagrant VM: Ubuntu 24.04 + Xvfb + openbox + D-Bus ]
       |
       v
  Target Qt/PySide App (unmodified)
```

The CLI auto-detects whether it's running on the host or inside the VM. On the host, commands proxy transparently through SSH — the agent doesn't need to think about where things run.

## Host requirements

- **Linux** (Fedora, Ubuntu, Arch, etc.)
- **Vagrant** with the **libvirt** provider (`vagrant-libvirt` plugin + QEMU/KVM)
- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**

VirtualBox is partially supported in templates but only libvirt has been tested.

## Getting started

### 1. Install the agent skills

```bash
npx -y @anthropic-ai/claude-code skill add quick-brown-foxxx/qt-ai-dev-tools
```

This gives your agent the `qt-dev-tools-setup` and `qt-app-interaction` skills — structured guidance for setting up the environment and interacting with Qt apps.

### 2. Ask your agent to set up the toolkit

The agent will use the `qt-dev-tools-setup` skill to:
- Copy the toolkit into your project
- Initialize a Vagrant workspace
- Boot the VM and verify the environment

### 3. Start interacting

Once set up, the agent uses the `qt-app-interaction` skill for the core workflow: **inspect** the widget tree → **interact** with widgets → **verify** results. The skill includes recipes for common tasks (form filling, menu navigation, dialog handling) and troubleshooting.

### Manual installation

If you prefer to set up manually or your agent doesn't support skills, read `skills/qt-dev-tools-setup/SKILL.md` directly — it's a step-by-step guide.

## Project status

Phases 1–5 are complete (CLI, type system, Vagrant subsystem, VM improvements, agent integration). Next: Phase 6 (complex widget support, runtime code execution bridge) and Phase 7 (streamlined distribution).

See [ROADMAP.md](docs/ROADMAP.md) for the full plan.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup, make targets, and contribution guidance.

## Not to be confused with

[qt-pilot](https://github.com/neatobandit0/qt-pilot) is a different project that uses an in-process Qt test harness requiring `setObjectName()` on widgets. qt-ai-dev-tools uses AT-SPI externally, works with any Qt app without modification, and can access Linux subsystems beyond the application.
