"""Tests for the Energy Advisor coordinator."""

from __future__ import annotations

from datetime import datetime, time, timezone

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_advisor.config import build_entry_data
from custom_components.energy_advisor.const import DOMAIN
from custom_components.energy_advisor.coordinator import EnergyAdvisorCoordinator
from custom_components.energy_advisor.manager import async_create_runtime_data, set_coordinator
from custom_components.energy_advisor.models import ActivityDefinition, EnergyAdvisorConfig


async def test_coordinator_generates_plan(hass) -> None:
    hass.states.async_set(
        "sensor.nordpool",
        "0.10",
        {
            "currency": "SEK",
            "raw_today": [
                {
                    "start": datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
                    "end": datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc).isoformat(),
                    "value": 0.10,
                },
                {
                    "start": datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc).isoformat(),
                    "end": datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc).isoformat(),
                    "value": 0.15,
                },
                {
                    "start": datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc).isoformat(),
                    "end": datetime(2025, 1, 1, 0, 45, tzinfo=timezone.utc).isoformat(),
                    "value": 0.20,
                },
                {
                    "start": datetime(2025, 1, 1, 0, 45, tzinfo=timezone.utc).isoformat(),
                    "end": datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc).isoformat(),
                    "value": 0.25,
                },
            ],
        },
    )

    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=15,
        window_start=time(0, 0),
        window_end=time(23, 59),
        timezone="UTC",
    )

    entry = MockConfigEntry(domain=DOMAIN, data=build_entry_data(config))
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    runtime = await async_create_runtime_data(hass, entry)
    runtime.activities = [ActivityDefinition(id="wash", name="Washing", duration_minutes=30)]

    coordinator = EnergyAdvisorCoordinator(hass, entry, runtime)
    set_coordinator(runtime, coordinator)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.activities
    assert coordinator.data.activities[0].activity_id == "wash"


async def test_async_update_activities_refreshes_plan(hass) -> None:
    hass.states.async_set(
        "sensor.nordpool",
        "0.10",
        {
            "currency": "SEK",
            "raw_today": [
                {
                    "start": datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
                    "end": datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc).isoformat(),
                    "value": 0.10,
                },
                {
                    "start": datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc).isoformat(),
                    "end": datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc).isoformat(),
                    "value": 0.15,
                },
            ],
        },
    )

    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=15,
        window_start=time(0, 0),
        window_end=time(23, 59),
        timezone="UTC",
    )

    entry = MockConfigEntry(domain=DOMAIN, data=build_entry_data(config))
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    runtime = await async_create_runtime_data(hass, entry)

    coordinator = EnergyAdvisorCoordinator(hass, entry, runtime)
    set_coordinator(runtime, coordinator)

    await coordinator.async_config_entry_first_refresh()
    assert coordinator.data is not None
    assert coordinator.data.activities == []

    await coordinator.async_update_activities(
        [ActivityDefinition(id="wash", name="Washing", duration_minutes=30)]
    )

    assert coordinator.data is not None
    assert coordinator.data.activities
    assert coordinator.data.activities[0].activity_id == "wash"
