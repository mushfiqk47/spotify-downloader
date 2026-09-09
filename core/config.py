"""
Settings persistence manager for StreamRip Core.
Saves and loads user preferences to a local JSON file.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _writable_config_path() -> Path:
    # Frozen (PyInstaller / Electron): settings must live next to the exe
    # or in user config dir, never inside the read-only _MEIPASS bundle.
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        try:
            p = exe_dir / "settings.json"
            p.touch(exist_ok=True)
            p.unlink(missing_ok=True)
            return p
        except OSError:
            pass

        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", str(Path.home())))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            # Linux / Unix XDG standard (Ubuntu, Arch, etc.)
            xdg = os.environ.get("XDG_CONFIG_HOME")
            base = Path(xdg) if xdg else Path.home() / ".config"

        app_dir = base / "StreamRipCore"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "settings.json"
    return Path(__file__).resolve().parent.parent / "settings.json"


def default_youtube_out() -> str:
    base = "Movies" if sys.platform == "darwin" else "Videos"
    return str(Path.home() / base / "YouTubeDownloads")


def default_spotify_out() -> str:
    return str(Path.home() / "Music" / "SpotifyDownloads")


def default_settings() -> Dict[str, Any]:
    # Computed fresh on every call so each OS user gets THEIR OWN home
    # dir, never another machine's absolute path baked in at import time.
    return {
        "mode": "youtube",
        "youtube_out": default_youtube_out(),
        "spotify_out": default_spotify_out(),
        "yt_stream": "Best Available (Source)",
        "yt_caption_env": "SubRip Subtitle (.srt)",
        "yt_capture_subs": False,
        "yt_transcript_only": False,
        "yt_lang": "English",
        "yt_file_format": "Match Source (no conversion)",
        "yt_audio_quality": "Best Available",
        "sp_stream": "MP3 Audio (.mp3)",
        "sp_bitrate": "Auto (Best Match)",
        "sp_generate_lrc": False,
        "sp_keep_archives": False,
    }


def _sanitize_out_dir(value: Any, default: str) -> str:
    """Drop stale paths left by another machine/user (e.g. a shipped
    settings.json containing ``C:\\Users\\SomeoneElse\\...``).

    Keep the stored value when it exists on disk (user-picked folders
    always exist because they come from a folder dialog) or when it sits
    under the CURRENT user's home (may be created on first download).
    Anything else falls back to this user's default.
    """
    if not isinstance(value, str) or not value.strip():
        return default
    cleaned = os.path.expandvars(os.path.expanduser(value.strip()))
    try:
        p = Path(cleaned)
    except Exception:
        return default
    try:
        if p.exists():
            return str(p)
    except OSError:
        return default
    try:
        p.relative_to(Path.home())
        return str(p)
    except Exception:
        return default


class SettingsManager:
    """Thread-safe settings manager for persisting user choices between sessions."""

    DEFAULT_SETTINGS = default_settings()

    def __init__(self, config_file: Optional[str] = None):
        if config_file:
            self.config_path = Path(config_file)
        else:
            self.config_path = _writable_config_path()

        self.data: Dict[str, Any] = default_settings()
        self.load()

    def load(self):
        """Loads configuration from JSON file, merging with default values."""
        if self.config_path.is_file():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception:
                pass
        self.sanitize()

    def sanitize(self):
        """Reset out-dirs that belong to another user/machine to this user's defaults."""
        defaults = default_settings()
        for key in ("youtube_out", "spotify_out"):
            self.data[key] = _sanitize_out_dir(self.data.get(key), defaults[key])
        if self.data.get("mode") not in ("youtube", "spotify"):
            self.data["mode"] = defaults["mode"]

    def save(self):
        """Persists current configuration to disk safely."""
        try:
            temp_path = self.config_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            temp_path.replace(self.config_path)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any):
        self.data[key] = value

    def set_many(self, items: Dict[str, Any]):
        self.data.update(items)
