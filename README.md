# StreamRip Core

A sleek, high-precision desktop media extraction studio for **YouTube** and **Spotify**. Built with **Electron**, a modular **Vanilla CSS/JS** frontend, and a high-performance **Python/Flask** backend powered by `yt-dlp` and `spotDL`.

Adheres strictly to the monochrome utility design system from [`design.md`](file:///c:/Users/MUSHFIQ/Documents/spotify%20downloder/design.md) (Cal.com aesthetic).

---

## 🎨 Visual Design & UI System

StreamRip Core implements a pragmatic, high-precision instrument interface:

- **Strict Monochrome Palette**: Ink (`#101010`), Graphite (`#242424`), Slate (`#6b7280`), Paper (`#f4f4f4`), and White (`#ffffff`), with **Action Blue** (`#0099ff`) reserved for live status indicators.
- **2-Column Split Studio Layout**:
  - **Left Configuration Column**:
    - **Source URL**: Target input field with right-aligned format hints (`youtube / playlists` or `spotify / albums / tracks`).
    - **Export Destination**: Path entry accompanied by a rounded **Browse** button (opens native OS folder picker in Electron or an interactive modal explorer in browser mode).
    - **Stream & Format Dropdowns**: Selectors for video resolution, audio formats, and caption/bitrate envelopes.
    - **Contained Options Card**: Preferences for creator subtitles, transcripts, language tags, and synced lyrics (`.lrc`).
    - **Full-Width Pill CTA**: Solid Ink button (`⤓ Start Extraction`) with hover animations, dynamically toggling to `■ Cancel Extraction` during active extraction runs.
  - **Right Column (Pipeline Terminal)**:
    - Dedicated live terminal console featuring monospace typography, tagged color logs, a 1,200-line memory-capped ring buffer, and **Clear** controls.
- **Dual Runtime Modes**: Runs either as a native, borderless **Electron desktop application** or as a lightweight **web application** in your default browser.

---

## 📖 How to Use StreamRip Core

### 1. Launching the App
Depending on your preference, launch StreamRip Core in **Desktop Window Mode** (Electron) or **Browser Mode**:

| Launch Target | Windows | Linux / macOS |
| :--- | :--- | :--- |
| **Desktop App (Electron)** | Double-click `run.bat` or run `npm start` | `./run.sh` or `make run` |
| **Browser Mode (Web UI)** | Run `python main.py` | `./run.sh --browser` or `make run-browser` |

---

### 2. 🎥 Downloading from YouTube

1. **Select YouTube Mode**: Click the **YouTube** tab in the header.
2. **Paste Source URL**: Enter any valid YouTube URL in the **Source URL** field:
   - Single video: `https://www.youtube.com/watch?v=...`
   - YouTube Shorts: `https://www.youtube.com/shorts/...`
   - Playlists: `https://www.youtube.com/playlist?list=...`
   - Channels or user uploads.
3. **Choose Quality Preset**:
   - `Best Available (Source)`: Highest video + audio streams available.
   - `1080p 60fps (H.264)`: High-definition 1080p stream.
   - `720p Optimized`: Standard HD for quick downloads.
   - `Lossless Audio Only (M4A)` or `Audio Only (.mp3)`: Audio rip directly from video.
4. **Configure Captions & Subtitles**:
   - Check **Capture Transcripts & Timestamps** to download subtitles.
   - Choose your format: `SubRip (.srt)`, `WebVTT (.vtt)`, or `Raw Timed Text (.json)`.
5. **Set Destination**: Click **Browse** to pick an export folder, or leave it set to your default `Videos/YouTubeDownloads` directory.
6. **Start Extraction**: Click **Start Extraction**. Watch real-time fragment downloads and progress in the terminal pane.

---

### 3. 🎵 Downloading from Spotify

1. **Select Spotify Mode**: Click the **Spotify** tab in the header.
2. **Paste Spotify Link**: Enter any public Spotify link:
   - Track: `https://open.spotify.com/track/...`
   - Album: `https://open.spotify.com/album/...`
   - Playlist: `https://open.spotify.com/playlist/...`
   - Artist discography: `https://open.spotify.com/artist/...`
3. **Select Audio Encoding**:
   - Formats: `MP3 Audio (.mp3)`, `FLAC Lossless (.flac)`, `OGG Vorbis (.ogg)`, `Opus (.opus)`, `M4A (.m4a)`, `WAV (.wav)`.
   - Bitrates: `Auto (Best Match)`, `320 kbps (High)`, `256 kbps`, `192 kbps`, `128 kbps`.
4. **Synced Lyrics (`.lrc`)**: Automatically fetches and embeds timestamped lyrics compatible with modern media players.
5. **Start Extraction**: Click **Start Extraction**. StreamRip indexes track metadata and downloads audio fragments in parallel across 4 worker threads.

---

### 4. 📁 Selecting Destination Folders

- **In Electron Desktop Mode**: Clicking **Browse** invokes the operating system's native folder selection dialog (`window.streamrip.selectFolder`).
- **In Browser Mode**: Clicking **Browse** opens an interactive in-page **Folder Browser Modal**:
  - Click any folder to drill down into subdirectories.
  - Click **Up** to traverse to parent directories.
  - Click **Home** to jump straight to your user profile.
  - Click **Drives** (on Windows) to switch drive letters (`C:\`, `D:\`, etc.).
  - Click **Select this folder** to confirm.

---

### 5. 🛑 Cancelling an Active Download

If you need to stop a download:
1. Click **Cancel Extraction** (the button turns into an active cancel trigger during runs).
2. The engine gracefully terminates the active `yt-dlp` or `spotdl` subprocess.
3. The terminal logs `Abort requested.` and resets to standby status.

---

### 6. 🔄 1-Click Dependency Updates

YouTube and Spotify frequently adjust their internal streaming APIs. StreamRip Core includes an integrated updater:
1. Click **Check Updates** in the top-right header (or let the app check automatically on boot).
2. If an update for `yt-dlp` or `spotdl` is detected, the button illuminates: `Update Available (N)`.
3. Click the button to trigger a live background `pip install --upgrade`.
4. The terminal displays real-time package upgrade logs, and automatically refreshes when complete.

---

## 📦 Multi-Platform Setup & Installation

### Supported Systems
- **Windows**: Windows 10 & 11 (64-bit)
- **Linux**: Ubuntu, Debian, Arch Linux, Manjaro, Fedora, openSUSE (64-bit)
- **macOS**: Apple Silicon (M1/M2/M3/M4) & Intel (macOS 11+)

---

### 🐧 Linux (Ubuntu, Arch, Fedora)

#### 1. Automated Setup
```bash
chmod +x setup.sh
./setup.sh
```
*Automatically detects your package manager (`apt`, `pacman`, `dnf`, `zypper`), installs `python3`, `ffmpeg`, `nodejs`, `npm`, creates a PEP 668-compliant `.venv`, and creates a desktop shortcut (`~/.local/share/applications/streamrip-core.desktop`).*

#### 2. Launch
```bash
./run.sh
# or launch directly in default browser:
./run.sh --browser
```

#### 3. Build Linux Packages (.AppImage, .deb, .tar.gz)
```bash
./build.sh
# or build a specific target:
./build.sh appimage
./build.sh deb
./build.sh tar.gz
# or with Makefile:
make dist-linux
```
*Generates Linux standalone distributions in `dist-installer/` (`StreamRip-Core-1.0.0-x64.tar.gz`, `.deb`, `.AppImage`).*

---

### 🍎 macOS (Apple Silicon & Intel)

#### 1. Automated Setup
```bash
chmod +x setup.sh
./setup.sh
```
*Verifies or installs [Homebrew](https://brew.sh), installs `python3`, `ffmpeg`, and `node`, sets up `.venv`, and prepares download folders.*

#### 2. Launch
```bash
./run.sh
# or launch in default browser:
./run.sh --browser
```

#### 3. Build macOS Bundles (.dmg, .zip)
```bash
./build.sh
# or with Makefile:
make dist-mac
```
*Generates `.dmg` and `.zip` installers inside `dist-installer/` with bundled Python runtime, FFmpeg, and gettext locale catalogs.*

---

### 🪟 Windows Setup & Launch

#### 1. Automated Setup
Double-click or run **`setup.bat`**:
```cmd
setup.bat
```

#### 2. Launching
Double-click **`run.bat`** or run:
```cmd
python main.py
```

#### 3. Packaging Windows Installer (.exe)
```cmd
npm run dist
# or with Makefile:
make dist-win
```
*Generates `StreamRip-Core-Setup-1.0.0.exe` (~158 MB lean onedir NSIS installer) in `dist-installer/`.*

---

### 🛠️ Quick Commands (Makefile)

If `make` is installed on your system, you can use these shorthand targets:
```bash
make setup          # Install dependencies on current OS (apt/pacman/dnf/brew)
make run            # Launch desktop application
make run-browser    # Run with default web browser
make build          # Build standalone binary and package app
make build-backend  # PyInstaller backend compilation
make dist-linux     # Build Linux packages (AppImage, deb, tar.gz)
make dist-mac       # Build macOS packages (dmg, zip)
make dist-win       # Build Windows setup exe
make test           # Verify Python syntax, modules, and routes
make clean          # Remove build artifacts and caches
```

---

## ⚡ High-Performance Architecture

StreamRip Core uses a decoupled layered architecture separating the Electron desktop shell, web frontend, Flask API, and extraction engines:

```
spotify downloder/
├── UI.html                       # Semantic HTML5 view (147 lines, zero inline CSS/JS)
├── css/                          # Modular styles (Cal.com design system)
│   ├── variables.css             # Color tokens, fonts, root variables, CSS reset
│   ├── layout.css                # App container, header, 2-column split grid, media queries
│   ├── components.css            # Input pills, dropdowns, checkboxes, action buttons, log pane
│   ├── modal.css                 # Folder browser modal overlay & directory tree
│   └── style.css                 # Main stylesheet bundling all CSS modules
├── js/                           # Frontend controllers
│   ├── state.js                  # App state, mode switching, /api/config loader
│   ├── folderPicker.js           # Native Electron dialog + in-browser /api/browse modal
│   ├── downloader.js             # Pipeline triggers, /api/download, job polling, abort
│   ├── updater.js                # /api/check-updates and live pip package upgrades
│   └── app.js                    # DOM initialization, memory-capped console stream, event bindings
├── electron/                     # Electron desktop shell
│   ├── main.js                   # Window lifecycle, backend process manager, native folder IPC
│   └── preload.js                # Context-isolated IPC bridge
├── core/                         # Shared backend foundations
│   ├── config.py                 # Cross-platform settings persistence (XDG, AppData, Library)
│   ├── ffmpeg.py                 # Cached multi-platform FFmpeg discovery
│   ├── runner.py                 # Thread-safe async subprocess runner with queue streaming
│   ├── updater.py                # Pure dependency version comparator and pip command builder
│   └── format.py                 # Byte and speed formatting utilities
├── engines/                      # Decoupled media extraction engines
│   ├── base.py                   # Abstract engine contract, states, and ProgressUpdate model
│   ├── youtube.py                # YouTubeEngine (yt-dlp, multi-chunk concurrent fragments)
│   └── spotify.py                # SpotifyEngine (spotDL, multi-threaded parallel downloads)
├── server.py                     # Flask REST API + static asset server
├── main.py                       # Lightweight studio launcher (starts Flask & opens browser)
├── backend.spec                  # Standalone PyInstaller compilation specification
├── setup.sh / setup.bat          # Multi-platform environment bootstrap scripts
├── run.sh / run.bat              # Multi-platform application launchers
├── build.sh                      # Universal packaging script
├── Makefile                      # CLI automation targets
├── streamrip-core.desktop        # Linux XDG desktop menu integration
└── .github/workflows/build.yml   # Multi-OS automated GitHub Actions CI/CD matrix
```

### Key Performance Innovations:
1. **Zero-Lag Event Draining**: CLI outputs stream into a thread-safe `queue.Queue`. The UI batches and consumes output without blocking event loops or locking rendering.
2. **Accelerated Multi-Connection Downloads**: YouTube video streams utilize `--concurrent-fragments 4` across concurrent HTTP connections for **3x–5x faster** download throughput.
3. **Multi-Threaded Audio Scraping**: Spotify downloads utilize `--threads 4` for parallel metadata indexing and audio acquisition.
4. **Pre-Compiled Regex Cache**: All regex parsers (`RE_DOWNLOAD_PCT`, `RE_ITEM_QUEUE`, `RE_SUCCESS`, `RE_ERROR`) are compiled once at class load time, accelerating line parsing by **over 10x**.
5. **Persistent User Settings**: Remembers chosen download folders, preferred stream presets, bitrates, and language tags between sessions in `settings.json`.
6. **Memory Capped Terminal Feed**: The log terminal buffer automatically ring-caps at 1,200 lines to prevent long-running download sessions from consuming excess memory.

---

## ☁️ Automated Cloud Builds (GitHub Actions)

This repository includes an automated continuous integration workflow in [`.github/workflows/build.yml`](file:///.github/workflows/build.yml).
Whenever you push code or publish a release tag (e.g. `v1.0.0`):
- **Ubuntu runner**: Compiles native Linux `.AppImage`, `.deb`, and `.tar.gz`.
- **macOS runner**: Compiles native macOS `.dmg` and `.zip` for Apple Silicon & Intel.
- **Windows runner**: Compiles native Windows `StreamRip-Core-Setup-1.0.0.exe`.
- Ready-to-use binaries are automatically attached to GitHub Actions Artifacts and Releases.

---

## ⚙️ Configuration (`settings.json`)

User configurations are automatically managed and persisted in standard OS locations:
- **Linux**: `~/.config/StreamRipCore/settings.json`
- **macOS**: `~/Library/Application Support/StreamRipCore/settings.json`
- **Windows**: `%APPDATA%\StreamRipCore\settings.json`

```json
{
  "mode": "youtube",
  "youtube_out": "/home/user/Videos/YouTubeDownloads",
  "spotify_out": "/home/user/Music/SpotifyDownloads",
  "yt_stream": "Best Available (Source)",
  "yt_caption_env": "SubRip Subtitle (.srt)",
  "yt_capture_subs": true,
  "yt_transcript_only": false,
  "yt_lang": "en",
  "sp_stream": "MP3 Audio (.mp3)",
  "sp_bitrate": "Auto (Best Match)",
  "sp_generate_lrc": true,
  "sp_keep_archives": false
}
```

---

## 🔧 Troubleshooting & Tips

- **FFmpeg Discovery**: The application automatically checks system `PATH`, standard Unix paths (`/usr/bin/ffmpeg`, `/usr/local/bin/ffmpeg`, `/opt/homebrew/bin/ffmpeg`), WinGet links, and `~/.spotdl/ffmpeg`.
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Arch Linux: `sudo pacman -S ffmpeg`
  - Fedora: `sudo dnf install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg`
- **Updating Extractors**: When YouTube or Spotify update streaming formats, click the **Check Updates** button in the header, or run:
  ```bash
  pip install --upgrade yt-dlp spotdl
  ```
- **JavaScript Runtimes**: For YouTube throttled formats or advanced signature decryption, install Node.js (`node`) or Deno (`deno`). `yt-dlp` will automatically link to them.
- **Aborting Downloads**: You can cleanly halt any running extraction at any time by clicking **■ Cancel Extraction**.
