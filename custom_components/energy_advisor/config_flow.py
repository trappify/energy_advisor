"""Config and options flow for Energy Advisor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import UpdateFailed

from .config import build_entry_data
from .const import (
    CONF_PRICE_SENSOR,
    CONF_SLOT_MINUTES,
    CONF_TIMEZONE,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_SLOT_MINUTES,
    DEFAULT_TIMEZONE,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    DOMAIN,
    LOGGER,
)
from .manager import EnergyAdvisorRuntimeData, async_save_activities, get_coordinator
from .models import ActivityDefinition, EnergyAdvisorConfig
from .util import str_to_time, time_to_str

GLOBAL_SETTINGS_SLOTS = [15, 30, 45, 60, 90, 120]
OPERATION_GLOBAL = "global"
OPERATION_ADD = "add"
OPERATION_EDIT = "edit"
OPERATION_REMOVE = "remove"
OPERATION_FINISH = "finish"

FIELD_OPERATION = "operation"
FIELD_ACTIVITY_ID = "activity_id"
FIELD_NAME = "name"
FIELD_DURATION = "duration_minutes"
FIELD_EARLIEST = "earliest_start"
FIELD_LATEST = "latest_end"
FIELD_PRIORITY = "priority"

ERROR_NO_SENSORS = "no_sensors"
ERROR_INVALID_TIME = "invalid_time"
ERROR_INVALID_SLOT = "invalid_slot"
ERROR_ACTIVITY_NOT_FOUND = "activity_not_found"


class EnergyAdvisorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Advisor."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_sensors: dict[str, str] = {}

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None):
        """Handle the initial step of the config flow."""
        errors: dict[str, str] = {}
        self._discovered_sensors = _discover_price_sensors(self.hass)

        if user_input is not None:
            try:
                price_sensor = user_input[CONF_PRICE_SENSOR]
                slot_minutes = int(user_input[CONF_SLOT_MINUTES])
                window_start = str_to_time(user_input[CONF_WINDOW_START])
                window_end = str_to_time(user_input[CONF_WINDOW_END])
                timezone = user_input.get(CONF_TIMEZONE) or None
            except (KeyError, ValueError):
                errors["base"] = ERROR_INVALID_TIME
            else:
                if not self._discovered_sensors:
                    errors["base"] = ERROR_NO_SENSORS
                elif price_sensor not in self._discovered_sensors:
                    errors[CONF_PRICE_SENSOR] = "invalid_selection"
                elif slot_minutes <= 0:
                    errors[CONF_SLOT_MINUTES] = ERROR_INVALID_SLOT
                else:
                    config = EnergyAdvisorConfig(
                        price_sensor=price_sensor,
                        slot_minutes=slot_minutes,
                        window_start=window_start,
                        window_end=window_end,
                        timezone=timezone,
                    )
                    await self.async_set_unique_id(price_sensor)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=self._discovered_sensors[price_sensor],
                        data=build_entry_data(config),
                    )

        if not self._discovered_sensors:
            errors["base"] = ERROR_NO_SENSORS

        schema = vol.Schema(
            {
                vol.Required(CONF_PRICE_SENSOR): vol.In(self._discovered_sensors),
                vol.Required(CONF_SLOT_MINUTES, default=DEFAULT_SLOT_MINUTES): vol.In(GLOBAL_SETTINGS_SLOTS),
                vol.Required(CONF_WINDOW_START, default=time_to_str(DEFAULT_WINDOW_START)): str,
                vol.Required(CONF_WINDOW_END, default=time_to_str(DEFAULT_WINDOW_END)): str,
                vol.Optional(CONF_TIMEZONE, default=self.hass.config.time_zone or DEFAULT_TIMEZONE): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return EnergyAdvisorOptionsFlowHandler(config_entry)


class EnergyAdvisorOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to manage scheduling settings and activities."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        self._selected_activity_id: str | None = None

    @property
    def _runtime(self) -> EnergyAdvisorRuntimeData:
        return self.hass.data[DOMAIN][self._entry.entry_id]

    async def async_step_init(self, user_input: Mapping[str, Any] | None = None):
        """Present the main options menu."""
        operations = {
            OPERATION_GLOBAL: "Update scheduling defaults",
            OPERATION_ADD: "Add activity",
            OPERATION_EDIT: "Edit activity",
            OPERATION_REMOVE: "Remove activity",
            OPERATION_FINISH: "Finish",
        }

        if not self._runtime.activities:
            operations.pop(OPERATION_EDIT, None)
            operations.pop(OPERATION_REMOVE, None)

        if user_input is not None:
            operation = user_input[FIELD_OPERATION]
            if operation == OPERATION_GLOBAL:
                return await self.async_step_global()
            if operation == OPERATION_ADD:
                return await self.async_step_add_activity()
            if operation == OPERATION_EDIT:
                return await self.async_step_edit_activity()
            if operation == OPERATION_REMOVE:
                return await self.async_step_remove_activity()
            if operation == OPERATION_FINISH:
                return self.async_create_entry(title="Energy Advisor", data=self._entry.options)

        schema = vol.Schema({vol.Required(FIELD_OPERATION): vol.In(operations)})
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_global(self, user_input: Mapping[str, Any] | None = None):
        """Edit global scheduling configuration."""
        errors: dict[str, str] = {}
        config = self._runtime.config

        if user_input is not None:
            try:
                slot_minutes = int(user_input[CONF_SLOT_MINUTES])
                window_start = str_to_time(user_input[CONF_WINDOW_START])
                window_end = str_to_time(user_input[CONF_WINDOW_END])
                timezone = user_input.get(CONF_TIMEZONE) or None
            except (KeyError, ValueError):
                errors["base"] = ERROR_INVALID_TIME
            else:
                if slot_minutes <= 0:
                    errors[CONF_SLOT_MINUTES] = ERROR_INVALID_SLOT
                else:
                    new_config = EnergyAdvisorConfig(
                        price_sensor=config.price_sensor,
                        slot_minutes=slot_minutes,
                        window_start=window_start,
                        window_end=window_end,
                        timezone=timezone,
                    )
                    self._runtime.config = new_config
                    self.hass.config_entries.async_update_entry(
                        self._entry, data=build_entry_data(new_config)
                    )
                    coordinator = get_coordinator(self._runtime)
                    if coordinator is not None:
                        await _safe_refresh(coordinator)
                    return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required(CONF_SLOT_MINUTES, default=config.slot_minutes): vol.In(GLOBAL_SETTINGS_SLOTS),
                vol.Required(CONF_WINDOW_START, default=time_to_str(config.window_start)): str,
                vol.Required(CONF_WINDOW_END, default=time_to_str(config.window_end)): str,
                vol.Optional(CONF_TIMEZONE, default=config.timezone or self.hass.config.time_zone or ""): str,
            }
        )
        return self.async_show_form(step_id="global", data_schema=schema, errors=errors)

    async def async_step_add_activity(self, user_input: Mapping[str, Any] | None = None):
        """Add a new activity definition."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                activity = _build_activity_from_user_input(user_input, require_id=False)
            except ValueError:
                errors["base"] = ERROR_INVALID_TIME
            else:
                activities = list(self._runtime.activities)
                activities.append(activity)
                await async_save_activities(self._runtime, activities)
                coordinator = get_coordinator(self._runtime)
                if coordinator is not None:
                    await _safe_update_activities(coordinator, activities)
                return await self.async_step_init()

        schema = _activity_schema()
        return self.async_show_form(step_id="add_activity", data_schema=schema, errors=errors)

    async def async_step_edit_activity(self, user_input: Mapping[str, Any] | None = None):
        """Edit an existing activity."""
        activities = list(self._runtime.activities)
        if not activities:
            return await self.async_step_init()

        if self._selected_activity_id is None:
            schema = vol.Schema(
                {
                    vol.Required(FIELD_ACTIVITY_ID): vol.In(
                        {activity.id: activity.name for activity in activities}
                    )
                }
            )
            if user_input is not None:
                self._selected_activity_id = user_input[FIELD_ACTIVITY_ID]
                return await self.async_step_edit_activity()
            return self.async_show_form(step_id="edit_activity_select", data_schema=schema)

        target = next((act for act in activities if act.id == self._selected_activity_id), None)
        if target is None:
            return await self.async_step_init()

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                updated = _build_activity_from_user_input(user_input, existing_id=target.id)
            except ValueError:
                errors["base"] = ERROR_INVALID_TIME
            else:
                new_activities = [updated if act.id == target.id else act for act in activities]
                await async_save_activities(self._runtime, new_activities)
                coordinator = get_coordinator(self._runtime)
                if coordinator is not None:
                    await _safe_update_activities(coordinator, new_activities)
                self._selected_activity_id = None
                return await self.async_step_init()

        schema = _activity_schema(default=target)
        return self.async_show_form(
            step_id="edit_activity",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_remove_activity(self, user_input: Mapping[str, Any] | None = None):
        """Remove an activity from the schedule."""
        activities = list(self._runtime.activities)
        if not activities:
            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required(FIELD_ACTIVITY_ID): vol.In(
                    {activity.id: activity.name for activity in activities}
                )
            }
        )
        if user_input is None:
            return self.async_show_form(step_id="remove_activity", data_schema=schema)

        target_id = user_input[FIELD_ACTIVITY_ID]
        new_activities = [activity for activity in activities if activity.id != target_id]
        if len(new_activities) == len(activities):
            return self.async_show_form(
                step_id="remove_activity",
                data_schema=schema,
                errors={"base": ERROR_ACTIVITY_NOT_FOUND},
            )

        await async_save_activities(self._runtime, new_activities)
        coordinator = get_coordinator(self._runtime)
        if coordinator is not None:
            await _safe_update_activities(coordinator, new_activities)
        return await self.async_step_init()

    async def async_step_edit_activity_select(
        self, user_input: Mapping[str, Any] | None = None
    ):
        """Proxy handler for legacy step id."""
        return await self.async_step_edit_activity(user_input=user_input)


def _discover_price_sensors(hass: HomeAssistant) -> dict[str, str]:
    """Return sensors that expose Nordpool-style raw price data."""
    sensors: dict[str, str] = {}
    for state in hass.states.async_all("sensor"):
        attributes = state.attributes
        if any(key in attributes for key in ("raw_today", "raw_tomorrow")):
            sensors[state.entity_id] = state.name or state.entity_id
    return sensors


def _activity_schema(default: ActivityDefinition | None = None) -> vol.Schema:
    """Build the schema used for add/edit activity forms."""
    return vol.Schema(
        {
            vol.Required(FIELD_NAME, default=default.name if default else ""): str,
            vol.Required(FIELD_DURATION, default=default.duration_minutes if default else 60): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            ),
            vol.Optional(
                FIELD_EARLIEST,
                default=time_to_str(default.earliest_start) if default and default.earliest_start else "",
            ): str,
            vol.Optional(
                FIELD_LATEST,
                default=time_to_str(default.latest_end) if default and default.latest_end else "",
            ): str,
            vol.Optional(FIELD_PRIORITY, default=default.priority if default else 0): vol.All(
                vol.Coerce(int), vol.Range(min=0)
            ),
        }
    )


def _build_activity_from_user_input(
    user_input: Mapping[str, Any],
    *,
    existing_id: str | None = None,
    require_id: bool = True,
) -> ActivityDefinition:
    """Create an activity definition from user submitted data."""
    name = user_input.get(FIELD_NAME)
    duration = int(user_input.get(FIELD_DURATION, 0))
    priority = int(user_input.get(FIELD_PRIORITY, 0))

    earliest_raw = user_input.get(FIELD_EARLIEST) or None
    latest_raw = user_input.get(FIELD_LATEST) or None

    earliest = str_to_time(earliest_raw) if earliest_raw else None
    latest = str_to_time(latest_raw) if latest_raw else None

    if duration <= 0:
        raise ValueError("Duration must be positive")

    activity_id = existing_id or (str(uuid4()) if not require_id else user_input.get(FIELD_ACTIVITY_ID))
    if activity_id is None:
        activity_id = str(uuid4())

    return ActivityDefinition(
        id=activity_id,
        name=name,
        duration_minutes=duration,
        earliest_start=earliest,
        latest_end=latest,
        priority=priority,
    )


async def _safe_refresh(coordinator: EnergyAdvisorCoordinator) -> None:
    """Refresh while swallowing planner errors."""
    try:
        await coordinator.async_refresh()
    except UpdateFailed as exc:  # pragma: no cover - defensive guard
        LOGGER.warning("Plan refresh failed during options flow: %s", exc)


async def _safe_update_activities(
    coordinator: EnergyAdvisorCoordinator, activities: list[ActivityDefinition]
) -> None:
    """Update activities and refresh without surfacing flow errors."""
    try:
        await coordinator.async_update_activities(activities)
    except UpdateFailed as exc:  # pragma: no cover - defensive guard
        LOGGER.warning("Plan refresh failed after activity change: %s", exc)
    except Exception as exc:  # pragma: no cover - defensive guard
        LOGGER.exception("Unexpected error updating activities: %s", exc)
