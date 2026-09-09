"""Pipeline queue pump + finish patch — no Qt/Tk, no network."""
import queue

from app_pipeline import MAX_ITEMS_PER_TICK, drain_queue, finish_patch


class FakeUpdate:
    def __init__(self, raw_line, tag="normal", percent=None):
        self.raw_line = raw_line
        self.tag = tag
        self.percent = percent


def _q(*items):
    q = queue.Queue()
    for it in items:
        q.put(it)
    return q


def test_drain_parses_lines_and_caps_at_limit():
    q = _q(*[("LINE", f"line {i}") for i in range(MAX_ITEMS_PER_TICK + 10)])
    batch = drain_queue(q, lambda line: FakeUpdate(line, percent=12.5))
    assert len(batch.log_rows) == MAX_ITEMS_PER_TICK
    assert batch.percent == 12.5
    assert q.qsize() == 10  # remainder left for next tick


def test_drain_collects_errors_and_completions():
    q = _q(
        ("LINE", "[download] 45.2% of 10MiB"),
        ("ERROR", "boom"),
        ("DONE", (0, False)),
    )
    batch = drain_queue(
        q, lambda line: FakeUpdate(line, percent=45.2 if "45.2" in line else None)
    )
    assert batch.log_rows[0][1] == "normal"
    assert batch.log_rows[1] == ("boom", "danger")
    assert batch.completions == [(0, False)]
    assert batch.percent == 45.2


def test_drain_empty_queue_returns_empty_batch():
    batch = drain_queue(queue.Queue(), lambda line: FakeUpdate(line))
    assert batch.log_rows == [] and batch.percent is None and batch.completions == []


def test_finish_patch_success_abort_failure():
    ok = finish_patch(0, False, "/tmp/out")
    assert ok.status == "Standby" and "/tmp/out" in ok.message
    aborted = finish_patch(1, True, "/tmp/out")
    assert aborted.status == "Aborted"
    failed = finish_patch(1, False, "/tmp/out")
    assert failed.status == "Failed" and "1" in failed.message
