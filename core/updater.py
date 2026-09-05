"""Module: dependency update checks + upgrades.

Deep Module: tiny Interface for the Tk Adapter (app.py).
  PACKAGES                -> list of managed deps
  build_check_command()   -> [python, -m, pip, list, --outdated, --format=json]
  parse_outdated_json()   -> {name: (current, latest)} filtered to PACKAGES
  build_update_command()  -> [python, -m, pip, install, --upgrade, ...]

Runner / threading lives in app.py; this file stays pure + testable.
"""
from __future__ import annotations

import json
from typing import Dict, List, Tuple

PACKAGES: List[str] = ["yt-dlp", "spotdl", "spotapi", "spotipyfree"]


def build_check_command(python_exe: str) -> List[str]:
    return [python_exe, "-m", "pip", "list", "--outdated", "--format=json", "--disable-pip-version-check"]


def parse_outdated_json(payload: str, wanted: List[str] | None = None) -> Dict[str, Tuple[str, str]]:
    """Parse `pip list --outdated --format=json` output, filtered to wanted pkgs."""
    targets = {p.lower() for p in (wanted or PACKAGES)}
    try:
        items = json.loads(payload or "[]")
    except Exception:
        return {}
    out: Dict[str, Tuple[str, str]] = {}
    if not isinstance(items, list):
        return {}
    for it in items:
        try:
            name = str(it.get("name", ""))
            if name.lower() in targets:
                out[name] = (str(it.get("version", "?")), str(it.get("latest_version", "?")))
        except Exception:
            continue
    return out


def build_update_command(python_exe: str, packages: List[str] | None = None) -> List[str]:
    pkgs = packages or PACKAGES
    return [python_exe, "-m", "pip", "install", "--upgrade", *pkgs]
