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
| `make lint` | ruff check + basedpyright (strict) |
| `make lint-fix` | Auto-fix lint issues |
| `make test` | Fast offscreen pytest-qt tests (no VM needed) |
| `make test-full` | All tests including AT-SPI, screenshots, CLI |
| `make test-cli` | CLI integration tests only |
| `make up` | Start the VM (~10 min first time) |
| `make status` | Check Xvfb, openbox, AT-SPI in VM |
| `make screenshot` | Capture current VM display |
| `make destroy` | Tear down VM |

## Architecture

See [CLAUDE.md](CLAUDE.md) for full project orientation — package structure, module responsibilities, key technical facts, coding standards, and workflow.

## Docs

- [PHILOSOPHY.md](docs/PHILOSOPHY.md) — design principles and non-negotiable coding standards
- [ROADMAP.md](docs/ROADMAP.md) — phases, priorities, and task tracking
