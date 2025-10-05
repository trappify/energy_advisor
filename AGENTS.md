# Energy Advisor – Agent Notebook

## Mission Snapshot
- Build a Home Assistant (HA) integration that recommends optimal scheduling slots for user-defined energy-consuming activities.
- Ensure HACS compliance, semantic versioning, automated testing, and reproducible local HA lab for validation.
- Provide UI-based configuration (config flow wizard) and maintain polished documentation + changelog.

## Constraints & Ground Rules
- Repository managed via git (user: `trappify`, email: `andreas@trappland.se`).
- Tests must accompany all features; run and pass before commits.
- Maintain `manifest.json` version bumps aligned with releases for HACS.
- Prefer UI-configurable setup; avoid YAML-only configuration.
- Operate within CLI sandbox (danger full-access, no approval prompts).

## Phase Plan (Living Document)
1. **Scaffolding & Tooling** – Repo hygiene, dev docs, base HA integration skeleton, automated CI/test harness setup.
2. **Core Integration Logic** – Data coordinator, activity models, scheduling engine, storage.
3. **UI & UX** – Config flow, options flow, dashboards, translations.
4. **Testing & Validation** – Unit/integration tests, HA test instance automation, coverage targets.
5. **Release Prep** – Versioning, changelog, packaging, push to GitHub, publish guidance.

## Immediate Next Actions
- Extend planner heuristics to support advanced constraints (overlaps, blackout periods).
- Build integration tests for services and sensor entity updates.
- Design dashboard/output presentation strategy (calendar entities, Lovelace blueprint).

## Open Questions
- Exact sensor entity IDs / schema for energy prices (await user sample).
- Expected output format for recommended schedules (entities vs. dashboard cards).
- Priority of additional constraints (e.g., per-activity blackout windows, power limits).

_Keep this file updated as milestones progress; note blockers, decisions, and open issues._

## Progress Log
- [x] Phase 2 implementation: Delivered config flow, coordinator, planner, storage, services, and test suite (2025-02-14).
- [x] Phase 2 design: Authored architecture plan covering config flow, planner, and test strategy (2025-02-14).
- [x] Phase 1 kick-off: Created agent notebook and repository scaffolding log (2025-02-14).
- [x] Phase 1 tooling: Added Home Assistant dev lab (docker compose), Python dev tooling, integration skeleton, and smoke tests (2025-02-14).