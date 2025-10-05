# Energy Advisor Integration Architecture

## Goals & Scope
The Energy Advisor integration recommends cost-efficient time slots for user-defined activities based on forward-looking energy prices. The initial release focuses on hourly and quarter-hourly Nordpool price data, activity durations, and optional user constraints (e.g., operating window). The integration must be fully configurable through the Home Assistant UI and compatible with HACS.

Key objectives:
- Provide a config flow that lets users pick an energy price sensor and define global scheduling constraints.
- Offer an options flow to manage activities (create, update, delete) and set per-activity constraints.
- Persist activity definitions and planner state using Home Assistant storage helpers tied to the config entry.
- Expose recommended schedules as Home Assistant entities, services, and diagnostics.
- Compute schedules automatically when new price data arrives or activities change.

## Component Overview

### Integration Surfaces
- **Config Flow (`config_flow.py`)** – multi-step wizard collecting:
  1. Energy price sensor entity (defaults filtered to Nordpool-compatible sensors supporting `raw_today`/`raw_tomorrow`).
  2. Global settings: default operating window, slot granularity, optional timezone override.

- **Options Flow** – two-phase UI:
  1. Global update form mirroring default operating constraints.
  2. Activity management sub-flow supporting add/edit/delete with storage-backed persistence.

- **Data Coordinator (`coordinator.py`)** – orchestrates price fetching, schedule computation, and entity updates:
  - Listens to state changes on the configured price sensor.
  - Normalises price data into a standard `PriceSeries` (15-minute resolution default; coalesces hourly data if needed).
  - Triggers planner recalculations on sensor updates, daily rollover, and activity changes.
  - Exposes cached planner results for entities/services.

- **Planner Engine (`planner.py`)** – pure-Python module encapsulating scheduling logic:
  - Accepts `ActivityDefinition` list, `PriceSeries` (timestamped prices), and global constraints.
  - Produces `ScheduleSolution` containing per-activity start times, cost estimates, and diagnostics (total cost, average price, slack).
  - Initial algorithm: greedy best-fit with conflict resolution on 15-minute slots, prioritised by either user priority or lowest per-slot cost.
  - Extensible to support more advanced optimisation (ILP) without impacting integration surfaces.

- **Storage Layer (`storage.py`)** – wraps `homeassistant.helpers.storage.Store` to persist activities and planner settings keyed by config entry ID. Provides typed accessors for tests and runtime.

- **Entities**
  - `sensor.energy_advisor_plan` – attributes hold recommended schedule, per-activity cost breakdown, metadata (plan date, data source, constraints).
  - Future-proof placeholder for `calendar` platform integration (optional Phase 3 addition) to visualise scheduled slots.

- **Services**
  - `energy_advisor.recompute_plan` – manual trigger for schedule recalculation.
  - `energy_advisor.export_plan` – return structured plan for automation usage (e.g., create todo tasks).

- **Diagnostics**
  - Implementation via `diagnostics.py` exposing latest price data snapshot, activities, and scheduler logs for troubleshooting.

## Data Model

```text
ConfigEntryData
  - price_sensor_entity_id: str
  - slot_minutes: int (default 15)
  - window_start: time (default 00:00)
  - window_end: time (default 23:59)
  - timezone: Optional[str]

ActivityDefinition
  - id: str (uuid)
  - name: str
  - duration_minutes: int
  - earliest_start: Optional[time]
  - latest_end: Optional[time]
  - priority: int (lower value = higher priority)
  - metadata: dict[str, Any] (for future extensions: max_daily_runs, notes, etc.)

PricePoint
  - start: datetime
  - end: datetime
  - price: Decimal
  - currency: str

ScheduleSolution
  - generated_at: datetime
  - horizon_start/horizon_end: datetime
  - activities: list[ScheduledActivity]
  - total_cost: Decimal
  - average_price: Decimal
  - unavailable_activities: list[str] (IDs unable to be scheduled under constraints)

ScheduledActivity
  - activity_id: str
  - start: datetime
  - end: datetime
  - slots: list[PricePoint]
  - cost: Decimal
```

## Scheduling Strategy

1. **Normalisation** – Convert `raw_today` / `raw_tomorrow` into a combined `PriceSeries` sorted by start time. If the sensor only exposes hourly prices, expand to the configured `slot_minutes` resolution.
2. **Constraint Window** – Build the allowed scheduling horizon based on global and per-activity windows (converted to datetimes within the relevant day).
3. **Slot Assignment**
   - Generate availability map with `slot_minutes` granularity.
   - For each activity (ordered by priority, then longest duration):
     - Scan candidate start times within constraints.
     - Compute cost as sum(price × duration share).
     - Select minimum-cost start that keeps slots exclusive.
   - Record conflicts or unscheduled activities for diagnostics.
4. **Lifecycle Hooks** – Re-run when:
   - Price sensor state updated and includes future prices.
   - Midnight rollover (handled via `async_track_time_change`).
   - Activities or global options mutate.

5. **Extendability** – Planner designed with a strategy interface to optionally switch to ILP or heuristics later.

## Test Strategy

- **Unit Tests**
  - Planner logic with synthetic price grids (cheap/expensive windows) ensuring correct slot selection and conflict avoidance.
  - Storage layer to confirm persistence round-trips and migrations.
  - Config/Options flows verifying form validation (e.g., invalid durations, overlapping windows).

- **Integration Tests** (pytest-homeassistant-custom-component)
  - Simulate Nordpool sensor updates using fixture data (derived from the provided sample).
  - Validate entity state/attributes after planner runs.
  - Exercise service calls and ensure recomputation updates the plan.

- **Dev Environment**
  - Docker HA lab ensures end-to-end manual validation with actual Nordpool integration if desired.

## Roadmap Considerations

- Phase 2: Implement planner, storage, coordinator, and tests using sample Nordpool data.
- Phase 3: Build config/options flows, translations (`en.json`, `sv.json`), and UI surfaces.
- Phase 4: Add calendar entity support and optional Lovelace dashboard blueprint.
- Phase 5: Harden for release (manifest version management, changelog, GitHub workflows, PyPI packaging if needed).
