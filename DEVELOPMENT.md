# Development

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for package management
- Vagrant + libvirt (for VM-based tests only)

## Setup

```bash
git clone https://github.com/quick-brown-foxxx/qt-ai-dev-tools.git
cd qt-ai-dev-tools
make setup    # runs uv sync + pre-commit install
```

## Make targets

`make workspace-init` must run before VM-dependent targets (generates Vagrantfile and provision.sh from templates).

| Target | What it does |
|--------|-------------|
| `make setup` | Initial project setup (uv sync + pre-commit install) |
| `make help` | Show available make targets |
| `make workspace-init` | Generate Vagrantfile, provision.sh, scripts from templates |
| `make up` | Start the VM (~10 min first time) |
| `make provision` | Re-run VM provisioning |
| `make ssh` | SSH into VM |
| `make sync` | Sync files to VM (rsync) |
| `make run` | Launch app in VM (headless) + screenshot |
| `make status` | Check Xvfb, openbox, AT-SPI in VM |
| `make destroy` | Destroy VM and clean up |
| `make test` | Fast offscreen pytest-qt tests (no VM needed) |
| `make test-full` | All tests including AT-SPI, screenshots, CLI |
| `make test-cli` | CLI integration tests only |
| `make test-atspi` | AT-SPI smoke test only |
| `make test-e2e` | E2E bridge tests (real app in VM) |
| `make lint` | ruff check + basedpyright (strict) |
| `make lint-fix` | Auto-fix lint issues with ruff |
| `make screenshot` | Capture current VM display |

## Architecture

See [CLAUDE.md](CLAUDE.md) for full project orientation — package structure, module responsibilities, key technical facts, coding standards, and workflow.

## Docs

- [PHILOSOPHY.md](docs/PHILOSOPHY.md) — design principles and non-negotiable coding standards
- [ROADMAP.md](docs/ROADMAP.md) — phases, priorities, and task tracking
