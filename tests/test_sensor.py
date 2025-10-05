"""Tests for Energy Advisor sensor entity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_advisor.const import DOMAIN
from custom_components.energy_advisor.sensor import EnergyAdvisorPlanSensor
from custom_components.energy_advisor.models import (
    PricePoint,
    ScheduleSolution,
    ScheduledActivity,
)


class DummyCoordinator:
    def __init__(self, hass, data):
        self.hass = hass
        self.data = data
        self._activity_names = {"wash": "Washer"}

    def async_add_listener(self, update_callback):
        return lambda: None

    def async_request_refresh(self):
        return None

    def get_activity_name(self, activity_id: str):
        return self._activity_names.get(activity_id)


async def test_plan_sensor_exposes_attributes(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    plan = ScheduleSolution(
        generated_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        horizon_start=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        horizon_end=datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc),
        activities=[
            ScheduledActivity(
                activity_id="wash",
                start=datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc),
                end=datetime(2025, 1, 1, 0, 45, tzinfo=timezone.utc),
                slot_prices=[
                    PricePoint(
                        start=datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc),
                        end=datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc),
                        price=Decimal("0.10"),
                        currency="SEK",
                    )
                ],
                cost=Decimal("0.025"),
            )
        ],
        total_cost=Decimal("0.025"),
        average_price=Decimal("0.05"),
        unscheduled_activity_ids=[],
    )

    coordinator = DummyCoordinator(hass, plan)

    sensor = EnergyAdvisorPlanSensor(coordinator, entry)
    sensor.hass = hass

    attributes = sensor.extra_state_attributes
    assert attributes["activities"][0]["activity_id"] == "wash"
    assert attributes["activities"][0]["name"] == "Washer"
    assert attributes["total_cost"] == str(plan.total_cost)
