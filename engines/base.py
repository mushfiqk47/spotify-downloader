"""
Base abstraction for download engines.
Defines engine states, data models, cached FFmpeg discovery, and interfaces.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import shutil
from typing import List, Optional

from core.process import AsyncProcessRunner


class EngineState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


@dataclass
class ProgressUpdate:
    percent: Optional[float] = None
    total_size: Optional[str] = None
    speed: Optional[str] = None
    eta: Optional[str] = None
    current_item: Optional[int] = None
    total_items: Optional[int] = None
    raw_line: str = ""
    tag: str = "normal"  # "action_blue", "muted", "success", "danger", "normal"


# Cached FFmpeg path lookup
_CACHED_FFMPEG: Optional[str] = None
_FFMPEG_CHECKED = False


def find_ffmpeg() -> Optional[str]:
    """Discovers and caches the path to the FFmpeg executable."""
    global _CACHED_FFMPEG, _FFMPEG_CHECKED
    if _FFMPEG_CHECKED:
        return _CACHED_FFMPEG

    which = shutil.which("ffmpeg")
    if which:
        _CACHED_FFMPEG = which
        _FFMPEG_CHECKED = True
        return which

    candidates = [
        Path.home() / ".spotdl" / "ffmpeg.exe",
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
    ]
    for c in candidates:
        if c.is_file():
            _CACHED_FFMPEG = str(c)
            break

    _FFMPEG_CHECKED = True
    return _CACHED_FFMPEG


class BaseDownloadEngine(ABC):
    """Abstract base class for decoupled download engines."""

    def __init__(self):
        self.runner = AsyncProcessRunner()
        self.state: EngineState = EngineState.IDLE

    @property
    def is_running(self) -> bool:
        return self.runner.is_running

    @abstractmethod
    def build_command(self, url: str, out_dir: str, **kwargs) -> List[str]:
        """Builds the exact CLI command list for execution."""
        pass

    @abstractmethod
    def parse_line(self, line: str) -> ProgressUpdate:
        """Parses a raw output line using pre-compiled regexes into structured ProgressUpdate."""
        pass

    def abort(self):
        """Cleanly halts active download process."""
        self.state = EngineState.ABORTED
        self.runner.abort()
