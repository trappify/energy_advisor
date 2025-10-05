"""Constants for the Energy Advisor integration."""

from __future__ import annotations

from datetime import time
import logging
from typing import Final

from homeassistant.const import Platform

LOGGER = logging.getLogger(__package__)

DOMAIN: Final = "energy_advisor"
PLATFORMS: Final[list[Platform]] = [Platform.SENSOR]

DATA_COORDINATOR: Final = "coordinator"
DATA_MANAGER: Final = "manager"

CONF_PRICE_SENSOR: Final = "price_sensor"
CONF_SLOT_MINUTES: Final = "slot_minutes"
CONF_WINDOW_START: Final = "window_start"
CONF_WINDOW_END: Final = "window_end"
CONF_TIMEZONE: Final = "timezone"

DEFAULT_SLOT_MINUTES: Final = 60
DEFAULT_WINDOW_START: Final = time(hour=0, minute=0)
DEFAULT_WINDOW_END: Final = time(hour=23, minute=59)
DEFAULT_TIMEZONE: Final | None = None

SERVICE_RECOMPUTE: Final = "recompute_plan"
SERVICE_EXPORT_PLAN: Final = "export_plan"

STORAGE_KEY_ACTIVITIES: Final = "activities"
STORAGE_VERSION: Final = 1

ATTR_PLAN_ACTIVITIES: Final = "activities"
ATTR_PLAN_GENERATED_AT: Final = "generated_at"
ATTR_PLAN_TOTAL_COST: Final = "total_cost"
ATTR_PLAN_AVERAGE_PRICE: Final = "average_price"
ATTR_PLAN_HORIZON_START: Final = "horizon_start"
ATTR_PLAN_HORIZON_END: Final = "horizon_end"
ATTR_PLAN_UNSCHEDULED: Final = "unscheduled"

ATTR_ENTRY_ID: Final = "entry_id"
