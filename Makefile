# ==============================================================================
# StreamRip Core - Multi-Platform Makefile
# ==============================================================================

.PHONY: all help setup run run-browser build build-backend dist-linux dist-mac dist-win clean test

PYTHON ?= $(shell which python3 2>/dev/null || which python 2>/dev/null || echo python)

all: help

help:
	@echo "StreamRip Core - Build & Runtime Automation"
	@echo "==========================================="
	@echo "  make setup          - Install dependencies (Linux: apt/pacman/dnf, macOS: brew)"
	@echo "  make run            - Launch application (Electron or Browser fallback)"
	@echo "  make run-browser    - Force run in default browser"
	@echo "  make build          - Build standalone backend and package desktop app"
	@echo "  make build-backend  - Build PyInstaller backend binary (dist-backend/)"
	@echo "  make dist-linux     - Package Linux (.AppImage, .deb, .tar.gz)"
	@echo "  make dist-mac       - Package macOS (.dmg, .zip)"
	@echo "  make dist-win       - Package Windows (.exe NSIS)"
	@echo "  make clean          - Remove build caches and generated distribution artifacts"
	@echo "  make test           - Run syntax and module verification tests"

setup:
	@chmod +x setup.sh run.sh build.sh 2>/dev/null || true
	@./setup.sh

venv-build:
	python3 -m venv .venv-build || python -m venv .venv-build
	. .venv-build/bin/activate && pip install --upgrade pip --quiet && pip install -r requirements.txt --quiet
	@echo "[OK] Clean build env ready (.venv-build). build.sh will use it automatically."

run:
	@chmod +x run.sh 2>/dev/null || true
	@./run.sh

run-browser:
	@chmod +x run.sh 2>/dev/null || true
	@./run.sh --browser

build:
	@chmod +x build.sh 2>/dev/null || true
	@./build.sh

build-backend:
	$(PYTHON) -m PyInstaller backend.spec --noconfirm --distpath dist-backend
	@chmod +x dist-backend/streamrip-backend/streamrip-backend 2>/dev/null || true
	@chmod +x dist-backend/ffmpeg 2>/dev/null || true

dist-linux: build-backend
	npm run dist:linux

dist-mac: build-backend
	npm run dist:mac

dist-win: build-backend
	npm run dist

test:
	$(PYTHON) -m compileall -q server.py main.py app_pipeline.py core engines tests
	$(PYTHON) -m pytest -q
	@echo "[OK] Compile + pytest passed."

clean:
	rm -rf dist-backend dist-installer dist build/backend build/streamrip-backend
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
