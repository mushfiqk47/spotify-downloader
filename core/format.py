"""Module: pure formatting helpers.

Deep Module: two pure functions, zero dependencies, zero side effects.
Interface is the test surface: `format_bytes(int)`, `format_speed(float)`.
"""
from __future__ import annotations


def format_bytes(n: int) -> str:
    if n <= 0:
        return "0 B"
    for unit, divisor in (("GB", 1073741824), ("MB", 1048576), ("KB", 1024)):
        if n >= divisor:
            return f"{n / divisor:.1f} {unit}"
    return f"{n} B"


def format_speed(n: float) -> str:
    if n <= 0:
        return "--"
    for unit, divisor in (("MB/s", 1048576), ("KB/s", 1024)):
        if n >= divisor:
            return f"{n / divisor:.1f} {unit}"
    return f"{n:.0f} B/s"
