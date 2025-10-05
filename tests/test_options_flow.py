"""Options flow tests for Energy Advisor."""

from __future__ import annotations

from datetime import time

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_advisor.config import build_entry_data
from custom_components.energy_advisor.config_flow import (
    FIELD_ACTIVITY_ID,
    FIELD_DURATION,
    FIELD_EARLIEST,
    FIELD_LATEST,
    FIELD_NAME,
    FIELD_OPERATION,
    FIELD_PRIORITY,
    OPERATION_ADD,
    OPERATION_EDIT,
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
from custom_components.energy_advisor.coordinator import EnergyAdvisorCoordinator
from custom_components.energy_advisor.manager import (
    async_create_runtime_data,
    async_save_activities,
    get_coordinator,
    set_coordinator,
)
from custom_components.energy_advisor.models import ActivityDefinition, EnergyAdvisorConfig


class DummyCoordinator:
    """Simple coordinator stub capturing refreshes."""

    def __init__(self) -> None:
        self.activity_updates: list | None = None
        self.refresh_count = 0

    async def async_refresh(self) -> None:
        self.refresh_count += 1

    async def async_update_activities(self, activities) -> None:
        self.activity_updates = activities
        await self.async_refresh()


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
    assert coordinator.refresh_count >= 1


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
    assert coordinator.refresh_count >= 1


async def test_options_flow_finish_returns_entry(hass, runtime) -> None:
    entry, runtime_data, coordinator = runtime
    flow = EnergyAdvisorOptionsFlowHandler(entry)
    flow.hass = hass

    result = await flow.async_step_init(user_input={FIELD_OPERATION: OPERATION_FINISH})
    assert result["type"] == "create_entry"


async def test_options_flow_edit_activity_with_real_coordinator(hass) -> None:
    now = time(0, 0)
    hass.states.async_set(
        "sensor.nordpool",
        "0.10",
        {
            "currency": "SEK",
            "raw_today": [
                {
                    "start": "2025-01-01T00:00:00+00:00",
                    "end": "2025-01-01T00:15:00+00:00",
                    "value": 0.10,
                },
                {
                    "start": "2025-01-01T00:15:00+00:00",
                    "end": "2025-01-01T00:30:00+00:00",
                    "value": 0.12,
                },
                {
                    "start": "2025-01-01T00:30:00+00:00",
                    "end": "2025-01-01T00:45:00+00:00",
                    "value": 0.14,
                },
                {
                    "start": "2025-01-01T00:45:00+00:00",
                    "end": "2025-01-01T01:00:00+00:00",
                    "value": 0.16,
                },
                {
                    "start": "2025-01-01T01:00:00+00:00",
                    "end": "2025-01-01T01:15:00+00:00",
                    "value": 0.18,
                },
                {
                    "start": "2025-01-01T01:15:00+00:00",
                    "end": "2025-01-01T01:30:00+00:00",
                    "value": 0.11,
                },
                {
                    "start": "2025-01-01T01:30:00+00:00",
                    "end": "2025-01-01T01:45:00+00:00",
                    "value": 0.09,
                },
            ],
        },
    )

    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=15,
        window_start=now,
        window_end=time(23, 59),
        timezone="UTC",
    )

    entry = MockConfigEntry(domain=DOMAIN, data=build_entry_data(config))
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    runtime = await async_create_runtime_data(hass, entry)

    activity = ActivityDefinition(
        id="wash",
        name="Washing",
        duration_minutes=30,
        earliest_start=time(1, 0),
        latest_end=time(6, 0),
        priority=1,
    )
    await async_save_activities(runtime, [activity])

    coordinator = EnergyAdvisorCoordinator(hass, entry, runtime)
    set_coordinator(runtime, coordinator)
    hass.data[DOMAIN][entry.entry_id] = runtime

    await coordinator.async_config_entry_first_refresh()

    flow = EnergyAdvisorOptionsFlowHandler(entry)
    flow.hass = hass

    await flow.async_step_init(user_input={FIELD_OPERATION: OPERATION_EDIT})
    selection = await flow.async_step_edit_activity(user_input=None)
    assert selection["type"] == "form"
    assert selection["step_id"] == "edit_activity_select"

    await flow.async_step_edit_activity_select(user_input={FIELD_ACTIVITY_ID: activity.id})
    await flow.async_step_edit_activity(
        user_input={
            FIELD_NAME: "Washer",
            FIELD_DURATION: 45,
            FIELD_EARLIEST: "01:00",
            FIELD_LATEST: "02:00",
            FIELD_PRIORITY: 0,
        }
    )

    assert runtime.activities[0].name == "Washer"
    assert coordinator.data is not None
    assert any(act.activity_id == "wash" for act in coordinator.data.activities)


async def test_options_flow_edit_select_step(hass, runtime) -> None:
    entry, runtime_data, coordinator = runtime
    runtime_data.activities = [
        ActivityDefinition(id="wash", name="Washing", duration_minutes=30)
    ]

    flow = EnergyAdvisorOptionsFlowHandler(entry)
    flow.hass = hass

    await flow.async_step_init(user_input={FIELD_OPERATION: OPERATION_EDIT})
    result = await flow.async_step_edit_activity()

    assert result["type"] == "form"
    assert result["step_id"] == "edit_activity_select"
