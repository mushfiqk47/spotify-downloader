#!/usr/bin/env bash
# ==============================================================================
# StreamRip Core - Universal Launcher for Linux & macOS
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Activate Python virtual environment if present
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Ensure python executable is available
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "[ERROR] Python 3 was not found. Please run ./setup.sh first."
    exit 1
fi

PY_BIN="$(command -v python3 || command -v python)"

# 2. Check execution mode
MODE="${1:-}"

if [ "$MODE" = "--browser" ] || [ "$MODE" = "-b" ]; then
    echo "Starting StreamRip Core in Browser Mode..."
    exec "$PY_BIN" "$SCRIPT_DIR/main.py"
fi

# 3. Launch via Electron if available; fallback to browser mode
if [ -d "$SCRIPT_DIR/node_modules/electron" ] && command -v npm >/dev/null 2>&1; then
    echo "Starting StreamRip Core Desktop Window..."
    exec npm start
else
    echo "Electron not installed or not built. Launching StreamRip Core in default web browser..."
    exec "$PY_BIN" "$SCRIPT_DIR/main.py"
fi
