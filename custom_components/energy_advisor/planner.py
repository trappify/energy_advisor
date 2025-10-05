"""Scheduling engine for Energy Advisor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
import math
from typing import Iterable

from homeassistant.util import dt as dt_util

from .models import (
    ActivityDefinition,
    EnergyAdvisorConfig,
    PricePoint,
    ScheduleSolution,
    ScheduledActivity,
)


@dataclass(slots=True)
class PlannerInputs:
    """Convenience structure for planner execution."""

    config: EnergyAdvisorConfig
    activities: list[ActivityDefinition]
    prices: list[PricePoint]


class PlanningError(Exception):
    """Raised when planning cannot be performed."""


def generate_plan(inputs: PlannerInputs) -> ScheduleSolution:
    """Produce a schedule based on the provided inputs."""
    if not inputs.prices:
        raise PlanningError("No price data available for planning")

    slot_minutes = _infer_slot_minutes(inputs)
    if slot_minutes <= 0:
        raise PlanningError("Invalid slot resolution")

    sorted_prices = sorted(inputs.prices, key=lambda item: item.start)
    prices = _aggregate_prices(sorted_prices, slot_minutes)
    if not prices:
        raise PlanningError("Unable to aggregate price data for planning")

    horizon_start = prices[0].start
    horizon_end = prices[-1].end

    slots = [
        _PlannerSlot(index=i, price=price, slot_minutes=slot_minutes) for i, price in enumerate(prices)
    ]

    occupancy = [False] * len(slots)
    scheduled: list[ScheduledActivity] = []
    unscheduled: list[str] = []

    activities = sorted(
        inputs.activities,
        key=lambda activity: (activity.priority, -activity.duration_minutes),
    )

    for activity in activities:
        placement = _find_best_slot(activity, slots, occupancy, inputs.config, slot_minutes)
        if placement is None:
            unscheduled.append(activity.id)
            continue
        scheduled_activity, occupied_indices = placement
        scheduled.append(scheduled_activity)
        for idx in occupied_indices:
            occupancy[idx] = True

    total_cost = sum((activity.cost for activity in scheduled), start=Decimal("0"))
    average_price = Decimal("0")
    total_minutes = sum(
        int((activity.end - activity.start).total_seconds() // 60) for activity in scheduled
    )
    if total_minutes:
        average_price = total_cost / (Decimal(total_minutes) / Decimal(60))

    return ScheduleSolution(
        generated_at=dt_util.utcnow(),
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        activities=scheduled,
        total_cost=total_cost,
        average_price=average_price,
        unscheduled_activity_ids=unscheduled,
    )


@dataclass(slots=True)
class _PlannerSlot:
    """Internal representation of a planning slot."""

    index: int
    price: PricePoint
    slot_minutes: int

    @property
    def start(self) -> datetime:
        return self.price.start

    @property
    def end(self) -> datetime:
        return self.price.end

    @property
    def price_value(self) -> Decimal:
        return self.price.price


def _infer_slot_minutes(inputs: PlannerInputs) -> int:
    configured = inputs.config.slot_minutes
    if configured <= 0:
        raise PlanningError("Configured slot minutes must be positive")

    raw_minutes = inputs.prices[0].duration_minutes()
    if raw_minutes <= 0:
        raise PlanningError("Invalid raw price slot duration")

    if configured % raw_minutes != 0:
        raise PlanningError(
            f"Configured slot minutes ({configured}) must be a multiple of raw data resolution ({raw_minutes})."
        )
    return configured


def _aggregate_prices(prices: list[PricePoint], slot_minutes: int) -> list[PricePoint]:
    """Aggregate raw price data to the configured slot duration."""
    raw_minutes = prices[0].duration_minutes()
    if slot_minutes == raw_minutes:
        return prices

    ratio = slot_minutes // raw_minutes
    if ratio <= 0:
        return []

    aggregated: list[PricePoint] = []
    for i in range(0, len(prices), ratio):
        chunk = prices[i : i + ratio]
        if len(chunk) < ratio:
            break
        start = chunk[0].start
        end = chunk[-1].end
        total = sum((point.price for point in chunk), start=Decimal("0"))
        average = total / Decimal(len(chunk))
        aggregated.append(PricePoint(start=start, end=end, price=average, currency=chunk[0].currency))
    return aggregated


def _find_best_slot(
    activity: ActivityDefinition,
    slots: list[_PlannerSlot],
    occupancy: list[bool],
    config: EnergyAdvisorConfig,
    slot_minutes: int,
) -> tuple[ScheduledActivity, list[int]] | None:
    required_minutes = max(activity.duration_minutes, slot_minutes)
    required_slots = math.ceil(required_minutes / slot_minutes)

    best_cost: Decimal | None = None
    best_indices: list[int] | None = None

    for index in range(0, len(slots) - required_slots + 1):
        candidate_slots = slots[index : index + required_slots]
        if any(occupancy[slot.index] for slot in candidate_slots):
            continue

        if not _slots_within_constraints(candidate_slots, activity, config, required_minutes):
            continue

        cost = _calculate_cost(candidate_slots, required_minutes, slot_minutes)
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_indices = [slot.index for slot in candidate_slots]

    if best_cost is None or best_indices is None:
        return None

    selected_slots = [slots[i] for i in best_indices]
    start_dt = selected_slots[0].start
    end_dt = start_dt + timedelta(minutes=required_minutes)
    cost = _calculate_cost(selected_slots, required_minutes, slot_minutes)

    scheduled = ScheduledActivity(
        activity_id=activity.id,
        start=start_dt,
        end=end_dt,
        slot_prices=[slot.price for slot in selected_slots],
        cost=cost,
    )
    return scheduled, best_indices


def _slots_within_constraints(
    candidate_slots: list[_PlannerSlot],
    activity: ActivityDefinition,
    config: EnergyAdvisorConfig,
    required_minutes: int,
) -> bool:
    start_dt = candidate_slots[0].start
    end_dt = start_dt + timedelta(minutes=required_minutes)

    window_start = _combine_with_date(start_dt, activity.earliest_start or config.window_start)
    window_end = _combine_with_date(start_dt, activity.latest_end or config.window_end)

    if start_dt < window_start or end_dt > window_end:
        return False

    return True


def _calculate_cost(
    candidate_slots: Iterable[_PlannerSlot],
    required_minutes: int,
    slot_minutes: int,
) -> Decimal:
    remaining = required_minutes
    total = Decimal("0")
    for slot in candidate_slots:
        portion = min(slot_minutes, remaining)
        total += slot.price_value * (Decimal(portion) / Decimal(60))
        remaining -= portion
        if remaining <= 0:
            break
    return total


def _combine_with_date(reference: datetime, tme: time) -> datetime:
    return reference.replace(hour=tme.hour, minute=tme.minute, second=tme.second, microsecond=0)
