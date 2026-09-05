"""
High-performance YouTube download engine powered by yt-dlp.
Features pre-compiled regex parsing and concurrent fragment acceleration.
"""
import os
import re
import sys
from typing import List

from engines.base import BaseDownloadEngine, ProgressUpdate, find_ffmpeg


class YouTubeEngine(BaseDownloadEngine):
    """Engine handling YouTube extraction with yt-dlp."""

    # Pre-compiled regular expressions for maximum parsing throughput
    RE_DOWNLOAD_PCT = re.compile(
        r"\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+(?:~\s*)?([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)"
    )
    RE_ITEM_QUEUE = re.compile(
        r"\[download\] Downloading (?:video|item) (\d+) of (\d+)",
        re.IGNORECASE,
    )
    RE_SUCCESS = re.compile(r"100%|has already been downloaded|Finished downloading", re.IGNORECASE)
    RE_ERROR = re.compile(r"ERROR:|WARNING: Unable|HTTP Error", re.IGNORECASE)

    STREAM_PRESETS = {
        "Best Available (Source)": "best",
        "1080p (FHD)": "best[height<=1080]",
        "720p (HD)": "best[height<=720]",
        "480p (SD)": "best[height<=480]",
        "Audio Only (.mp3)": "mp3",
        "Audio Only (.m4a)": "m4a",
    }

    CAPTION_EXT_MAP = {
        "SubRip Subtitle (.srt)": "srt",
        "WebVTT (.vtt)": "vtt",
        "Advanced SubStation (.ass)": "ass",
        "Timed Lyrics (.lrc)": "lrc",
    }

    def build_command(
        self,
        url: str,
        out_dir: str,
        stream_preset: str = "Best Available (Source)",
        caption_env: str = "SubRip Subtitle (.srt)",
        capture_subs: bool = True,
        transcript_only: bool = False,
        lang: str = "en",
        concurrent_fragments: int = 4,
        **kwargs,
    ) -> List[str]:
        cmd = [sys.executable, "-m", "yt_dlp"]

        # 1. Format / Stream selection
        preset_val = self.STREAM_PRESETS.get(stream_preset, "best")
        if preset_val == "mp3":
            cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
        elif preset_val == "m4a":
            cmd.extend(["-x", "--audio-format", "m4a", "--audio-quality", "0"])
        elif preset_val == "best":
            cmd.extend(["-f", "bestvideo+bestaudio/best"])
        else:
            cmd.extend(["-f", f"{preset_val}+bestaudio/best"])

        # 2. Performance: Multi-connection concurrent fragment downloading
        if concurrent_fragments > 1 and preset_val not in ("mp3", "m4a"):
            cmd.extend(["--concurrent-fragments", str(concurrent_fragments)])

        # 3. FFmpeg integration
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            cmd.extend(["--ffmpeg-location", ffmpeg])

        # 4. Subtitles / Transcripts
        if capture_subs:
            sub_ext = self.CAPTION_EXT_MAP.get(caption_env, "srt")
            clean_lang = lang.strip() or "en"
            cmd.extend([
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", clean_lang,
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
            return ProgressUpdate(
                percent=float(pct_str),
                total_size=total_sz,
                speed=spd,
                eta=eta,
                raw_line=line,
                tag="action_blue",
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
