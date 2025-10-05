"""Utility helpers for Energy Advisor."""

from __future__ import annotations

from datetime import time


def time_to_str(value: time) -> str:
    """Render a time object as HH:MM string."""
    return value.strftime("%H:%M")


def str_to_time(value: str) -> time:
    """Parse HH:MM formatted string into a time object."""
    parts = value.split(":")
    if len(parts) < 2:
        raise ValueError("Invalid time format; expected HH:MM")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour=hour, minute=minute, second=second)
