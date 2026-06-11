# NEXUS v3 Working State

Short handoff for Codex sessions. Keep current and compact.

## Current Phase

Items 0–8: **complete** (see PLAN.md for full ledger)
Items 9–14: **in progress via automated loop** — see `backlog.json`

## App In One Sentence

NEXUS is an AI support-triage and incident-investigation product: noisy logs go in, a triaged investigation packet comes out, one human review gate (GUARDIAN) remains.

## Baseline State

- Branch: `master`, commit: `dce8c99`
- `pytest tests/ -q` → **120 passed, 3 failed (pre-existing — do not fix)**
- Pre-existing failures: `test_replica_runner_inspects_pack_scaffold_assets`, `test_replica_runner_executes_db_pool_pack`, `test_webhook_requires_valid_signature`
- `npm run browser:verify` → 6 passed
- `./scripts/docker_fresh.sh` → passes
- `./scripts/local_enterprise_smoke.sh` → passes
- `python demo.py` → passes

## What Is Complete (items 0–8)

- UI shell: queue, incident console, inputs, replay, training, settings
- SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN pipeline (live graph path)
- REPLICA runtime substrate: `replica_runtime.py`, two Docker Compose packs
- `build_trace_summary`, `build_replica_summary`, `enrich_memory_with_runtime`, `rank_candidate_fixes_with_runtime` all implemented in `enterprise_runtime.py`
- FORGE and GUARDIAN runtime-aware posture: fully implemented in the live graph path (`_forge_node`, `_guardian_node`)
- Deployment-safe runtime behavior (fails closed without Docker)

## What Is Pending (items 9–14)

See `backlog.json` for full detail. Summary:

| # | Title | Key gap |
|---|---|---|
| 9 | Runtime evidence weighting in FORGE | `best_mitigation_outcome_class` and `runtime_comparison_summary` are empty in static/seeded path — `build_mitigation_checks` never sets `outcome_class` |
| 10 | Runtime-aware GUARDIAN posture | Static path returns raw fixture guardian reasoning — `validated_clause` enrichment from `_guardian_node` is not applied in `build_incident_response` |
| 11 | TRACE developer handoff packet v2 | Cascades from item 9 — `runtime_comparison_summary` being empty means TRACE state_anomalies miss the runtime evidence line |
| 12 | Runtime comparison UI refinement | `#runtimeComparisonBlock`, `#runtimeBaselineRow`, `#runtimeMitigatedRow`, `#runtimeOutcomeLabel` DOM IDs do not exist yet |
| 13 | Memory linkage to runtime outcomes | `memory_hits` not returned from `build_incident_response` and `enrich_memory_with_runtime` not called in static path |
| 14 | End-to-end demo closure | demo.py, DEMO_WALKTHROUGH.md, DEMO_CHEAT_SHEET.md need runtime narrative |

## Two Code Paths — Critical to Understand

**STATIC/SEEDED path** (what tests and Playwright use):
`surface_payloads.py:build_incident_response` → reads from `incident_payloads.py` fixtures

**LIVE GRAPH path** (what live incidents use):
`enterprise_runtime.py` LangGraph nodes (`_forge_node`, `_guardian_node`, etc.)

Items 9–13 fix the **static path**. The live path is already correct.

## Loop Setup Files

- `backlog.json` — machine-readable task list (items 9–14)
- `AGENTS.md` — full loop rules, file map, function map
- `.agents/skills/nexus-backlog-loop.md` — Codex app skill
- `BLOCKERS.md` — auto-populated if agent gets stuck

## Most Important Files for Items 9–14

| File | Why |
|---|---|
| `server/services/enterprise_runtime.py` | `build_mitigation_checks`, `build_replica_summary`, `build_trace_summary`, `enrich_memory_with_runtime` |
| `server/services/surface_payloads.py` | `build_incident_response` — the static path that all tests use |
| `server/incident_payloads.py` | INC001 and INC002 fixture data |
| `frontend/incident.html` | REPLICA card — needs `#runtimeComparisonBlock` et al |
| `frontend/static/incident.js` | Populates the REPLICA/TRACE/FORGE/GUARDIAN DOM from API response |
| `tests/e2e/browser-verification.spec.js` | Playwright spec — will grow from 6 to 10 tests after item 12 |
| `scripts/local_enterprise_smoke.sh` | Smoke checks both INC001 and INC002 on live Docker |

## Operating Mode for Loop

- Reasoning: **Extra High** for the full loop run
- Default: follow AGENTS.md loop rules, do not stop between items
- Do not fix the 3 pre-existing test failures — they are out of scope
