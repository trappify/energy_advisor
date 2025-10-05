# Energy Advisor

Custom Home Assistant integration that suggests low-cost time slots for energy intensive activities using forward-looking price data (e.g., Nordpool). Users define activities, durations, and optional time windows; Energy Advisor builds a plan aligned with price forecasts and exposes it via sensor attributes and services.

## HACS Installation (Custom Repository)

1. Add custom repository in HACS: `https://github.com/trappify/energy_advisor` (Category: Integration).
2. Install **Energy Advisor** from HACS and restart Home Assistant when prompted.
3. Go to *Settings → Devices & Services → + Add Integration* and search for "Energy Advisor" to complete the UI setup wizard.

> **Note:** Until public releases are tagged, the integration must be added as a custom repository. Once tagged, HACS will detect stable releases automatically.

## Manual Installation

1. Download the latest archive generated via `./scripts/build_release.sh` or grab the repository ZIP.
2. Extract the archive so that `custom_components/energy_advisor` sits inside your Home Assistant `/config/custom_components/` directory.
3. Restart Home Assistant and add the integration through the UI.

## Services & Entities

- `sensor.energy_advisor_plan`: exposes the computed schedule with per-activity details.
- `energy_advisor.recompute_plan`: force a planner refresh.
- `energy_advisor.export_plan`: return the latest plan payload.

## Development

- Python 3.11+
- Install dependencies: `pip install -e .[dev]`
- Run tests: `pytest`
- Lint/format (ruff): `ruff check .`
- Package release artifact: `./scripts/build_release.sh <version>` → outputs `dist/energy_advisor-<version>.zip`
- Install HACS in the dev lab: `./scripts/install_hacs.sh`
- Install Nordpool custom integration: `./scripts/install_nordpool.sh`
- Local Home Assistant lab: `docker compose up`

Additional architecture notes and HACS validation steps live under `docs/`.
