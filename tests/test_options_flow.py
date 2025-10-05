"""Options flow tests for Energy Advisor."""

from __future__ import annotations

from datetime import time

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_advisor.config import build_entry_data
from custom_components.energy_advisor.config_flow import (
    FIELD_OPERATION,
    OPERATION_ADD,
    OPERATION_FINISH,
    OPERATION_GLOBAL,
    EnergyAdvisorOptionsFlowHandler,
)
from custom_components.energy_advisor.const import (
    CONF_PRICE_SENSOR,
    CONF_SLOT_MINUTES,
    CONF_TIMEZONE,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DOMAIN,
)
from custom_components.energy_advisor.manager import async_create_runtime_data, get_coordinator, set_coordinator
from custom_components.energy_advisor.models import EnergyAdvisorConfig


class DummyCoordinator:
    """Simple coordinator stub capturing refreshes."""

    def __init__(self) -> None:
        self.activity_updates: list | None = None
        self.refresh_requested = False

    def async_request_refresh(self) -> None:
        self.refresh_requested = True

    def update_activities(self, activities) -> None:
        self.activity_updates = activities
        self.async_request_refresh()


@pytest.fixture
async def runtime(hass):
    hass.data.setdefault(DOMAIN, {})
    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=60,
        window_start=time(6, 0),
        window_end=time(22, 0),
        timezone="Europe/Stockholm",
    )
    entry = MockConfigEntry(domain=DOMAIN, data=build_entry_data(config))
    entry.add_to_hass(hass)

    runtime = await async_create_runtime_data(hass, entry)
    coordinator = DummyCoordinator()
    set_coordinator(runtime, coordinator)
    hass.data[DOMAIN][entry.entry_id] = runtime

    return entry, runtime, coordinator


async def test_options_flow_add_activity(hass, runtime) -> None:
    entry, runtime_data, coordinator = runtime
    flow = EnergyAdvisorOptionsFlowHandler(entry)
    flow.hass = hass

    await flow.async_step_init(user_input={FIELD_OPERATION: OPERATION_ADD})
    await flow.async_step_add_activity(
        user_input={
            "name": "Washing",
            "duration_minutes": 90,
            "earliest_start": "07:00",
            "latest_end": "21:00",
            "priority": 1,
        }
    )

    assert runtime_data.activities
    assert coordinator.activity_updates is not None
    assert coordinator.refresh_requested is True


async def test_options_flow_update_global_settings(hass, runtime) -> None:
    entry, runtime_data, coordinator = runtime
    flow = EnergyAdvisorOptionsFlowHandler(entry)
    flow.hass = hass

    await flow.async_step_init(user_input={FIELD_OPERATION: OPERATION_GLOBAL})
    await flow.async_step_global(
        user_input={
            CONF_SLOT_MINUTES: 30,
            CONF_WINDOW_START: "05:00",
            CONF_WINDOW_END: "23:00",
            CONF_TIMEZONE: "Europe/Stockholm",
        }
    )

    assert runtime_data.config.slot_minutes == 30
    assert coordinator.refresh_requested is True


async def test_options_flow_finish_returns_entry(hass, runtime) -> None:
    entry, runtime_data, coordinator = runtime
    flow = EnergyAdvisorOptionsFlowHandler(entry)
    flow.hass = hass

    result = await flow.async_step_init(user_input={FIELD_OPERATION: OPERATION_FINISH})
    assert result["type"] == "create_entry"
