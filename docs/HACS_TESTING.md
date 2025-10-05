# HACS Workflow Validation

This project targets HACS distribution. Use the checklist below whenever we cut a release or regress functionality.

## Prerequisites
- Local Home Assistant dev lab running via `docker compose up` (see repository README).
- HACS installed inside the dev lab (download release from https://github.com/hacs/integration/releases and place under `/config/custom_components/hacs`).
- Create a long-lived access token in Home Assistant for the HACS onboarding wizard (one-time setup inside the test instance).

## Package Sanity Checks
1. Run `./scripts/build_release.sh <version>` and confirm the resulting archive under `dist/` contains:
   - `custom_components/energy_advisor/**`
   - `hacs.json`
   - `README.md`
   - `docs/ARCHITECTURE.md`
   - `AGENTS.md`
   No `__pycache__` or `.pyc` files should ship.
2. Execute `python -m script.hassfest` from the repo root (inside the virtualenv) to validate manifest metadata.
3. Ensure `manifest.json` version matches the tagged release you are preparing and follows semantic versioning.

## HACS Install Test (Custom Repository)
1. Start the Home Assistant dev container (`./scripts/run_homeassistant.sh -d`).
2. In the HA UI → Settings → Devices & Services → HACS, add a **Custom repository** pointing to `https://github.com/trappify/energy_advisor` with category **Integration**.
3. Install “Energy Advisor” from HACS, choose the version/tag under test, and restart Home Assistant when prompted.
4. Navigate to Settings → Devices & Services → “+ Add Integration” and confirm “Energy Advisor” appears and the config flow loads successfully.

## Post-Install Smoke
- Complete the config flow using the built-in Nordpool sensor fixture or a mock sensor.
- Verify the `sensor.energy_advisor_plan` entity is created and populated after the first refresh.
- Invoke `energy_advisor.recompute_plan` service from Developer Tools to ensure manual refresh is functional.

## Release Checklist
- Update `hacs.json` minimum Home Assistant version when bumping core requirements.
- Update `README.md` installation instructions if the workflow changes.
- Tag the release (`git tag vX.Y.Z && git push origin vX.Y.Z`) after tests pass and HACS manual install succeeds.
