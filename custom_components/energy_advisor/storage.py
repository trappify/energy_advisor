"""Persistence helpers for Energy Advisor."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_KEY_ACTIVITIES, STORAGE_VERSION
from .models import ActivityDefinition, StoredActivity


@dataclass(slots=True)
class EnergyAdvisorStorageState:
    """Serializable storage payload."""

    version: int = STORAGE_VERSION
    activities: list[StoredActivity] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnergyAdvisorStorageState":
        """Create storage state from raw dict."""
        stored = [
            StoredActivity(**activity) for activity in data.get(STORAGE_KEY_ACTIVITIES, [])
        ]
        return cls(version=data.get("version", STORAGE_VERSION), activities=stored)

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "version": self.version,
            STORAGE_KEY_ACTIVITIES: [asdict(activity) for activity in self.activities],
        }

    def to_definitions(self) -> list[ActivityDefinition]:
        """Convert stored activities to runtime definitions."""
        return [activity.to_definition() for activity in self.activities]

    @classmethod
    def from_definitions(cls, activities: Iterable[ActivityDefinition]) -> "EnergyAdvisorStorageState":
        """Create storage state from runtime definitions."""
        return cls(
            activities=[StoredActivity.from_definition(activity) for activity in activities]
        )


class EnergyAdvisorStorage:
    """HA store wrapper for Energy Advisor activities."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def async_load(self) -> EnergyAdvisorStorageState:
        """Load persisted state from disk."""
        data: dict[str, Any] | None = await self._store.async_load()
        if not data:
            return EnergyAdvisorStorageState()
        return EnergyAdvisorStorageState.from_dict(data)

    async def async_save(self, state: EnergyAdvisorStorageState) -> None:
        """Persist the provided state."""
        await self._store.async_save(state.as_dict())

    @classmethod
    def create(cls, hass, entry_id: str) -> "EnergyAdvisorStorage":  # type: ignore[override]
        """Factory helper to create a Store instance bound to the config entry."""
        store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry_id}", private=True)
        return cls(store)
