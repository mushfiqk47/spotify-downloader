"""
Base abstraction for download engines.
Defines engine states, data models, cached FFmpeg discovery, and interfaces.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import sys
from pathlib import Path
from typing import List, Optional

from core.process import AsyncProcessRunner
from core.ffmpeg import find_ffmpeg as _core_find_ffmpeg


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


def find_ffmpeg() -> Optional[str]:
    """Seam alias -> single cached implementation in core.ffmpeg (Locality)."""
    return _core_find_ffmpeg()


def is_frozen() -> bool:
    """True when running inside a PyInstaller / Electron bundle."""
    return bool(getattr(sys, "frozen", False))


def get_python_exe() -> str:
    """Discovers console python.exe, preventing pythonw.exe subprocess issues on Windows."""
    exe = sys.executable
    p = Path(exe)
    if "pythonw" in p.name.lower():
        alt_name = p.name.lower().replace("pythonw", "python")
        console_py = p.with_name(alt_name)
        if console_py.is_file():
            return str(console_py)
    return exe


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
