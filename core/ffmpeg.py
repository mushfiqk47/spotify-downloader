"""Module: FFmpeg discovery.

Clean-OS order (first hit wins):
  1. Bundled sidecar next to the backend exe
     (<resources>/backend/ffmpeg(.exe) in packaged app, dist-backend/ in dev,
      _MEIPASS in PyInstaller onefile).
  2. imageio-ffmpeg pip static binary (no system install needed).
  3. System PATH + well-known locations (dev machines with ffmpeg installed).
"""
from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional


def _exe_name(base: str) -> str:
    return base + (".exe" if sys.platform == "win32" else "")


def _bundled_candidates() -> list[Path]:
    names = [_exe_name("ffmpeg")]
    dirs: list[Path] = []
    # PyInstaller onefile unpack dir
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(Path(meipass))
    # Frozen exe dir (<resources>/backend/ or dist-backend/)
    if getattr(sys, "frozen", False):
        try:
            dirs.append(Path(sys.executable).resolve().parent)
        except Exception:
            pass
    # Dev / repo layouts
    here = Path(__file__).resolve().parent.parent
    dirs.extend([
        here / "dist-backend",
        here / "backend",
        here,
    ])
    # Electron extraResources when running from source via `npm start`
    # (electron/main.js cwd = repo root, resources path not available here,
    # but dist-backend/ above already covers dev).
    out: list[Path] = []
    for d in dirs:
        for n in names:
            out.append(d / n)
    return out


_CANDIDATES = (
    # Windows locations
    Path.home() / ".spotdl" / "ffmpeg.exe",
    Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
    Path("C:/ffmpeg/bin/ffmpeg.exe"),
    # Linux & macOS locations
    Path.home() / ".spotdl" / "ffmpeg",
    Path("/usr/bin/ffmpeg"),
    Path("/usr/local/bin/ffmpeg"),
    Path("/opt/homebrew/bin/ffmpeg"),
    Path("/opt/local/bin/ffmpeg"),
)


def _ensure_exec(path: Path) -> Optional[str]:
    try:
        if path.is_file():
            if os.name != "nt":
                try:
                    if not os.access(str(path), os.X_OK):
                        os.chmod(str(path), 0o755)
                except OSError:
                    pass
            return str(path)
    except OSError:
        pass
    return None


@lru_cache(maxsize=1)
def find_ffmpeg() -> Optional[str]:
    """Discover ffmpeg once per process; cached for all engines."""
    # 1. Bundled sidecar (packaged app / dev dist-backend)
    for c in _bundled_candidates():
        hit = _ensure_exec(c)
        if hit:
            return hit
    # 2. imageio-ffmpeg static binary (pip-installed, works on clean OS)
    try:
        import imageio_ffmpeg  # type: ignore

        exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
        hit = _ensure_exec(exe)
        if hit:
            return hit
    except Exception:
        pass
    # 3. System PATH
    which = shutil.which("ffmpeg")
    if which:
        return which
    for c in _CANDIDATES:
        try:
            if c.is_file():
                return str(c)
        except OSError:
            continue
    return None


def clear_cache() -> None:
    find_ffmpeg.cache_clear()
