"""Basic tests for the Energy Advisor integration bootstrap."""

from datetime import datetime, timedelta, timezone

from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import AsyncMock

from custom_components.energy_advisor import async_setup, async_setup_entry, async_unload_entry
from custom_components.energy_advisor.config import build_entry_data
from custom_components.energy_advisor.const import DOMAIN
from custom_components.energy_advisor.manager import get_coordinator
from custom_components.energy_advisor.models import EnergyAdvisorConfig


async def test_async_setup(hass) -> None:
    """Verify the domain is initialised during setup."""
    assert await async_setup(hass, {})
    assert DOMAIN in hass.data


async def test_async_setup_and_unload_entry(hass) -> None:
    """Config entry lifecycle should maintain hass data structures."""
    await async_setup(hass, {})

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

    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=15,
        window_start=now.time(),
        window_end=now.replace(hour=23, minute=59).time(),
        timezone="UTC",
    )
    entry = MockConfigEntry(domain=DOMAIN, data=build_entry_data(config))

    assert await async_setup_entry(hass, entry)
    runtime = hass.data[DOMAIN][entry.entry_id]
    assert runtime.config.price_sensor == "sensor.nordpool"
    assert get_coordinator(runtime) is not None

    assert await async_unload_entry(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]
