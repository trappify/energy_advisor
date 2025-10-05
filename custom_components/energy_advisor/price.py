"""Helpers for working with price sensor data."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .models import PricePoint

RAW_PRICE_KEYS = ("raw_today", "raw_tomorrow")


class PriceExtractionError(HomeAssistantError):
    """Raised when price data cannot be extracted."""


def extract_price_points(hass: HomeAssistant, entity_id: str) -> list[PricePoint]:
    """Parse raw price data from a sensor entity."""
    state = hass.states.get(entity_id)
    if state is None:
        raise PriceExtractionError(f"Sensor {entity_id} is unavailable")

    raw = _collect_raw_entries(state)
    if not raw:
        raise PriceExtractionError("Price sensor does not expose raw price data")

    currency = state.attributes.get("currency") or state.attributes.get("unit_of_measurement", "")

    points: list[PricePoint] = []
    for entry in raw:
        start_raw = entry["start"]
        end_raw = entry["end"]
        start = start_raw if isinstance(start_raw, datetime) else dt_util.parse_datetime(start_raw)
        end = end_raw if isinstance(end_raw, datetime) else dt_util.parse_datetime(end_raw)
        if start is None or end is None:
            continue
        price = Decimal(str(entry["value"]))
        points.append(PricePoint(start=start, end=end, price=price, currency=currency))

    if not points:
        raise PriceExtractionError("No valid entries extracted from price sensor")

    points.sort(key=lambda item: item.start)
    return points


def _collect_raw_entries(state: State) -> list[dict[str, str]]:
    raw_entries: list[dict[str, str]] = []
    for key in RAW_PRICE_KEYS:
        raw_value = state.attributes.get(key) or []
        raw_entries.extend(_normalize_entries(raw_value))
    return raw_entries


def _normalize_entries(raw_value: Iterable) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if isinstance(raw_value, list):
        for item in raw_value:
            if not isinstance(item, dict):
                continue
            if {"start", "end", "value"}.issubset(item):
                entries.append(item)
    return entries
