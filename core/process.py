"""Module: process Seam (backward-compatible facade).

This file is the stable Seam: existing callers keep doing
`from core.process import AsyncProcessRunner, find_ffmpeg, ...`
while the Implementations live in deep Modules:
  - `core.runner`  -> AsyncProcessRunner
  - `core.ffmpeg`  -> find_ffmpeg (single cached source; Locality)
  - `core.format`  -> format_bytes / format_speed (pure)

Deletion test: deleting this file removes nothing but aliases —
complexity lives behind the new Modules, not here.
"""
from core.ffmpeg import find_ffmpeg
from core.format import format_bytes, format_speed
from core.runner import AsyncProcessRunner

__all__ = ["AsyncProcessRunner", "find_ffmpeg", "format_bytes", "format_speed"]
