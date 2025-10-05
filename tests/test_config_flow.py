"""Config flow tests for Energy Advisor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.energy_advisor.config_flow import EnergyAdvisorConfigFlow
from custom_components.energy_advisor.const import (
    CONF_PRICE_SENSOR,
    CONF_SLOT_MINUTES,
    CONF_TIMEZONE,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DOMAIN,
)


async def test_config_flow_happy_path(hass) -> None:
    now = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    hass.states.async_set(
        "sensor.nordpool",
        "0.10",
        {
            "raw_today": [
                {
                    "start": now.isoformat(),
                    "end": (now + timedelta(minutes=15)).isoformat(),
                    "value": 0.10,
                }
            ],
        },
    )

    flow = EnergyAdvisorConfigFlow()
    flow.hass = hass
    flow.context = {}

    result = await flow.async_step_user(user_input=None)
    assert result["type"] == "form"

    user_input = {
        CONF_PRICE_SENSOR: "sensor.nordpool",
        CONF_SLOT_MINUTES: 60,
        CONF_WINDOW_START: "06:00",
        CONF_WINDOW_END: "22:00",
        CONF_TIMEZONE: "Europe/Stockholm",
    }

    result2 = await flow.async_step_user(user_input=user_input)
    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_PRICE_SENSOR] == "sensor.nordpool"
    assert result2["data"][CONF_SLOT_MINUTES] == 60


async def test_config_flow_errors_without_sensor(hass) -> None:
    flow = EnergyAdvisorConfigFlow()
    flow.hass = hass
    flow.context = {}

    result = await flow.async_step_user(user_input=None)
    assert result["errors"]["base"] == "no_sensors"
