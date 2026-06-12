# NEXUS v3 Working State

Short handoff for Codex or Claude sessions. Keep current and compact.

## Current Phase

Items `15–34`: **complete**
Next phase: execute `backlog-35-plus.json`

## App In One Sentence

NEXUS is an AI support-triage and incident-investigation product: noisy logs go in, a triaged investigation packet comes out, and one governed human review gate remains.

## Baseline State

- Branch: `master`
- Baseline commit: `83d8510`
- `pytest tests/ -q` → **141 passed**
- `npm run browser:verify` → **11 passed**
- `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` → passes
- `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` → passes
- `python demo.py` → passes

## What Is Complete

- support-triage product narrative across queue, inputs, incident, replay, training, and docs
- SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN pipeline
- two bounded runtime packs:
  - `INC001` timeout / retry amplification
  - `INC002` DB pool exhaustion / session leak
- packaged-app replay delegation to a Docker-capable runtime host
- replay persistence for live `nxs_...` incidents
- runtime trust, lifecycle, and replay history visibility
- hypothesis packet for the flagship outages
- TRACE owner cues and trace-to-code packet for both flagship outages
- mitigation ladder across REPLICA, FORGE, and GUARDIAN
- bounded debugger packet for `INC001` only

## What Is Real Today Vs Still Bounded

Real today:

- the packaged app on `:7860` can delegate replay to the runtime host when `ENABLE_RUNTIME_HOST_RELAY=1` is enabled
- replay evidence persists back into the live incident view
- seeded and live incident paths both distinguish runtime-backed evidence from scaffold-only inference
- the manual walkthrough in `docs/DEMO_WALKTHROUGH.md` is accurate for the current flagship flow

Still bounded:

- REPLICA only supports the curated checkout outage packs
- TRACE is a bounded developer handoff, not a universal debugger
- the debugger packet is descriptive guidance, not an interactive step-through debugger
- the UI is improved from the original baseline but not yet fully redesigned

## Two Code Paths — Critical To Understand

**STATIC/SEEDED path**:
`server/services/surface_payloads.py:build_incident_response` → reads from `server/incident_payloads.py` fixtures

**LIVE GRAPH path**:
`server/services/enterprise_runtime.py` plus `server/services/incidents.py`

These paths must stay semantically aligned.

## Loop Setup Files

- `backlog-next.json` — completed backlog through item `34`
- `backlog-35-plus.json` — active backlog for the next frontier
- `AGENTS.md` — loop rules and current validated baseline
- `docs/LOOPS_RUNBOOK.md` — operator-facing guide and prompt templates
- `docs/DEMO_WALKTHROUGH.md` — owner walkthrough for the business use case
- `docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md` — broader product strategy and scope

## Most Important Files For The Next Phase

| File | Why |
|---|---|
| `frontend/static/styles.css` | global product visual system and differentiation |
| `frontend/incident.html` | incident console layout and flagship operator flow |
| `frontend/static/incident.js` | incident packet rendering and new product affordances |
| `frontend/static/api.js` | fresh incident parity and fallback synthesis |
| `server/services/enterprise_runtime.py` | live path runtime, trace, forge, guardian behavior |
| `server/services/incidents.py` | live incident context assembly and replay persistence |
| `server/services/replica_runtime.py` | bounded pack execution and debugger/replay substrate |
| `runtime_host/server/app.py` | runtime-host execution behavior |
| `tests/e2e/browser-verification.spec.js` | browser truthfulness and flagship UX |
| `scripts/local_enterprise_smoke.sh` | Docker-path confidence checks |

## Next Recommended Frontier

1. full UI revamp for the core product surfaces so the product feels materially different and easier to understand
2. stronger flagship incident console information architecture
3. stronger parity for fresh `nxs_...` incidents with the seeded runtime story
4. bounded debugger execution flow for `INC001`
5. runtime-host operator UX and runtime pack productization
6. final docs/demo sync for the deeper product layer
