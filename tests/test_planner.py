"""Tests for the Energy Advisor planner."""

from __future__ import annotations

from datetime import datetime, time, timezone, timedelta
from decimal import Decimal

import pytest

from custom_components.energy_advisor.models import ActivityDefinition, EnergyAdvisorConfig, PricePoint
from custom_components.energy_advisor.planner import PlannerInputs, PlanningError, generate_plan


def _price_point(start_hour: int, start_minute: int, price: float) -> PricePoint:
    start = datetime(2025, 1, 1, start_hour, start_minute, tzinfo=timezone.utc)
    end = start + timedelta(minutes=15)
    return PricePoint(start=start, end=end, price=Decimal(str(price)), currency="SEK")


def test_generate_plan_selects_lowest_cost_slot() -> None:
    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=15,
        window_start=time(0, 0),
        window_end=time(23, 59),
        timezone="UTC",
    )
    prices = [
        _price_point(0, 0, 0.40),
        _price_point(0, 15, 0.10),
        _price_point(0, 30, 0.20),
        _price_point(0, 45, 0.50),
    ]
    activities = [ActivityDefinition(id="wash", name="Washing", duration_minutes=30)]

    plan = generate_plan(PlannerInputs(config=config, activities=activities, prices=prices))

    assert plan.activities[0].start.minute == 15
    assert plan.activities[0].end.minute == 45
    assert plan.activities[0].cost == Decimal("0.075")
    assert plan.unscheduled_activity_ids == []


def test_generate_plan_aggregates_prices() -> None:
    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=30,
        window_start=time(0, 0),
        window_end=time(23, 59),
        timezone="UTC",
    )
    prices = [
        _price_point(0, 0, 0.20),
        _price_point(0, 15, 0.20),
        _price_point(0, 30, 0.80),
        _price_point(0, 45, 0.80),
    ]
    activities = [ActivityDefinition(id="dryer", name="Dryer", duration_minutes=30)]

    plan = generate_plan(PlannerInputs(config=config, activities=activities, prices=prices))

    # The activity should begin at midnight because the first aggregated block is cheaper.
    assert plan.activities[0].start.minute == 0
    assert plan.activities[0].end.minute == 30
    assert plan.activities[0].cost == Decimal("0.10")


def test_generate_plan_rejects_invalid_slot_multiple() -> None:
    config = EnergyAdvisorConfig(
        price_sensor="sensor.nordpool",
        slot_minutes=20,
        window_start=time(0, 0),
        window_end=time(23, 59),
        timezone="UTC",
    )
    prices = [_price_point(0, 0, 0.20)]

    with pytest.raises(PlanningError):
        generate_plan(PlannerInputs(config=config, activities=[], prices=prices))
