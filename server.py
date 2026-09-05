"""StreamRip backend: serves UI.html + JSON API for downloads and updates.

Run:  python server.py  ->  http://127.0.0.1:5050
API:
  GET  /                        -> UI.html
  GET  /api/check-updates       -> {updates: {name: [current, latest]}}
  POST /api/update              -> {job_id} (pip upgrade in background)
  POST /api/download            -> {job_id} (yt-dlp / spotdl in background)
  GET  /api/job/<job_id>        -> {logs: [{msg, tag}], percent, done, exit_code}
  POST /api/job/<job_id>/abort  -> {ok: true}
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from app_pipeline import drain_queue
from core.config import SettingsManager
from core.runner import AsyncProcessRunner
from core.updater import PACKAGES, build_check_command, build_update_command, parse_outdated_json
from engines import SpotifyEngine, YouTubeEngine
from engines.base import get_python_exe, is_frozen


def _base_dir() -> Path:
    # PyInstaller onefile unpacks bundled data to sys._MEIPASS at runtime.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


BASE_DIR = _base_dir()
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")

settings = SettingsManager()
yt_engine = YouTubeEngine()
sp_engine = SpotifyEngine()

# job_id -> {"runner": AsyncProcessRunner, "engine": engine|None, "done": bool, "exit_code": int|None}
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _new_job(runner: AsyncProcessRunner, engine=None) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"runner": runner, "engine": engine, "done": False, "exit_code": None}
    return job_id


@app.get("/")
def index():
    return send_from_directory(str(BASE_DIR), "UI.html")


@app.get("/api/check-updates")
def check_updates():
    if is_frozen():
        # Packaged exe has no pip-managed environment to upgrade in place.
        return jsonify({"updates": {}, "frozen": True}), 200
    try:
        cmd = build_check_command(get_python_exe())
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        updates = parse_outdated_json(proc.stdout or "")
        return jsonify({"updates": {k: list(v) for k, v in updates.items()}})
    except Exception as e:
        return jsonify({"updates": {}, "error": str(e)}), 200


@app.post("/api/update")
def start_update():
    if is_frozen():
        return jsonify({"error": "Self-update is managed by the installer in the packaged app."}), 400
    body = request.get_json(silent=True) or {}
    pkgs = body.get("packages") or list(PACKAGES)
    # only allow known packages (no arbitrary pip installs)
    pkgs = [p for p in pkgs if p.lower() in {x.lower() for x in PACKAGES}]
    if not pkgs:
        pkgs = list(PACKAGES)
    runner = AsyncProcessRunner()
    runner.start(cmd=build_update_command(get_python_exe(), pkgs))
    job_id = _new_job(runner, None)
    return jsonify({"job_id": job_id, "packages": pkgs})


@app.post("/api/download")
def start_download():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip().strip('"').strip("'")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    mode = body.get("mode") or settings.get("mode", "youtube")
    out_dir = (body.get("out_dir") or "").strip() or str(
        Path.home() / ("Videos/YouTubeDownloads" if mode == "youtube" else "Music/SpotifyDownloads")
    )
    os.makedirs(out_dir, exist_ok=True)

    if mode == "youtube":
        engine = yt_engine
        cmd = engine.build_command(
            url=url, out_dir=out_dir,
            stream_preset=body.get("yt_stream") or settings.get("yt_stream"),
            caption_env=body.get("yt_caption_env") or settings.get("yt_caption_env"),
            capture_subs=bool(body.get("yt_capture_subs", settings.get("yt_capture_subs", True))),
            transcript_only=bool(body.get("yt_transcript_only", False)),
            lang=(body.get("yt_lang") or settings.get("yt_lang", "en")),
        )
    else:
        engine = sp_engine
        cmd = engine.build_command(
            url=url, out_dir=out_dir,
            stream_preset=body.get("sp_stream") or settings.get("sp_stream"),
            bitrate=body.get("sp_bitrate") or settings.get("sp_bitrate"),
            generate_lrc=bool(body.get("sp_generate_lrc", settings.get("sp_generate_lrc", True))),
        )

    # block parallel downloads on the shared engine runner: use a fresh runner per job
    runner = AsyncProcessRunner()
    runner.start(cmd=cmd)
    job_id = _new_job(runner, engine)
    return jsonify({"job_id": job_id, "out_dir": out_dir})


@app.get("/api/job/<job_id>")
def poll_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404

    runner: AsyncProcessRunner = job["runner"]
    engine = job["engine"]

    if engine is None:
        # updater job: raw lines, tag by keyword
        logs: list[dict] = []
        done = False
        exit_code = None
        while True:
            try:
                msg_type, data = runner.output_queue.get_nowait()
            except Exception:
                break
            if msg_type == "LINE":
                low = data.lower()
                tag = "danger" if ("error" in low or "failed" in low) else (
                    "success" if "successfully installed" in low else "muted")
                logs.append({"msg": data, "tag": tag})
            elif msg_type == "ERROR":
                logs.append({"msg": data, "tag": "danger"})
            elif msg_type == "DONE":
                exit_code, _aborted = data
                done = True
        if done:
            job["done"] = True
            job["exit_code"] = exit_code
        return jsonify({"logs": logs, "percent": None, "done": job["done"], "exit_code": job["exit_code"]})

    batch = drain_queue(runner.output_queue, engine.parse_line)
    logs = [{"msg": m, "tag": t} for m, t in batch.log_rows]
    done = False
    exit_code = None
    for code, _aborted in batch.completions:
        done = True
        exit_code = code
    if done:
        job["done"] = True
        job["exit_code"] = exit_code
    return jsonify({"logs": logs, "percent": batch.percent, "done": job["done"], "exit_code": job["exit_code"]})


@app.post("/api/job/<job_id>/abort")
def abort_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    try:
        job["runner"].abort()
    except Exception:
        pass
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Engine forwarder: lets the frozen exe run yt-dlp / spotdl in-process
    # via subprocesses of itself (no system python needed).
    if len(sys.argv) >= 2 and sys.argv[1] == "--engine-yt-dlp":
        from yt_dlp import main as _yt_main
        sys.exit(_yt_main(sys.argv[2:]))
    if len(sys.argv) >= 2 and sys.argv[1] == "--engine-spotdl":
        from spotdl.console import console_entry_point as _sp_main
        sys.argv = ["spotdl", *sys.argv[2:]]
        sys.exit(_sp_main())
    port = int(os.environ.get("STREAMRIP_PORT", "5050"))
    print(f"StreamRip backend on http://127.0.0.1:{port}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
