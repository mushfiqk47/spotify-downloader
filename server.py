"""StreamRip backend: serves UI.html + JSON API for downloads and updates.

Run:  python server.py  ->  http://127.0.0.1:5050
API:
  GET  /                        -> UI.html
  GET  /css/<path>, /js/<path>, /Logo.svg -> static assets (frozen-safe)
  GET  /api/health              -> {ok: True} (lightweight Electron readiness probe)
  GET  /api/config              -> defaults + ffmpeg status
  GET  /api/browse?path=...     -> folder listing for Browse button
  POST /api/browse-native       -> real OS folder window (browser mode too)
  GET  /api/check-updates       -> {updates: {name: [current, latest]}}
  POST /api/update              -> {job_id} (pip upgrade in background)
  POST /api/download            -> {job_id} (yt-dlp / spotdl in background)
  GET  /api/job/<job_id>        -> {logs: [{msg, tag}], percent, done, exit_code}
  POST /api/job/<job_id>/abort  -> {ok: true}
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
import gettext as _gettext

# Ensure gettext never crashes with FileNotFoundError if a locale domain is missing (e.g. ytmusicapi 'base' in frozen env)
_orig_gettext_translation = _gettext.translation
def _safe_gettext_translation(domain, localedir=None, languages=None, class_=None, fallback=False, codeset=None):
    try:
        return _orig_gettext_translation(domain, localedir=localedir, languages=languages, class_=class_, fallback=fallback)
    except FileNotFoundError:
        return _orig_gettext_translation(domain, localedir=localedir, languages=languages, class_=class_, fallback=True)
_gettext.translation = _safe_gettext_translation

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
    if getattr(sys, "frozen", False):
        # onedir: datas (UI.html, css/, js/) live in _internal/ next to the exe.
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "_internal" / "UI.html").is_file():
            return exe_dir / "_internal"
        return exe_dir
    return Path(__file__).resolve().parent


BASE_DIR = _base_dir()
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")

settings = SettingsManager()
yt_engine = YouTubeEngine()
sp_engine = SpotifyEngine()

# job_id -> {"runner": AsyncProcessRunner, "engine": engine|None, "done": bool,
#            "exit_code": int|None, "created_at": float, "completed_at": float|None,
#            "last_poll": float}
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

# Hard caps so a long-lived desktop session can never grow _jobs unbounded.
# Done jobs expire fast (UI already showed the result); running jobs get a
# generous TTL so an overnight playlist can't be reaped mid-run.
MAX_JOBS = 20
DONE_JOB_TTL = 600.0  # 10 min after completion
JOB_TTL = 86400.0  # 24 h absolute max (abandoned running job)

# /api/browse hardening: a single huge directory (e.g. C:\Windows\WinSxS)
# must not blow up the JSON response or hang the UI modal.
BROWSE_MAX_DIRS = 500

# SSRF guard (CWE-918): this backend listens on localhost, but yt-dlp/spotdl
# follow any URL they're given. Only allow the hosts this app is built for.
_ALLOWED_HOSTS = {
    "youtube": ("youtube.com", "www.youtube.com", "youtu.be", "music.youtube.com"),
    "spotify": ("open.spotify.com",),
}


def _is_allowed_url(url: str, mode: str) -> bool:
    try:
        from urllib.parse import urlparse

        parts = urlparse(url)
        if parts.scheme not in ("http", "https"):
            return False
        host = (parts.hostname or "").lower()
        return host in _ALLOWED_HOSTS.get(mode, ()) or any(
            host.endswith("." + base) for base in _ALLOWED_HOSTS.get(mode, ())
        )
    except Exception:
        return False


def _prune_jobs(now: float | None = None) -> None:
    """Evict expired / excess jobs. Caller must hold _jobs_lock."""
    now = time.time() if now is None else now
    # 1. Expire done jobs past DONE_JOB_TTL, and anything past absolute TTL.
    expired = [
        jid
        for jid, job in _jobs.items()
        if (job.get("done") and now - job.get("completed_at", job["created_at"]) > DONE_JOB_TTL)
        or (now - job["created_at"] > JOB_TTL)
    ]
    for jid in expired:
        _jobs.pop(jid, None)
    # 2. Enforce cap: evict oldest done first, then oldest overall.
    while len(_jobs) > MAX_JOBS:
        done_ids = sorted(
            (jid for jid, j in _jobs.items() if j.get("done")),
            key=lambda jid: _jobs[jid]["created_at"],
        )
        victim = done_ids[0] if done_ids else min(_jobs, key=lambda jid: _jobs[jid]["created_at"])
        _jobs.pop(victim, None)


def _new_job(runner: AsyncProcessRunner, engine=None) -> str:
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    with _jobs_lock:
        _prune_jobs(now)
        _jobs[job_id] = {
            "runner": runner,
            "engine": engine,
            "done": False,
            "exit_code": None,
            "created_at": now,
            "completed_at": None,
            "last_poll": now,
        }
        _prune_jobs(now)
    return job_id


def _mark_done(job: dict, exit_code: int | None) -> None:
    job["done"] = True
    job["exit_code"] = exit_code
    job["completed_at"] = time.time()


@app.get("/")
def index():
    return send_from_directory(str(BASE_DIR), "UI.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


# Explicit frozen-safe static routes (do not rely on Flask static_url_path
# semantics inside the PyInstaller bundle / Electron asar).
@app.get("/css/<path:name>")
def serve_css(name: str):
    return send_from_directory(str(BASE_DIR / "css"), name)


@app.get("/js/<path:name>")
def serve_js(name: str):
    return send_from_directory(str(BASE_DIR / "js"), name)


@app.get("/Logo.svg")
def serve_logo():
    return send_from_directory(str(BASE_DIR), "Logo.svg")


_PREF_KEYS = ("mode", "youtube_out", "spotify_out", "yt_stream", "yt_caption_env",
               "yt_capture_subs", "yt_transcript_only", "yt_lang", "yt_file_format",
               "yt_audio_quality", "sp_stream", "sp_bitrate", "sp_generate_lrc",
               "sp_keep_archives")


def _config_payload() -> dict:
    return {k: settings.get(k) for k in _PREF_KEYS}


@app.get("/api/config")
def get_config():
    # Belt-and-braces: sanitize on every read so a stale settings file
    # from another machine can never leak another user's home dir to this UI.
    try:
        settings.sanitize()
    except Exception:
        pass
    try:
        from core.ffmpeg import find_ffmpeg as _find_ffmpeg
        ffmpeg = _find_ffmpeg()
    except Exception:
        ffmpeg = None
    return jsonify({
        **_config_payload(),
        "platform": sys.platform,
        "frozen": is_frozen(),
        "ffmpeg": ffmpeg,
        "ffmpeg_ok": bool(ffmpeg),
    })


@app.post("/api/config")
def save_config():
    """Persist this user's own choices (out folders, mode). Only whitelisted keys."""
    body = request.get_json(silent=True) or {}
    allowed = set(_PREF_KEYS)
    patch: dict = {}
    for key in allowed:
        if key not in body:
            continue
        value = body[key]
        if key in ("youtube_out", "spotify_out"):
            if not isinstance(value, str) or not value.strip():
                continue
            value = os.path.expandvars(os.path.expanduser(value.strip()))
            try:
                if not Path(value).is_absolute():
                    continue
            except Exception:
                continue
        if key == "mode" and value not in ("youtube", "spotify"):
            continue
        if key == "yt_lang" and value not in YouTubeEngine.ALLOWED_LANGS:
            continue
        patch[key] = value
    if patch:
        settings.set_many(patch)
        try:
            settings.sanitize()
        except Exception:
            pass
        settings.save()
    return jsonify({
        "ok": True,
        **_config_payload(),
    })


def _native_dialog_available() -> bool:
    """True when this machine can pop a real OS folder window."""
    if sys.platform in ("win32", "darwin"):
        return True  # PowerShell FolderBrowserDialog / osascript — always present
    return bool(shutil.which("zenity") or shutil.which("kdialog"))


def _native_dialog(start: str | None) -> str | None:
    """Open the real OS folder window on THIS machine and return the picked
    absolute path, or None on cancel/failure. Backend and browser run on the
    same box, so the window appears on the user's screen. No tkinter needed
    (it is excluded from the frozen build)."""
    if sys.platform == "win32":
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
            "$d.Description = 'Choose export folder';"
            "$d.ShowNewFolderButton = $true;"
        )
        env = dict(os.environ)
        if start:
            env["STREAMRIP_BROWSE_START"] = start
            ps += "$d.SelectedPath = $env:STREAMRIP_BROWSE_START;"
        ps += "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $d.SelectedPath }"
        try:
            # NOTE: no CREATE_NO_WINDOW here — we WANT the window to show.
            proc = subprocess.run(
                ["powershell", "-sta", "-noprofile", "-noninteractive", "-command", ps],
                capture_output=True, text=True, timeout=180, env=env)
        except Exception:
            return None
        return (proc.stdout or "").strip() or None
    if sys.platform == "darwin":
        try:
            proc = subprocess.run(
                ["osascript", "-e", 'POSIX path of (choose folder with prompt "Choose export folder")'],
                capture_output=True, text=True, timeout=180)
        except Exception:
            return None
        return (proc.stdout or "").strip() or None
    for cmd in (["zenity", "--file-selection", "--directory", "--title=Choose export folder"],
                ["kdialog", "--getexistingdirectory", os.path.expanduser("~")]):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except FileNotFoundError:
            continue
        except Exception:
            return None
        out = (proc.stdout or "").strip()
        return out or None
    return None


@app.post("/api/browse-native")
def browse_native():
    """Open the real OS folder window. Body: {start?: existing dir}.
    -> {picked: str|None, cancelled: bool, available: bool}"""
    if not _native_dialog_available():
        return jsonify({"picked": None, "cancelled": False, "available": False})
    body = request.get_json(silent=True) or {}
    start = (body.get("start") or "").strip() or None
    if start:
        try:
            if not Path(start).exists():
                start = None
        except Exception:
            start = None
    picked = _native_dialog(start)
    if not picked:
        return jsonify({"picked": None, "cancelled": True, "available": True})
    return jsonify({"picked": picked, "cancelled": False, "available": True})


def _list_drives():
    """Windows drive roots (C:\\, D:\\, ...) that actually exist."""
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        try:
            if Path(root).exists():
                drives.append(root)
        except Exception:
            continue
    return drives


@app.get("/api/browse")
def browse_folders():
    """Folder browser for the UI Browse button (works in browser mode too).

    GET /api/browse?path=<abs path>  -> {path, parent, dirs: [{name, path}], drives, home}
    GET /api/browse                   -> starts at current out_dir / home.
    GET /api/browse?path=__drives__   -> Windows drive list only.
    Only directories are listed; files are never exposed.
    """
    raw = (request.args.get("path") or "").strip()
    if raw == "__drives__":
        drives = _list_drives()
        return jsonify({"path": "__drives__", "parent": None, "dirs": [
            {"name": d, "path": d} for d in drives], "drives": drives,
            "home": str(Path.home())})
    if not raw:
        raw = settings.get("youtube_out") or str(Path.home())
    # allow home-relative shorthand
    p = Path(os.path.expandvars(os.path.expanduser(raw)))
    try:
        if not p.exists():
            # fall back to nearest existing ancestor
            for parent in [p, *p.parents]:
                if parent.exists():
                    p = parent
                    break
        if p.is_file():
            p = p.parent
        p = p.resolve()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    try:
        entries = sorted(
            (d for d in p.iterdir() if d.is_dir()),
            key=lambda d: d.name.lower())
        dirs = [{"name": d.name, "path": str(d)} for d in entries
                if not d.name.startswith("$")][:BROWSE_MAX_DIRS]
        truncated = len(entries) > len(dirs)
    except PermissionError:
        return jsonify({"error": f"Access denied: {p}", "path": str(p)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    parent = str(p.parent) if p.parent != p else None
    drives = _list_drives() if sys.platform == "win32" else []
    return jsonify({
        "path": str(p), "parent": parent, "dirs": dirs,
        "truncated": truncated,
        "drives": drives, "home": str(Path.home()),
        "sep": os.sep,
    })


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
    if len(url) > 2048:
        return jsonify({"error": "URL too long"}), 400

    mode = body.get("mode") or settings.get("mode", "youtube")
    if mode not in ("youtube", "spotify"):
        return jsonify({"error": "Invalid mode"}), 400
    if not _is_allowed_url(url, mode):
        expected = "youtube.com / youtu.be" if mode == "youtube" else "open.spotify.com"
        return jsonify({"error": f"URL must be a {expected} link for {mode} mode"}), 400

    out_dir = (body.get("out_dir") or "").strip() or str(
        settings.get("youtube_out" if mode == "youtube" else "spotify_out")
        or Path.home() / ("Videos/YouTubeDownloads" if mode == "youtube" else "Music/SpotifyDownloads")
    )
    try:
        out_path = Path(os.path.expandvars(os.path.expanduser(out_dir)))
        if not out_path.is_absolute():
            return jsonify({"error": "Export folder must be an absolute path"}), 400
        out_path.mkdir(parents=True, exist_ok=True)
        out_dir = str(out_path)
    except OSError as e:
        return jsonify({"error": f"Cannot create export folder: {e}"}), 400

    _lang = body.get("yt_lang") or settings.get("yt_lang", "English")
    if _lang not in YouTubeEngine.ALLOWED_LANGS:
        _lang = "English"

    if mode == "youtube":
        engine = yt_engine
        cmd = engine.build_command(
            url=url, out_dir=out_dir,
            stream_preset=body.get("yt_stream") or settings.get("yt_stream"),
            caption_env=body.get("yt_caption_env") or settings.get("yt_caption_env"),
            capture_subs=bool(body.get("yt_capture_subs", settings.get("yt_capture_subs", False))),
            transcript_only=bool(body.get("yt_transcript_only", False)),
            lang=_lang,
            file_format=(body.get("yt_file_format") or settings.get("yt_file_format")),
            audio_quality=(body.get("yt_audio_quality") or settings.get("yt_audio_quality", "Best Available")),
        )
    else:
        engine = sp_engine
        cmd = engine.build_command(
            url=url, out_dir=out_dir,
            stream_preset=body.get("sp_stream") or settings.get("sp_stream"),
            bitrate=body.get("sp_bitrate") or settings.get("sp_bitrate"),
            generate_lrc=bool(body.get("sp_generate_lrc", settings.get("sp_generate_lrc", False))),
        )

    # block parallel downloads on the shared engine runner: use a fresh runner per job
    runner = AsyncProcessRunner()
    runner.start(cmd=cmd)
    job_id = _new_job(runner, engine)
    return jsonify({"job_id": job_id, "out_dir": out_dir})


@app.get("/api/job/<job_id>")
def poll_job(job_id: str):
    if not isinstance(job_id, str) or len(job_id) != 12 or not all(
        c in "0123456789abcdef" for c in job_id
    ):
        return jsonify({"error": "unknown job"}), 404
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is not None:
            job["last_poll"] = time.time()
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
            with _jobs_lock:
                _mark_done(job, exit_code)
        return jsonify({"logs": logs, "percent": None, "done": job["done"], "exit_code": job["exit_code"]})

    batch = drain_queue(runner.output_queue, engine.parse_line)
    logs = [{"msg": m, "tag": t} for m, t in batch.log_rows]
    done = False
    exit_code = None
    for code, _aborted in batch.completions:
        done = True
        exit_code = code
    if done:
        with _jobs_lock:
            _mark_done(job, exit_code)
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
