"""Module: async subprocess execution.

Deep Module — small Interface, lots of behaviour hidden inside:
  runner.start(cmd) -> None
  runner.abort() -> None
  runner.is_running -> bool
  runner.output_queue -> Queue[("LINE"|"ERROR"|"DONE", payload)]

Design rules applied:
- Accept dependencies, don't create them: caller passes `cmd`;
  runner never builds yt-dlp/spotdl flags itself (that's the engine Adapter's job).
- Return results, don't produce side effects: output flows through
  `output_queue` + optional callbacks; runner never touches Tk.
- One Seam: UI polls the queue; tests push fake lines through the same Seam.

Perf: daemon thread, line-buffered pipe, stale-queue drain on start,
graceful terminate-then-kill abort.
"""
from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
from typing import Callable, List, Optional


class AsyncProcessRunner:
    """Non-blocking process executor streaming to a queue."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._aborted = False
        self.output_queue: queue.Queue = queue.Queue()

    @property
    def is_running(self) -> bool:
        proc = self._proc
        return proc is not None and proc.poll() is None

    def start(
        self,
        cmd: List[str],
        on_output: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[int, bool], None]] = None,
    ) -> None:
        self._aborted = False
        # Drain stale items so a new run never replays old lines.
        while True:
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break

        def worker() -> None:
            flags: dict = {}
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
                    bufsize=1,
                    **flags,
                )
            except Exception as e:  # noqa: BLE001 - must surface to UI queue
                err = f"Error launching process: {e}"
                self.output_queue.put(("ERROR", err))
                if on_output:
                    on_output(err)
                if on_complete:
                    on_complete(-1, False)
                return

            proc = self._proc
            assert proc is not None and proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self.output_queue.put(("LINE", line))
                    if on_output:
                        on_output(line)
            try:
                exit_code = proc.wait()
            except Exception:  # noqa: BLE001
                exit_code = -1
            self.output_queue.put(("DONE", (exit_code, self._aborted)))
            if on_complete:
                on_complete(exit_code, self._aborted)
            self._proc = None

        self._thread = threading.Thread(target=worker, daemon=True, name="AsyncProcessRunner")
        self._thread.start()

    def abort(self) -> None:
        self._aborted = True
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(0.1)
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
