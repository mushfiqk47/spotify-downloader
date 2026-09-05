"""
High-performance Spotify download engine powered by spotDL.
Features multi-threaded parallel downloads and pre-compiled regex parsing.
"""
import os
import re
import sys
from typing import List

from engines.base import BaseDownloadEngine, ProgressUpdate


class SpotifyEngine(BaseDownloadEngine):
    """Engine handling Spotify extraction with spotDL."""

    # Pre-compiled regular expressions
    RE_FOUND = re.compile(r"Found (\d+) (?:song|songs|track|tracks|file|files)", re.IGNORECASE)
    RE_DOWNLOADING = re.compile(r"Downloading\D*(\d+)\s*/\s*(\d+)", re.IGNORECASE)
    RE_DOWNLOADED = re.compile(r"Downloaded\D*(\d+)\s*/\s*(\d+)\s*file", re.IGNORECASE)
    RE_SUCCESS = re.compile(r"Downloaded|Completed|Done", re.IGNORECASE)
    RE_ERROR = re.compile(r"ERROR:|Failed|LookupError|Exception", re.IGNORECASE)

    FORMAT_MAP = {
        "MP3 Audio (.mp3)": "mp3",
        "FLAC Lossless (.flac)": "flac",
        "OGG Vorbis (.ogg)": "ogg",
        "Opus (.opus)": "opus",
        "M4A (.m4a)": "m4a",
        "WAV (.wav)": "wav",
    }

    BITRATE_MAP = {
        "Auto (Best Match)": "auto",
        "320 kbps (High)": "320k",
        "256 kbps": "256k",
        "192 kbps": "192k",
        "128 kbps": "128k",
    }

    def build_command(
        self,
        url: str,
        out_dir: str,
        stream_preset: str = "MP3 Audio (.mp3)",
        bitrate: str = "Auto (Best Match)",
        generate_lrc: bool = True,
        threads: int = 4,
        **kwargs,
    ) -> List[str]:
        fmt = self.FORMAT_MAP.get(stream_preset, "mp3")
        bit_val = self.BITRATE_MAP.get(bitrate, "auto")
        out_template = os.path.join(out_dir, "{artists} - {title}.{output-ext}")

        cmd = [
            sys.executable, "-m", "spotdl", "download", url,
            "--output", out_template,
            "--format", fmt,
            "--bitrate", bit_val,
            "--threads", str(threads),
            "--simple-tui",
            "--print-errors",
        ]

        if generate_lrc:
            cmd.append("--generate-lrc")

        return cmd

    def parse_line(self, line: str) -> ProgressUpdate:
        m_downloading = self.RE_DOWNLOADING.search(line)
        if m_downloading:
            curr, total = m_downloading.groups()
            return ProgressUpdate(
                current_item=int(curr),
                total_items=int(total),
                raw_line=line,
                tag="action_blue",
            )

        m_found = self.RE_FOUND.search(line)
        if m_found:
            total = m_found.group(1)
            return ProgressUpdate(
                total_items=int(total),
                raw_line=line,
                tag="muted",
            )

        if self.RE_SUCCESS.search(line):
            return ProgressUpdate(raw_line=line, tag="success")

        if self.RE_ERROR.search(line):
            return ProgressUpdate(raw_line=line, tag="danger")

        return ProgressUpdate(raw_line=line, tag="normal")
