#!/usr/bin/env bash
# ==============================================================================
# StreamRip Core - Environment Setup for Linux (Ubuntu, Arch, Fedora) & macOS
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
echo -e "${BOLD}${BLUE}   StreamRip Core - Universal Setup         ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OS="$(uname -s)"

# ------------------------------------------------------------------------------
# 1. Detect OS & Install System Dependencies
# ------------------------------------------------------------------------------
echo -e "${BOLD}1. Detecting OS & System Package Manager...${NC}"

install_deps_linux() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_ID="${ID:-}"
        DISTRO_LIKE="${ID_LIKE:-}"
    else
        DISTRO_ID="unknown"
        DISTRO_LIKE=""
    fi

    echo -e "   Detected Linux Distribution: ${YELLOW}${DISTRO_ID}${NC}"

    case "$DISTRO_ID" in
        ubuntu|debian|pop|mint|elementary|kali|zorin)
            echo -e "   Using ${GREEN}apt${NC} to install packages..."
            sudo apt-get update -qq
            sudo apt-get install -y python3 python3-pip python3-venv ffmpeg nodejs npm
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            echo -e "   Using ${GREEN}pacman${NC} to install packages..."
            sudo pacman -Sy --noconfirm python python-pip python-virtualenv ffmpeg nodejs npm
            ;;
        fedora|rhel|centos|rocky|alma)
            echo -e "   Using ${GREEN}dnf${NC} to install packages..."
            sudo dnf install -y python3 python3-pip ffmpeg nodejs npm
            ;;
        opensuse*|suse)
            echo -e "   Using ${GREEN}zypper${NC} to install packages..."
            sudo zypper in -y python3 python3-pip ffmpeg nodejs npm
            ;;
        alpine)
            echo -e "   Using ${GREEN}apk${NC} to install packages..."
            sudo apk add --no-cache python3 py3-pip ffmpeg nodejs npm
            ;;
        *)
            # Fallback based on ID_LIKE
            if echo "$DISTRO_LIKE" | grep -qE "debian|ubuntu"; then
                sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip python3-venv ffmpeg nodejs npm
            elif echo "$DISTRO_LIKE" | grep -q "arch"; then
                sudo pacman -Sy --noconfirm python python-pip python-virtualenv ffmpeg nodejs npm
            elif echo "$DISTRO_LIKE" | grep -qE "fedora|rhel"; then
                sudo dnf install -y python3 python3-pip ffmpeg nodejs npm
            else
                echo -e "${YELLOW}[WARNING] Unsupported distribution detected: $DISTRO_ID.${NC}"
                echo -e "Please ensure python3, pip, python-venv, ffmpeg, nodejs, and npm are installed."
            fi
            ;;
    esac
}

install_deps_macos() {
    echo -e "   Detected macOS (${YELLOW}$(uname -m)${NC})"
    if ! command -v brew >/dev/null 2>&1; then
        echo -e "${YELLOW}[!] Homebrew not detected.${NC}"
        echo -e "Installing Homebrew now..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ -d "/opt/homebrew/bin" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -d "/usr/local/bin" ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi

    echo -e "   Updating brew and installing dependencies: python, ffmpeg, node..."
    brew install python ffmpeg node
}

if [ "$OS" = "Darwin" ]; then
    install_deps_macos
elif [ "$OS" = "Linux" ]; then
    install_deps_linux
else
    echo -e "${RED}[ERROR] Unsupported operating system: $OS${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] System tools installed.${NC}\n"

# ------------------------------------------------------------------------------
# 2. Python Virtual Environment (PEP 668 Compliant)
# ------------------------------------------------------------------------------
echo -e "${BOLD}2. Configuring Python Virtual Environment (.venv)...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "   ${GREEN}[OK] Created .venv${NC}"
else
    echo -e "   ${GREEN}[OK] Existing .venv detected${NC}"
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo -e "   Upgrading pip and installing requirements..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "${GREEN}[OK] Python dependencies installed successfully.${NC}\n"

# ------------------------------------------------------------------------------
# 3. Node / Electron Dependencies
# ------------------------------------------------------------------------------
echo -e "${BOLD}3. Installing Electron & Desktop Dependencies...${NC}"
if command -v npm >/dev/null 2>&1; then
    npm install
    echo -e "${GREEN}[OK] Node modules installed.${NC}\n"
else
    echo -e "${YELLOW}[!] npm not found in PATH. Electron desktop packaging will be skipped.${NC}\n"
fi

# ------------------------------------------------------------------------------
# 4. Bootstrap Default Directories
# ------------------------------------------------------------------------------
echo -e "${BOLD}4. Creating default download folders...${NC}"
SPOTIFY_OUT="$HOME/Music/SpotifyDownloads"
mkdir -p "$SPOTIFY_OUT"
echo -e "   ${GREEN}[OK]${NC} $SPOTIFY_OUT"

if [ "$OS" = "Darwin" ]; then
    YOUTUBE_OUT="$HOME/Movies/YouTubeDownloads"
    mkdir -p "$YOUTUBE_OUT"
    echo -e "   ${GREEN}[OK]${NC} $YOUTUBE_OUT"
else
    YOUTUBE_OUT="$HOME/Videos/YouTubeDownloads"
    mkdir -p "$YOUTUBE_OUT"
    echo -e "   ${GREEN}[OK]${NC} $YOUTUBE_OUT"
fi
echo ""

# ------------------------------------------------------------------------------
# 5. Make helper scripts executable & register Desktop shortcut on Linux
# ------------------------------------------------------------------------------
echo -e "${BOLD}5. Setting executable permissions...${NC}"
chmod +x run.sh build.sh setup.sh 2>/dev/null || true

if [ "$OS" = "Linux" ] && [ -d "$HOME/.local/share/applications" ]; then
    echo -e "   Registering Linux Desktop application shortcut..."
    DESKTOP_ENTRY="$HOME/.local/share/applications/streamrip-core.desktop"
    cat > "$DESKTOP_ENTRY" <<EOF
[Desktop Entry]
Name=StreamRip Core
Comment=YouTube & Spotify extraction studio
Exec=$SCRIPT_DIR/run.sh
Icon=$SCRIPT_DIR/build/icon.png
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Video;Network;
StartupWMClass=StreamRip Core
EOF
    chmod +x "$DESKTOP_ENTRY"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
    echo -e "   ${GREEN}[OK] Desktop shortcut created at $DESKTOP_ENTRY${NC}"
fi

echo -e "\n${BOLD}${GREEN}============================================${NC}"
echo -e "${BOLD}${GREEN}   Setup Complete!                          ${NC}"
echo -e "${BOLD}${GREEN}   Run './run.sh' to launch StreamRip Core. ${NC}"
echo -e "${BOLD}${GREEN}============================================${NC}"
