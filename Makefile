.PHONY: up provision ssh sync test test-unit test-full test-e2e test-integration screenshot destroy help status lint-full workspace-init setup

SHELL := /bin/bash

setup: ## initial project setup
	bash scripts/setup.sh

help: ## show this message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ── Workspace ───────────────────────────────────────────────────────────────

workspace-init: ## generate Vagrantfile, provision.sh, scripts from templates
	uv run qt-ai-dev-tools workspace init

# ── VM lifecycle ────────────────────────────────────────────────────────────

up: ## start VM (~10 min first time)
	uv run qt-ai-dev-tools vm up

sync: ## sync files to VM (rsync)
	uv run qt-ai-dev-tools vm sync

provision: ## re-run VM provisioning
	cd .qt-ai-dev-tools && vagrant provision

ssh: ## SSH into VM
	uv run qt-ai-dev-tools vm ssh

status: ## check Xvfb, openbox, AT-SPI status
	uv run qt-ai-dev-tools vm run "echo '=== Xvfb ===' && systemctl is-active xvfb && echo '=== Desktop session ===' && systemctl --user is-active desktop-session && echo '=== AT-SPI ===' && python3 -c 'import gi; gi.require_version(\"Atspi\",\"2.0\"); from gi.repository import Atspi; d=Atspi.get_desktop(0); print(f\"Apps on bus: {d.get_child_count()}\")'"

destroy: ## destroy VM and clean up
	uv run qt-ai-dev-tools vm destroy

# ── App ─────────────────────────────────────────────────────────────────────

start-app: ## launch app in VM (headless)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run python3 app/main.py &"
	sleep 1
	uv run qt-ai-dev-tools screenshot --output /tmp/app-running.png
	@echo "Screenshot: /tmp/app-running.png"

# ── Tests ────────────────────────────────────────────────────────────────────

test-full: ## all tests — VM + host proxy, zero skips
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/unit/ tests/test_main.py -v -n auto -k 'not BridgeProxy' && uv run pytest tests/e2e/ tests/integration/ -v --ignore=tests/e2e/test_bridge_proxy.py"
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/e2e/test_bridge_proxy.py -v -p timeout --timeout=120

test-unit: ## unit tests only (parallel, some in vm)
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/ -v -n auto -p xdist -p timeout
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -v -k atspi && uv run pytest tests/test_main.py -v -n auto"

test-e2e: ## e2e tests only (requires VM + Xvfb)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/ -v --ignore=tests/e2e/test_bridge_proxy.py"
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/e2e/test_bridge_proxy.py -v -p timeout --timeout=120

test-integration: ## integration tests only (requires VM + Xvfb)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/integration/ -v"

# ── Lint ─────────────────────────────────────────────────────────────────────

lint-full: ## run linters with auto-fix
	uv run poe lint_full

# ── Debug ─────────────────────────────────────────────────────────────────────

screenshot: ## screenshot current VM display
	uv run qt-ai-dev-tools screenshot --output /tmp/vm-current.png
