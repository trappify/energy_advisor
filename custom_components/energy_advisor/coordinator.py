"""Coordinator responsible for refreshing Energy Advisor plans."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER
from .manager import EnergyAdvisorRuntimeData
from .models import ActivityDefinition
from .planner import PlannerInputs, PlanningError, generate_plan
from .price import PriceExtractionError, extract_price_points

UPDATE_INTERVAL = timedelta(minutes=30)


class EnergyAdvisorCoordinator(DataUpdateCoordinator):
    """Coordinates price ingestion and schedule computation."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        runtime: EnergyAdvisorRuntimeData,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._runtime = runtime
        self._price_listener = None

    async def async_config_entry_first_refresh(self) -> None:
        """Ensure we subscribe to sensor updates before the first refresh."""
        await super().async_config_entry_first_refresh()
        if self._price_listener is None:
            self._price_listener = async_track_state_change_event(
                self.hass,
                [self._runtime.config.price_sensor],
                self._handle_price_event,
            )

    async def _async_update_data(self):  # type: ignore[override]
        """Fetch the latest plan."""
        try:
            price_points = extract_price_points(self.hass, self._runtime.config.price_sensor)
        except PriceExtractionError as exc:
            raise UpdateFailed(str(exc)) from exc

        try:
            plan = generate_plan(
                PlannerInputs(
                    config=self._runtime.config,
                    activities=list(self._runtime.activities),
                    prices=price_points,
                )
            )
        except PlanningError as exc:
            raise UpdateFailed(str(exc)) from exc

        return plan

    def update_activities(self, activities: list[ActivityDefinition]) -> None:
        """Replace tracked activities and refresh plan."""
        self._runtime.activities = activities
        self.async_request_refresh()

    async def _handle_price_event(self, event) -> None:
        """Trigger refresh when price sensor updates."""
        LOGGER.debug("Price sensor %s changed; triggering refresh", self._runtime.config.price_sensor)
        await self.async_request_refresh()

    async def async_unload(self) -> None:
        """Clean up listeners."""
        if self._price_listener is not None:
            self._price_listener()
            self._price_listener = None
