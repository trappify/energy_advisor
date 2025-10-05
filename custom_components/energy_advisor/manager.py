"""Runtime manager for Energy Advisor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .config import config_entry_to_model
from .const import DATA_COORDINATOR
from .models import ActivityDefinition, EnergyAdvisorConfig
from .storage import EnergyAdvisorStorage, EnergyAdvisorStorageState


@dataclass
class EnergyAdvisorRuntimeData:
    """Runtime container stored in hass.data."""

    config: EnergyAdvisorConfig
    storage: EnergyAdvisorStorage
    activities: list[ActivityDefinition]
    extra: dict[str, Any]


async def async_create_runtime_data(hass: HomeAssistant, entry: ConfigEntry) -> EnergyAdvisorRuntimeData:
    """Initialise runtime data for a config entry."""
    config = config_entry_to_model(entry)
    storage = EnergyAdvisorStorage.create(hass, entry.entry_id)
    state = await storage.async_load()
    activities = state.to_definitions()
    return EnergyAdvisorRuntimeData(config=config, storage=storage, activities=activities, extra={})


async def async_save_activities(
    runtime: EnergyAdvisorRuntimeData,
    activities: list[ActivityDefinition],
) -> None:
    """Persist activities via storage helper and update runtime state."""
    runtime.activities = activities
    state = EnergyAdvisorStorageState.from_definitions(activities)
    await runtime.storage.async_save(state)


def get_coordinator(runtime: EnergyAdvisorRuntimeData):
    """Convenience accessor for the coordinator stored in runtime.extra."""
    return runtime.extra.get(DATA_COORDINATOR)


def set_coordinator(runtime: EnergyAdvisorRuntimeData, coordinator) -> None:
    """Attach coordinator reference to runtime data."""
    runtime.extra[DATA_COORDINATOR] = coordinator
