.PHONY: up provision ssh sync run test test-full screenshot destroy help status lint lint-fix test-cli workspace-init

SHELL := /bin/bash

# Scripts are generated from templates via `qt-ai-dev-tools workspace init`.
# VM commands also have CLI equivalents: `qt-ai-dev-tools vm up|status|ssh|sync|destroy`.
VM_RUN := ./scripts/vm-run.sh
SCREENSHOT := ./scripts/screenshot.sh

help: ## show this message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## start VM (first time: ~10 min)  [CLI: qt-ai-dev-tools vm up]
	vagrant up --provider=libvirt
	chmod +x scripts/vm-run.sh scripts/screenshot.sh

sync: ## sync files to VM (rsync)  [CLI: qt-ai-dev-tools vm sync]
	vagrant rsync

provision: ## re-run provisioning
	vagrant provision

ssh: ## SSH into VM  [CLI: qt-ai-dev-tools vm ssh]
	vagrant ssh

run: ## launch app in VM (headless)
	$(VM_RUN) "python3 /vagrant/app/main.py &"
	sleep 1
	$(SCREENSHOT) /tmp/app-running.png
	@echo "Screenshot: /tmp/app-running.png"

# ── Workspace ───────────────────────────────────────────────────────────────

workspace-init: ## regenerate Vagrantfile, provision.sh, scripts from templates
	uv run python -c "from pathlib import Path; from qt_ai_dev_tools.vagrant.workspace import render_workspace; [print(f'  {p}') for p in render_workspace(Path('.'))]"

# ── Tests ────────────────────────────────────────────────────────────────────

test: ## fast pytest-qt tests (offscreen, no Xvfb)
	$(VM_RUN) "cd /vagrant && QT_QPA_PLATFORM=offscreen uv run pytest tests/test_main.py -v -k 'not atspi and not scrot'"

test-full: ## full tests including AT-SPI, screenshot, and CLI (requires Xvfb)
	$(VM_RUN) "cd /vagrant && uv run pytest tests/ -v"

test-atspi: ## AT-SPI smoke test only
	$(VM_RUN) "cd /vagrant && uv run pytest tests/ -v -k atspi"

test-cli: ## CLI integration tests only
	$(VM_RUN) "cd /vagrant && uv run pytest tests/integration/ -v"

# ── Lint ─────────────────────────────────────────────────────────────────────

lint: ## run linters (ruff check + basedpyright)
	uv run basedpyright src/
	uv run ruff check src/ tests/

lint-fix: ## run linters with auto-fix
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# ── Debug ─────────────────────────────────────────────────────────────────────

screenshot: ## screenshot current VM display
	$(SCREENSHOT) /tmp/vm-current.png

status: ## check Xvfb, openbox, AT-SPI status  [CLI: qt-ai-dev-tools vm status]
	$(VM_RUN) "echo '=== Xvfb ===' && systemctl is-active xvfb && echo '=== Desktop session ===' && systemctl --user is-active desktop-session && echo '=== AT-SPI ===' && python3 -c 'import gi; gi.require_version(\"Atspi\",\"2.0\"); from gi.repository import Atspi; d=Atspi.get_desktop(0); print(f\"Apps on bus: {d.get_child_count()}\")'"

destroy: ## destroy VM and clean up  [CLI: qt-ai-dev-tools vm destroy]
	vagrant destroy -f
	rm -f .vagrant-ssh-config
