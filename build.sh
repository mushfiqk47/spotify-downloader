#!/usr/bin/env bash
# ==============================================================================
# StreamRip Core - Cross-Platform Build Pipeline for Linux & macOS
# ==============================================================================

set -e

# ANSI color codes
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}   StreamRip Core - Packaging & Build Pipeline${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OS="$(uname -s)"

# ------------------------------------------------------------------------------
# 1. Environment & Virtualenv Detection
# ------------------------------------------------------------------------------
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    echo -e "${BOLD}1. Activating Python virtual environment (.venv)...${NC}"
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.venv/bin/activate"
else
    echo -e "${YELLOW}[!] .venv not found; using active Python environment.${NC}"
fi

PY_BIN="$(command -v python3 || command -v python)"
if [ -z "$PY_BIN" ]; then
    echo -e "${RED}[ERROR] Python 3 not found in PATH. Please run ./setup.sh.${NC}"
    exit 1
fi

if ! "$PY_BIN" -c "import PyInstaller" 2>/dev/null; then
    echo -e "${YELLOW}[!] PyInstaller not found. Installing PyInstaller...${NC}"
    "$PY_BIN" -m pip install pyinstaller
fi

# ------------------------------------------------------------------------------
# 2. Compile Python Backend Executable
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}2. Compiling Python Backend Executable with PyInstaller...${NC}"
"$PY_BIN" -m PyInstaller backend.spec --noconfirm --distpath dist-backend

# Backend binary name differs per OS (Windows adds .exe)
BACKEND_BIN="$SCRIPT_DIR/dist-backend/streamrip-backend"
if [ "$OS" != "Darwin" ] && [ "$OS" != "Linux" ]; then
    BACKEND_BIN="$SCRIPT_DIR/dist-backend/streamrip-backend.exe"
fi
if [ ! -f "$BACKEND_BIN" ]; then
    # fallback: accept either name on any OS
    if [ -f "$SCRIPT_DIR/dist-backend/streamrip-backend.exe" ]; then
        BACKEND_BIN="$SCRIPT_DIR/dist-backend/streamrip-backend.exe"
    elif [ -f "$SCRIPT_DIR/dist-backend/streamrip-backend" ]; then
        BACKEND_BIN="$SCRIPT_DIR/dist-backend/streamrip-backend"
    fi
fi
if [ -f "$BACKEND_BIN" ]; then
    chmod +x "$BACKEND_BIN" 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/dist-backend/ffmpeg" 2>/dev/null || true
    echo -e "${GREEN}[OK] Standalone backend built:${NC} $BACKEND_BIN"
    echo -e "   Verifying bundled runtime..."
    "$PY_BIN" -c "from PyInstaller.utils.hooks import collect_data_files; d=collect_data_files('pykakasi'); assert any('kanwadict4' in a for a,_ in d); print('   [OK] pykakasi data')"
    "$PY_BIN" -c "import imageio_ffmpeg; print('   [OK] ffmpeg:', imageio_ffmpeg.get_ffmpeg_exe())"
else
    echo -e "${RED}[ERROR] Backend binary build failed.${NC}"
    exit 1
fi

# If argument is --backend-only, stop here
if [ "${1:-}" = "--backend-only" ]; then
    echo -e "\n${GREEN}[OK] Backend build complete!${NC}"
    exit 0
fi

# ------------------------------------------------------------------------------
# 3. Package Electron Application
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}3. Packaging Desktop Application with Electron-Builder...${NC}"

if ! command -v npm >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] npm not found in PATH. Cannot package Electron app.${NC}"
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo -e "   Installing npm dependencies first..."
    npm install
fi

TARGET="${1:-}"

if [ "$OS" = "Darwin" ]; then
    echo -e "   Building macOS bundle (.dmg, .zip)..."
    if [ "$TARGET" = "zip" ]; then
        npx electron-builder --mac zip
    else
        npm run dist:mac
    fi
elif [ "$OS" = "Linux" ]; then
    echo -e "   Building Linux packages (.AppImage, .deb, .tar.gz)..."
    case "$TARGET" in
        appimage)
            npx electron-builder --linux AppImage
            ;;
        deb)
            npx electron-builder --linux deb
            ;;
        tar|tar.gz)
            npx electron-builder --linux tar.gz
            ;;
        *)
            npm run dist:linux
            ;;
    esac
else
    echo -e "${YELLOW}[!] Unknown OS ($OS). Running generic pack...${NC}"
    npm run pack
fi

echo -e "\n${BOLD}${GREEN}============================================${NC}"
echo -e "${BOLD}${GREEN}   Build Completed Successfully!            ${NC}"
echo -e "${BOLD}${GREEN}   Artifacts available in: 'dist-installer/' ${NC}"
echo -e "${BOLD}${GREEN}============================================${NC}"
ls -lh dist-installer/ 2>/dev/null || true
