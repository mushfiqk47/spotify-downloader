"""Job store TTL/cap + URL allowlist. Skips if flask isn't installed (dev without venv)."""
import time

flask = __import__("pytest").importorskip("flask")

import server


def test_is_allowed_url_blocks_ssrf():
    assert server._is_allowed_url("https://www.youtube.com/watch?v=x", "youtube")
    assert server._is_allowed_url("https://youtu.be/x", "youtube")
    assert not server._is_allowed_url("https://open.spotify.com/track/x", "youtube")
    assert server._is_allowed_url("https://open.spotify.com/track/x", "spotify")
    assert not server._is_allowed_url("http://127.0.0.1:5050/admin", "youtube")
    assert not server._is_allowed_url("file:///etc/passwd", "youtube")
    assert not server._is_allowed_url("https://evil-youtube.com.evil.com/watch", "youtube")


def test_prune_evicts_done_and_caps_total(monkeypatch):
    monkeypatch.setattr(server, "MAX_JOBS", 3)
    monkeypatch.setattr(server, "DONE_JOB_TTL", 0.01)
    server._jobs.clear()
    old = time.time() - 100
    for i in range(5):
        server._jobs[f"job{i:08d}abcd"] = {
            "runner": None, "engine": None, "done": True, "exit_code": 0,
            "created_at": old + i, "completed_at": old + i, "last_poll": old + i,
        }
    with server._jobs_lock:
        server._prune_jobs(time.time())
    assert len(server._jobs) <= 3
    server._jobs.clear()
