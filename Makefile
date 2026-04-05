.PHONY: up provision ssh sync run test test-unit test-vm test-e2e test-cli test-atspi screenshot destroy help status lint lint-fix workspace-init setup

SHELL := /bin/bash

setup: ## initial project setup
	bash scripts/setup.sh

help: ## show this message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── Workspace ───────────────────────────────────────────────────────────────

workspace-init: ## generate Vagrantfile, provision.sh, scripts from templates
	uv run qt-ai-dev-tools workspace init --path .

# ── VM lifecycle ────────────────────────────────────────────────────────────

up: ## start VM (~10 min first time)
	uv run qt-ai-dev-tools vm up

sync: ## sync files to VM (rsync)
	uv run qt-ai-dev-tools vm sync

provision: ## re-run VM provisioning
	vagrant provision

ssh: ## SSH into VM
	uv run qt-ai-dev-tools vm ssh

status: ## check Xvfb, openbox, AT-SPI status
	uv run qt-ai-dev-tools vm run "echo '=== Xvfb ===' && systemctl is-active xvfb && echo '=== Desktop session ===' && systemctl --user is-active desktop-session && echo '=== AT-SPI ===' && python3 -c 'import gi; gi.require_version(\"Atspi\",\"2.0\"); from gi.repository import Atspi; d=Atspi.get_desktop(0); print(f\"Apps on bus: {d.get_child_count()}\")'"

destroy: ## destroy VM and clean up
	uv run qt-ai-dev-tools vm destroy

# ── App ─────────────────────────────────────────────────────────────────────

run: ## launch app in VM (headless)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run python3 app/main.py &"
	sleep 1
	uv run qt-ai-dev-tools screenshot --output /tmp/app-running.png
	@echo "Screenshot: /tmp/app-running.png"

# ── Tests ────────────────────────────────────────────────────────────────────
#
# Hierarchy:
#   test           = everything (VM tests + host proxy tests) — the default
#   ├── test-vm    = all tests that run inside the VM
#   │   ├── test-unit  (parallel via xdist, also works on host)
#   │   ├── test-e2e   (serial, real apps + AT-SPI + bridge)
#   │   └── test-cli   (serial, CLI integration)
#   └── host-side proxy tests (bridge proxy, runs from host)
#
# Subsets for focused work:
#   test-unit      = unit tests only (fast, no VM needed)
#   test-e2e       = e2e tests only
#   test-cli       = CLI integration only
#   test-atspi     = AT-SPI smoke tests only

test: ## all tests — VM + host proxy, zero skips
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/unit/ tests/test_main.py -v -n auto && uv run pytest tests/e2e/ tests/integration/ -v"
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/e2e/test_bridge_proxy.py -v -p timeout --timeout=120

test-vm: ## all VM tests: unit parallel + e2e/integration serial
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/unit/ tests/test_main.py -v -n auto && uv run pytest tests/e2e/ tests/integration/ -v"

test-unit: ## unit tests only (parallel, no VM needed)
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/ -v -n auto -p xdist -p timeout

test-e2e: ## e2e tests only (requires VM + Xvfb)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/ -v"

test-cli: ## CLI integration tests only (requires VM + Xvfb)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/integration/ -v"

test-atspi: ## AT-SPI smoke tests only
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -v -k atspi"

# ── Lint ─────────────────────────────────────────────────────────────────────

lint: ## run linters (ruff check + basedpyright)
	uv run basedpyright src/
	uv run ruff check src/ tests/

lint-fix: ## run linters with auto-fix
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# ── Debug ─────────────────────────────────────────────────────────────────────

screenshot: ## screenshot current VM display
	uv run qt-ai-dev-tools screenshot --output /tmp/vm-current.png
