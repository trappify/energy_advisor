"""Data models used by the Energy Advisor integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class EnergyAdvisorConfig:
    """Configuration collected from the config entry."""

    price_sensor: str
    slot_minutes: int
    window_start: time
    window_end: time
    timezone: str | None = None


@dataclass(slots=True)
class ActivityDefinition:
    """Activity that requires scheduling."""

    id: str
    name: str
    duration_minutes: int
    earliest_start: time | None = None
    latest_end: time | None = None
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PricePoint:
    """Energy price for a discrete time slot."""

    start: datetime
    end: datetime
    price: Decimal
    currency: str

    def duration_minutes(self) -> int:
        """Return the duration of this price point in whole minutes."""
        seconds = int((self.end - self.start).total_seconds())
        return max(seconds // 60, 1)


@dataclass(slots=True)
class ScheduledActivity:
    """Activity placement proposal."""

    activity_id: str
    start: datetime
    end: datetime
    slot_prices: list[PricePoint]
    cost: Decimal


@dataclass(slots=True)
class ScheduleSolution:
    """Planner output for a planning horizon."""

    generated_at: datetime
    horizon_start: datetime
    horizon_end: datetime
    activities: list[ScheduledActivity]
    total_cost: Decimal
    average_price: Decimal
    unscheduled_activity_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StoredActivity:
    """Persisted representation of an activity."""

    id: str
    name: str
    duration_minutes: int
    earliest_start: str | None
    latest_end: str | None
    priority: int
    metadata: dict[str, Any]

    @classmethod
    def from_definition(cls, definition: ActivityDefinition) -> "StoredActivity":
        """Create a stored activity from a runtime definition."""
        return cls(
            id=definition.id,
            name=definition.name,
            duration_minutes=definition.duration_minutes,
            earliest_start=definition.earliest_start.isoformat() if definition.earliest_start else None,
            latest_end=definition.latest_end.isoformat() if definition.latest_end else None,
            priority=definition.priority,
            metadata=definition.metadata,
        )

    def to_definition(self) -> ActivityDefinition:
        """Convert to a runtime definition."""
        return ActivityDefinition(
            id=self.id,
            name=self.name,
            duration_minutes=self.duration_minutes,
            earliest_start=time_from_iso(self.earliest_start),
            latest_end=time_from_iso(self.latest_end),
            priority=self.priority,
            metadata=self.metadata,
        )


def time_from_iso(value: str | None) -> time | None:
    """Parse an ISO formatted time string (HH:MM[:SS])."""
    if value is None:
        return None
    try:
        parts = value.split(":")
    except AttributeError as exc:  # pragma: no cover - defensive guard
        raise ValueError("Invalid time value") from exc

    if len(parts) not in (2, 3):
        raise ValueError("Invalid time format")

    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    return time(hour=hour, minute=minute, second=second)
