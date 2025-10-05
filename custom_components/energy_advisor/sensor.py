"""Sensor platform for Energy Advisor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_PLAN_ACTIVITIES,
    ATTR_PLAN_AVERAGE_PRICE,
    ATTR_PLAN_GENERATED_AT,
    ATTR_PLAN_HORIZON_END,
    ATTR_PLAN_HORIZON_START,
    ATTR_PLAN_TOTAL_COST,
    ATTR_PLAN_UNSCHEDULED,
    DOMAIN,
)
from .coordinator import EnergyAdvisorCoordinator
from .manager import EnergyAdvisorRuntimeData, get_coordinator
from .models import ScheduleSolution

ENTITY_NAME = "Energy Advisor Plan"
ENTITY_ICON = "mdi:calendar-clock"
ATTR_ATTRIBUTION_TEXT = "Energy Advisor planned schedule"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Energy Advisor sensor entities."""
    runtime: EnergyAdvisorRuntimeData = hass.data[DOMAIN][entry.entry_id]
    coordinator: EnergyAdvisorCoordinator = get_coordinator(runtime)
    async_add_entities([EnergyAdvisorPlanSensor(coordinator, entry)])


class EnergyAdvisorPlanSensor(CoordinatorEntity[EnergyAdvisorCoordinator], SensorEntity):
    """Sensor exposing the computed plan."""

    _attr_has_entity_name = True
    _attr_name = ENTITY_NAME
    _attr_icon = ENTITY_ICON

    def __init__(self, coordinator: EnergyAdvisorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_plan"

    @property
    def native_value(self) -> str | None:
        plan: ScheduleSolution | None = self.coordinator.data
        if plan is None:
            return None
        return plan.generated_at.isoformat()

    @property
    def extra_state_attributes(self) -> dict:
        plan: ScheduleSolution | None = self.coordinator.data
        if plan is None:
            return {}
        return {
            ATTR_ATTRIBUTION: ATTR_ATTRIBUTION_TEXT,
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
                    "prices": [
                        {
                            "start": price.start.isoformat(),
                            "end": price.end.isoformat(),
                            "price": str(price.price),
                            "currency": price.currency,
                        }
                        for price in activity.slot_prices
                    ],
                }
                for activity in plan.activities
            ],
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Energy Advisor",
            configuration_url="/config/integrations/integration/energy_advisor",
        )
