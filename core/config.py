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
    # or in %APPDATA%, never inside the read-only _MEIPASS bundle.
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        try:
            p = exe_dir / "settings.json"
            p.touch(exist_ok=True)
            p.unlink(missing_ok=True)
            return p
        except OSError:
            pass
        appdata = Path(os.environ.get("APPDATA", str(Path.home()))) / "StreamRipCore"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata / "settings.json"
    return Path(__file__).resolve().parent.parent / "settings.json"


class SettingsManager:
    """Thread-safe settings manager for persisting user choices between sessions."""

    DEFAULT_SETTINGS = {
        "mode": "youtube",
        "youtube_out": str(Path.home() / "Videos" / "YouTubeDownloads"),
        "spotify_out": str(Path.home() / "Music" / "SpotifyDownloads"),
        "yt_stream": "Best Available (Source)",
        "yt_caption_env": "SubRip Subtitle (.srt)",
        "yt_capture_subs": True,
        "yt_transcript_only": False,
        "yt_lang": "en",
        "sp_stream": "MP3 Audio (.mp3)",
        "sp_bitrate": "Auto (Best Match)",
        "sp_generate_lrc": True,
        "sp_keep_archives": False,
    }

    def __init__(self, config_file: Optional[str] = None):
        if config_file:
            self.config_path = Path(config_file)
        else:
            self.config_path = _writable_config_path()

        self.data: Dict[str, Any] = dict(self.DEFAULT_SETTINGS)
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
