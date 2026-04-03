#!/usr/bin/env bash
# Делает скриншот внутри VM и копирует на хост.
# Агент вызывает этот скрипт для visual feedback.
#
# Использование:
#   ./scripts/screenshot.sh [output_path]
#   ./scripts/screenshot.sh ./debug/after_click.png

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_CONFIG="$PROJECT_ROOT/.vagrant-ssh-config"

OUTPUT="${1:-/tmp/vm-screenshot.png}"
mkdir -p "$(dirname "$OUTPUT")"

REMOTE_PATH="/tmp/vm-screenshot-$$.png"

# Скриншот внутри VM
ssh -F "$SSH_CONFIG" \
    -o ControlMaster=auto \
    -o ControlPath="/tmp/vagrant-qt-dev-%r@%h:%p" \
    -o ControlPersist=10m \
    default \
    "DISPLAY=:99 scrot '$REMOTE_PATH'"

# Копируем на хост
scp -F "$SSH_CONFIG" \
    "default:$REMOTE_PATH" \
    "$OUTPUT"

# Чистим remote
ssh -F "$SSH_CONFIG" \
    -o ControlPath="/tmp/vagrant-qt-dev-%r@%h:%p" \
    default \
    "rm -f '$REMOTE_PATH'"

echo "Скриншот: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
