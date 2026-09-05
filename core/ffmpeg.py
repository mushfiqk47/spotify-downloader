"""Module: FFmpeg discovery.

Deep Module with a tiny Interface: `find_ffmpeg() -> str | None`.
All caching lives inside (Locality). Callers get Leverage: one call,
zero knowledge of PATH / WinGet / spotdl locations.
"""
from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Optional


_CANDIDATES = (
    Path.home() / ".spotdl" / "ffmpeg.exe",
    Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
    Path("C:/ffmpeg/bin/ffmpeg.exe"),
)


@lru_cache(maxsize=1)
def find_ffmpeg() -> Optional[str]:
    """Discover ffmpeg once per process; cached for all engines."""
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
