"""
High-performance YouTube download engine powered by yt-dlp.
Features pre-compiled regex parsing and concurrent fragment acceleration.
"""
import os
import re
import shutil
import sys
from typing import List

from engines.base import BaseDownloadEngine, ProgressUpdate, find_ffmpeg, get_python_exe, is_frozen


class YouTubeEngine(BaseDownloadEngine):
    """Engine handling YouTube extraction with yt-dlp."""

    # Pre-compiled regular expressions for maximum parsing throughput
    RE_DOWNLOAD_PCT = re.compile(
        r"\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+(?:~\s*)?([^\s]+)(?:\s+at\s+(.+?)\s+ETA\s+([^\s]+))?"
    )
    RE_ITEM_QUEUE = re.compile(
        r"\[download\] Downloading (?:video|item) (\d+) of (\d+)",
        re.IGNORECASE,
    )
    RE_SUCCESS = re.compile(r"100%|has already been downloaded|Finished downloading", re.IGNORECASE)
    RE_ERROR = re.compile(r"ERROR:|WARNING: Unable|HTTP Error", re.IGNORECASE)

    STREAM_PRESETS = {
        "Best Available (Source)": "bestvideo+bestaudio/best",
        "1080p (FHD)": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "720p (HD)": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "480p (SD)": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        "Audio Only (.mp3)": "mp3",
        "Audio Only (.m4a)": "m4a",
    }

    CAPTION_EXT_MAP = {
        "SubRip Subtitle (.srt)": "srt",
        "WebVTT (.vtt)": "vtt",
        "Advanced SubStation (.ass)": "ass",
        "Timed Lyrics (.lrc)": "lrc",
    }

    # Audio Quality menu (shown when File Format is an audio target).
    # Values are yt-dlp --audio-quality levels (0 = best, 10 = smallest).
    AUDIO_QUALITY_MAP = {
        "Best Available": "0",
        "High Quality": "2",
        "Medium Quality": "5",
        "Compact File": "8",
    }

    # File Format menu. Video entries remux the download into that container
    # (no re-encode); audio entries extract just the audio track instead.
    FILE_FORMAT_MAP = {
        "Match Source (no conversion)": (None, None),
        "MP4 Video (.mp4)": ("remux", "mp4"),
        "MKV Video (.mkv)": ("remux", "mkv"),
        "MP3 Audio (.mp3)": ("audio", "mp3"),
        "M4A Audio (.m4a)": ("audio", "m4a"),
        "OPUS Audio (.opus)": ("audio", "opus"),
        "FLAC Audio (.flac)": ("audio", "flac"),
        "WAV Audio (.wav)": ("audio", "wav"),
    }

    def build_command(
        self,
        url: str,
        out_dir: str,
        stream_preset: str = "Best Available (Source)",
        caption_env: str = "SubRip Subtitle (.srt)",
        capture_subs: bool = False,
        transcript_only: bool = False,
        lang: str = "en",
        concurrent_fragments: int = 4,
        file_format: str = "Match Source (no conversion)",
        audio_quality: str = "Best Available",
        **kwargs,
    ) -> List[str]:
        if is_frozen():
            # Inside the packaged exe there is no system python.
            # Re-invoke our own backend exe which forwards to yt-dlp in-process.
            cmd = [sys.executable, "--engine-yt-dlp"]
        else:
            cmd = [get_python_exe(), "-m", "yt_dlp"]

        # 0. JavaScript runtime (fixes extraction & throttled format errors in yt-dlp)
        if shutil.which("node"):
            cmd.extend(["--js-runtimes", "node"])
        elif shutil.which("deno"):
            cmd.extend(["--js-runtimes", "deno"])

        # 1. Format / Stream selection + File Format menu (audio wins over video)
        preset_val = self.STREAM_PRESETS.get(stream_preset, "bestvideo+bestaudio/best")
        kind, codec = self.FILE_FORMAT_MAP.get(file_format, (None, None))
        preset_is_audio = preset_val in ("mp3", "m4a")
        ffmpeg = find_ffmpeg()

        if kind == "audio" or (kind is None and preset_is_audio):
            # Extract just the audio track (best audio source) at the chosen quality.
            audio_codec = codec or preset_val
            aq = self.AUDIO_QUALITY_MAP.get(audio_quality, "0")
            cmd.extend(["-f", "bestaudio/best", "-x",
                        "--audio-format", audio_codec, "--audio-quality", aq])
        elif preset_is_audio:
            # Legacy audio-only presets with Match Source.
            cmd.extend(["-x", "--audio-format", preset_val, "--audio-quality", "0"])
        else:
            cmd.extend(["-f", preset_val])
            # 2. Performance: Multi-connection concurrent fragment downloading
            if concurrent_fragments > 1:
                cmd.extend(["--concurrent-fragments", str(concurrent_fragments)])
            if kind == "remux" and ffmpeg:
                cmd.extend(["--remux-video", codec])

        # 3. FFmpeg integration
        if ffmpeg:
            cmd.extend(["--ffmpeg-location", ffmpeg])

        # 4. Subtitles / Transcripts
        if capture_subs:
            sub_ext = self.CAPTION_EXT_MAP.get(caption_env, "srt")
            clean_lang = lang.strip() or "en"
            sub_lang_spec = f"{clean_lang}.*,{clean_lang}" if clean_lang == "en" else clean_lang
            cmd.extend([
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", sub_lang_spec,
                "--sub-format", "best",
            ])
            if ffmpeg:
                cmd.extend(["--convert-subs", sub_ext])
            if transcript_only:
                cmd.append("--skip-download")

        # 5. Output template & flags
        out_template = os.path.join(out_dir, "%(title)s.%(ext)s")
        cmd.extend(["-o", out_template, "--newline", "--no-warnings", url])
        return cmd

    def parse_line(self, line: str) -> ProgressUpdate:
        # Check percentage download progress
        m_pct = self.RE_DOWNLOAD_PCT.search(line)
        if m_pct:
            pct_str, total_sz, spd, eta = m_pct.groups()
            tag = "success" if float(pct_str) >= 100.0 else "action_blue"
            return ProgressUpdate(
                percent=float(pct_str),
                total_size=total_sz,
                speed=spd,
                eta=eta,
                raw_line=line,
                tag=tag,
            )

        # Check playlist/queue progress
        m_queue = self.RE_ITEM_QUEUE.search(line)
        if m_queue:
            curr, total = m_queue.groups()
            return ProgressUpdate(
                current_item=int(curr),
                total_items=int(total),
                raw_line=line,
                tag="normal",
            )

        if self.RE_SUCCESS.search(line):
            return ProgressUpdate(raw_line=line, tag="success")

        if self.RE_ERROR.search(line):
            return ProgressUpdate(raw_line=line, tag="danger")

        return ProgressUpdate(raw_line=line, tag="normal")
