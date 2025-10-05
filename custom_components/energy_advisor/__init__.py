"""Energy Advisor integration bootstrap."""

from __future__ import annotations

from typing import Any, Iterator

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ENTRY_ID,
    ATTR_PLAN_ACTIVITIES,
    ATTR_PLAN_AVERAGE_PRICE,
    ATTR_PLAN_GENERATED_AT,
    ATTR_PLAN_HORIZON_END,
    ATTR_PLAN_HORIZON_START,
    ATTR_PLAN_TOTAL_COST,
    ATTR_PLAN_UNSCHEDULED,
    DOMAIN,
    PLATFORMS,
    SERVICE_EXPORT_PLAN,
    SERVICE_RECOMPUTE,
)
from .coordinator import EnergyAdvisorCoordinator
from .manager import (
    EnergyAdvisorRuntimeData,
    async_create_runtime_data,
    get_coordinator,
    set_coordinator,
)
from .models import ScheduleSolution

ConfigEntryType = ConfigEntry


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Energy Advisor integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntryType) -> bool:
    """Set up Energy Advisor from a config entry."""
    runtime = await async_create_runtime_data(hass, entry)

    coordinator = EnergyAdvisorCoordinator(hass, entry, runtime)
    set_coordinator(runtime, coordinator)

    hass.data[DOMAIN][entry.entry_id] = runtime

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise ConfigEntryNotReady(str(exc)) from exc

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntryType) -> bool:
    """Unload an Energy Advisor config entry."""
    runtime: EnergyAdvisorRuntimeData | None = hass.data[DOMAIN].get(entry.entry_id)
    if runtime is None:
        return False

    coordinator: EnergyAdvisorCoordinator | None = get_coordinator(runtime)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        if coordinator is not None:
            await coordinator.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        _async_unregister_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntryType) -> None:
    """Reload entry when config data changes."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration level services once."""
    if hass.services.has_service(DOMAIN, SERVICE_RECOMPUTE):
        return

    async def handle_recompute(call: ServiceCall) -> None:
        await _handle_recompute(hass, call)

    async def handle_export(call: ServiceCall) -> dict[str, Any]:
        return await _handle_export(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECOMPUTE,
        handle_recompute,
        schema=vol.Schema({vol.Optional(ATTR_ENTRY_ID): str}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_PLAN,
        handle_export,
        schema=vol.Schema({vol.Optional(ATTR_ENTRY_ID): str}),
        supports_response=True,
    )


def _async_unregister_services(hass: HomeAssistant) -> None:
    """Remove services when no entries remain."""
    if hass.services.has_service(DOMAIN, SERVICE_RECOMPUTE):
        hass.services.async_remove(DOMAIN, SERVICE_RECOMPUTE)
    if hass.services.has_service(DOMAIN, SERVICE_EXPORT_PLAN):
        hass.services.async_remove(DOMAIN, SERVICE_EXPORT_PLAN)


async def _handle_recompute(hass: HomeAssistant, call: ServiceCall) -> None:
    """Trigger a recompute of planning data."""
    for runtime in _iter_target_runtimes(hass, call.data):
        coordinator: EnergyAdvisorCoordinator | None = get_coordinator(runtime)
        if coordinator is not None:
            await coordinator.async_request_refresh()


async def _handle_export(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Return the latest plan as a service response."""
    runtime = next(_iter_target_runtimes(hass, call.data), None)
    if runtime is None:
        return {}

    coordinator: EnergyAdvisorCoordinator | None = get_coordinator(runtime)
    if coordinator is None or coordinator.data is None:
        return {}

    return _plan_to_dict(coordinator.data)


def _iter_target_runtimes(hass: HomeAssistant, data: dict[str, Any]) -> Iterator[EnergyAdvisorRuntimeData]:
    entry_id = data.get(ATTR_ENTRY_ID)
    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        runtime = entries.get(entry_id)
        if runtime:
            yield runtime
        return
    yield from entries.values()


def _plan_to_dict(plan: ScheduleSolution) -> dict[str, Any]:
    """Convert plan data into a serialisable response."""
    return {
        ATTR_PLAN_GENERATED_AT: plan.generated_at.isoformat(),
        ATTR_PLAN_HORIZON_START: plan.horizon_start.isoformat(),
        ATTR_PLAN_HORIZON_END: plan.horizon_end.isoformat(),
        ATTR_PLAN_TOTAL_COST: str(plan.total_cost),
        ATTR_PLAN_AVERAGE_PRICE: str(plan.average_price),
        ATTR_PLAN_UNSCHEDULED: plan.unscheduled_activity_ids,
        ATTR_PLAN_ACTIVITIES: [
            {
                "activity_id": activity.activity_id,
                "start": activity.start.isoformat(),
                "end": activity.end.isoformat(),
                "cost": str(activity.cost),
                "slots": [
                    {
                        "start": slot.start.isoformat(),
                        "end": slot.end.isoformat(),
                        "price": str(slot.price),
                        "currency": slot.currency,
                    }
                    for slot in activity.slot_prices
                ],
            }
            for activity in plan.activities
        ],
    }
