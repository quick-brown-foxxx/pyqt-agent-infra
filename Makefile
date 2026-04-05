.PHONY: up provision ssh sync run test test-full screenshot destroy help status lint lint-fix test-cli test-e2e workspace-init setup

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
	uv run qt-ai-dev-tools vm run "python3 /vagrant/app/main.py &"
	sleep 1
	uv run qt-ai-dev-tools screenshot --output /tmp/app-running.png
	@echo "Screenshot: /tmp/app-running.png"

# ── Tests ────────────────────────────────────────────────────────────────────

test: ## fast pytest-qt tests (offscreen, no Xvfb)
	uv run qt-ai-dev-tools vm run "cd /vagrant && QT_QPA_PLATFORM=offscreen uv run pytest tests/test_main.py -v -k 'not atspi and not scrot'"

test-full: ## full tests including AT-SPI, screenshot, and CLI (requires Xvfb)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -v"

test-atspi: ## AT-SPI smoke test only
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/ -v -k atspi"

test-cli: ## CLI integration tests only
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/integration/ -v"

test-e2e: ## e2e bridge tests (real app in VM)
	uv run qt-ai-dev-tools vm run "cd /vagrant && uv run pytest tests/e2e/ -v --timeout=60"

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
