"""Config entry helpers for Energy Advisor."""

from __future__ import annotations

from datetime import time
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_PRICE_SENSOR,
    CONF_SLOT_MINUTES,
    CONF_TIMEZONE,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_SLOT_MINUTES,
    DEFAULT_TIMEZONE,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
)
from .models import EnergyAdvisorConfig
from .util import str_to_time, time_to_str


def config_entry_to_model(entry: ConfigEntry) -> EnergyAdvisorConfig:
    """Create an EnergyAdvisorConfig from a config entry."""
    data = entry.data or {}
    return EnergyAdvisorConfig(
        price_sensor=data.get(CONF_PRICE_SENSOR, ""),
        slot_minutes=data.get(CONF_SLOT_MINUTES, DEFAULT_SLOT_MINUTES),
        window_start=_read_time(data, CONF_WINDOW_START, DEFAULT_WINDOW_START),
        window_end=_read_time(data, CONF_WINDOW_END, DEFAULT_WINDOW_END),
        timezone=data.get(CONF_TIMEZONE, DEFAULT_TIMEZONE),
    )


def _read_time(data: dict[str, Any], key: str, default: time) -> time:
    value = data.get(key)
    if value is None:
        return default
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        return str_to_time(value)
    raise ValueError(f"Unsupported time format for {key!r}")


def build_entry_data(config: EnergyAdvisorConfig) -> dict[str, Any]:
    """Serialize EnergyAdvisorConfig for storage within config entries."""
    payload: dict[str, Any] = {
        CONF_PRICE_SENSOR: config.price_sensor,
        CONF_SLOT_MINUTES: config.slot_minutes,
        CONF_WINDOW_START: time_to_str(config.window_start),
        CONF_WINDOW_END: time_to_str(config.window_end),
    }
    if config.timezone:
        payload[CONF_TIMEZONE] = config.timezone
    return payload
