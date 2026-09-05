"""
Process management and system utilities.
Thread-safe subprocess runner streaming to queues for zero-lag UI updates.
"""
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional


class AsyncProcessRunner:
    """Non-blocking process executor with queue-based line buffering and clean abort."""

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._aborted = False
        self.output_queue: queue.Queue = queue.Queue()

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(
        self,
        cmd: List[str],
        on_output: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[int, bool], None]] = None,
    ):
        """Starts a background process, streaming output via callback and queue."""
        self._aborted = False
        # Clear any stale queue items
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break

        def worker():
            flags = {}
            if os.name == "nt":
                flags["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    **flags,
                )
            except Exception as e:
                err_msg = f"Error launching process: {e}"
                self.output_queue.put(("ERROR", err_msg))
                if on_output:
                    on_output(err_msg)
                if on_complete:
                    on_complete(-1, False)
                return

            if self._proc.stdout is not None:
                for line in self._proc.stdout:
                    line = line.rstrip()
                    if line:
                        self.output_queue.put(("LINE", line))
                        if on_output:
                            on_output(line)

            exit_code = self._proc.wait()
            self.output_queue.put(("DONE", (exit_code, self._aborted)))
            if on_complete:
                on_complete(exit_code, self._aborted)
            self._proc = None

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def abort(self):
        """Terminates and kills the active process."""
        self._aborted = True
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                time.sleep(0.1)
                if self._proc.poll() is None:
                    self._proc.kill()
            except Exception:
                pass


def find_ffmpeg() -> Optional[str]:
    """Finds available FFmpeg binary on Windows system or standard paths."""
    which = shutil.which("ffmpeg")
    if which:
        return which
    candidates = [
        Path.home() / ".spotdl" / "ffmpeg.exe",
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def format_bytes(n: int) -> str:
    if n <= 0:
        return "0 B"
    for unit, divisor in [("GB", 1073741824), ("MB", 1048576), ("KB", 1024)]:
        if n >= divisor:
            return f"{n / divisor:.1f} {unit}"
    return f"{n} B"


def format_speed(n: float) -> str:
    if n <= 0:
        return "--"
    for unit, divisor in [("MB/s", 1048576), ("KB/s", 1024)]:
        if n >= divisor:
            return f"{n / divisor:.1f} {unit}"
    return f"{n:.0f} B/s"
