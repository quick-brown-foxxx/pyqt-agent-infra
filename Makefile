.PHONY: up provision ssh sync run test test-full screenshot destroy help status

SHELL := /bin/bash
VM_RUN := ./scripts/vm-run.sh
SCREENSHOT := ./scripts/screenshot.sh

help: ## показать это сообщение
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## поднять VM (первый раз: ~10 минут)
	vagrant up --provider=libvirt
	chmod +x scripts/vm-run.sh scripts/screenshot.sh

sync: ## синхронизировать файлы в VM (rsync)
	vagrant rsync

provision: ## перезапустить provisioning
	vagrant provision

ssh: ## зайти в VM
	vagrant ssh

run: ## запустить приложение в VM (headless)
	$(VM_RUN) "python3 /vagrant/app/main.py &"
	sleep 1
	$(SCREENSHOT) /tmp/app-running.png
	@echo "Скриншот: /tmp/app-running.png"

# ── Тесты ────────────────────────────────────────────────────────────────────

test: ## быстрые pytest-qt тесты (offscreen, без Xvfb)
	$(VM_RUN) "cd /vagrant && QT_QPA_PLATFORM=offscreen pytest tests/ -v -k 'not atspi and not scrot'"

test-full: ## полные тесты включая AT-SPI и screenshot (требует Xvfb)
	$(VM_RUN) "cd /vagrant && pytest tests/ -v"

test-atspi: ## только AT-SPI smoke test
	$(VM_RUN) "cd /vagrant && pytest tests/ -v -k atspi"

# ── Debug ─────────────────────────────────────────────────────────────────────

screenshot: ## скриншот текущего состояния VM
	$(SCREENSHOT) /tmp/vm-current.png

status: ## проверить статус Xvfb, openbox, AT-SPI
	$(VM_RUN) "echo '=== Xvfb ===' && systemctl is-active xvfb && echo '=== Desktop session ===' && systemctl --user is-active desktop-session && echo '=== AT-SPI ===' && python3 -c 'import gi; gi.require_version(\"Atspi\",\"2.0\"); from gi.repository import Atspi; d=Atspi.get_desktop(0); print(f\"Apps on bus: {d.get_child_count()}\")'"

destroy: ## удалить VM и очистить образ
	vagrant destroy -f
	rm -f .vagrant-ssh-config
