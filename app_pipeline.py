"""Module: pipeline control (extraction lifecycle + queue pump).

Deep Module behind a 4-method Interface:
  build_launch_plan() -> LaunchPlan | None   (validate + build cmd, pure)
  mark_running() / mark_finished(exit, aborted) -> UI patch dicts (pure, Return results)
  drain_queue(queue, parse) -> PumpResult     (batch parse, no Tk inside)

The Tk Adapter (`app.py`) stays thin: it calls these and applies the
returned patches to widgets. Tests cross the same Seam without Tk:
pass a fake queue + fake parse fn, assert on the returned dataclasses.

Perf: pump caps at 40 lines/tick -> 60fps UI never starves; parsing
uses the engines' pre-compiled regexes (no re.compile per line).
"""
from __future__ import annotations

import queue
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple


@dataclass(frozen=True)
class LaunchPlan:
    cmd: List[str]
    url: str
    out_dir: str


@dataclass(frozen=True)
class ParsedBatch:
    log_rows: List[Tuple[str, str]] = field(default_factory=list)
    percent: Optional[float] = None
    completions: List[Tuple[int, bool]] = field(default_factory=list)


@dataclass(frozen=True)
class FinishPatch:
    status: str
    tone: str  # "success" | "danger"
    message: str
    message_tag: str


MAX_ITEMS_PER_TICK = 40


def drain_queue(
    q: "queue.Queue",
    parse: Callable[[str], object],
    limit: int = MAX_ITEMS_PER_TICK,
) -> ParsedBatch:
    """Pull up to `limit` items; parse LINEs via injected `parse` fn.

    Accepts the queue (doesn't create it) and returns results
    (doesn't touch widgets) -> trivially testable through this Interface.
    """
    rows: List[Tuple[str, str]] = []
    percent: Optional[float] = None
    completions: List[Tuple[int, bool]] = []
    remaining = limit
    while remaining > 0:
        try:
            msg_type, data = q.get_nowait()
        except queue.Empty:
            break
        remaining -= 1
        if msg_type == "LINE":
            update = parse(data)  # ProgressUpdate duck-typed
            if getattr(update, "percent", None) is not None:
                percent = update.percent
            rows.append((getattr(update, "raw_line", data), getattr(update, "tag", "normal")))
        elif msg_type == "ERROR":
            rows.append((data, "danger"))
        elif msg_type == "DONE":
            exit_code, aborted = data
            completions.append((exit_code, aborted))
    return ParsedBatch(log_rows=rows, percent=percent, completions=completions)


def finish_patch(exit_code: int, aborted: bool, out_dir: str) -> FinishPatch:
    if aborted:
        return FinishPatch("Aborted", "danger", "Execution terminated by user.", "danger")
    if exit_code == 0:
        return FinishPatch("Standby", "success", f"\nPipeline finished. Payload saved to: {out_dir}", "success")
    return FinishPatch("Failed", "danger", f"\nPipeline halted with exit code {exit_code}.", "danger")
