#!/usr/bin/env bash
# Run a command inside the Vagrant VM with full Qt/AT-SPI environment.
#
# Usage:
#   ./scripts/vm-run.sh "pytest /vagrant/tests/"
#   ./scripts/vm-run.sh "python3 /vagrant/app/main.py &"
#   ./scripts/vm-run.sh --sync "pytest /vagrant/tests/"   # rsync first

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Optional --sync flag
if [[ "${1:-}" == "--sync" ]]; then
    (cd "$PROJECT_ROOT" && vagrant rsync 2>&1 | tail -1) >&2
    shift
fi

# SSH config (regenerate if stale)
SSH_CONFIG="$PROJECT_ROOT/.vagrant-ssh-config"
if [[ ! -f "$SSH_CONFIG" ]] || [[ "$PROJECT_ROOT/Vagrantfile" -nt "$SSH_CONFIG" ]]; then
    echo "[vm-run] Updating SSH config..." >&2
    (cd "$PROJECT_ROOT" && vagrant ssh-config > "$SSH_CONFIG")
fi

# Environment that .bashrc would set (works in non-interactive shells too)
ENV_PREFIX='export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_ACCESSIBILITY=1 QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus";'

ssh -F "$SSH_CONFIG" \
    -o ControlMaster=auto \
    -o ControlPath="/tmp/vagrant-qt-dev-%r@%h:%p" \
    -o ControlPersist=10m \
    default \
    "$ENV_PREFIX $*"
