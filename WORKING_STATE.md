# NEXUS v3 Working State

Short handoff for Codex or Claude sessions. Keep current and compact.

## Current Phase

Items `15–34`: **complete**
Items `35–40`: **complete**
Items `41–46`: **complete**
Items `47–53`: **complete**
Items `54–60`: **complete**
Items `61–68`: **complete** (hardening and truthfulness checkpoint)
Items `69–76`: **complete** (pilot readiness checkpoint) in `backlog-69-plus.json`
Items `77–85`: **complete** (market-ready v1 hardening, deployment preparation, buyer proof, UI polish, release checkpoint) in `backlog-77-plus.json`
Items `86–92`: **complete** (wedge-strengthening, three-outage support, LLM reasoning enhancement, pilot conversion, checkpoint) in `backlog-86-plus.json`
Items `93–100`: **complete** (pilot conversion and technical proof deepening) in `backlog-93-plus.json`
Items `101–108`: **complete** (FR2 repeatable enterprise pilot checkpoint) in `backlog-101-plus.json`

## App In One Sentence

NEXUS is an AI support-triage and incident-investigation product: noisy logs go in, a triaged investigation packet comes out, and one governed human review gate remains.

## Baseline State

- Branch: `master`
- Baseline feature slice through item `108` (FR2 repeatable enterprise pilot checkpoint complete): latest commit
- `pytest tests/ -q` → **150 passed**
- `npm run browser:verify` → **11 passed**
- `python demo.py` → all three incidents complete
- `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` → passes
- `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` → passes (all smoke checks)

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
- **bounded debugger flow for `INC001` with ordered checkpoints and state transitions**
- **premium visual system across all core surfaces** (item 35)
- **improved incident console information architecture** (item 36)
- **fresh incident runtime-story parity** with clear scaffold-only language (item 37)
- **runtime-host visibility** in operator UI (item 39)
- **owner-facing docs and manual walkthrough synced to current runtime-host product reality** (item 40)
- **operator-triggered bounded replay for fresh incidents** with live incident console action (item 41)
- **runtime-host capability matrix and pack coverage visibility** in training page (item 42)
- **persisted debugger evidence and replay-linked debugging trail** for INC001 (item 43)
- **developer handoff packet v5** with owner-first inspection brief and replay evidence (item 44)
- **post-approval outcome capture and memory ingestion** with visible incident UI and training reference (item 45)
- **final operator-to-engineering demo closure** with updated walkthrough and post-approval flow (item 46)
- **engineering handoff export and case packaging** for support-to-engineering delivery (item 47)
- **bounded debugger parity for INC002** with explicit curated-pack scope (item 48)
- **runtime-host productization v2** with stronger product-facing execution posture (item 49)
- **outcome-weighted memory ranking** based on executed or approved outcomes (item 50)
- **curated pack onboarding contract** for new outage-class support (item 51)
- **operator ROI and audit surface** showing replay, approval, and reuse value (item 52)
- **visual system reinvention pass** beyond the item-35 refinement (item 53)
- **delivery-target handoff packages** for GitHub, Jira-style, and Slack-style workflows (item 54)
- **replay-driven mitigation matrix** for flagship incidents (item 55)
- **runtime-host run queue and execution guardrails** with visible training-surface posture (item 56)
- **recurrence-aware outcome memory and reopen signals** in the memory layer (item 57)
- **curated pack validator and scaffold tooling** for bounded pack expansion (item 58)
- **approval audit timeline and governance export** for the flagship flow (item 59)
- **final product-design polish and story sync** after the enterprise workflow surfaces landed (item 60)

## What Is Real Today Vs Still Bounded

Real today:

- the packaged app on `:7860` can delegate replay to the runtime host when `ENABLE_RUNTIME_HOST_RELAY=1` is enabled
- replay evidence persists back into the live incident view
- seeded and live incident paths both distinguish runtime-backed evidence from scaffold-only inference
- the manual walkthrough in `docs/DEMO_WALKTHROUGH.md` is accurate for the current flagship flow

Still bounded:

- REPLICA only supports the curated checkout outage packs
- TRACE is a bounded developer handoff, not a universal debugger
- the debugger flows are descriptive guidance, not interactive step-through debuggers
- external delivery targets are still export-oriented rather than full third-party integrations
- bounded downstream sends and engineering feedback loops are now present for the pilot workflow
- recent runtime execution history is durable, but active in-flight runtime posture is still app-local rather than full job orchestration

## Two Code Paths — Critical To Understand

**STATIC/SEEDED path**:
`server/services/surface_payloads.py:build_incident_response` → reads from `server/incident_payloads.py` fixtures

**LIVE GRAPH path**:
`server/services/enterprise_runtime.py` plus `server/services/incidents.py`

These paths must stay semantically aligned.

## Loop Setup Files

- `backlog-next.json` — completed backlog through item `34`
- `backlog-35-plus.json` — completed backlog through item `40`
- `backlog-41-plus.json` — completed backlog through item `46`
- `backlog-47-plus.json` — completed backlog through item `53`
- `backlog-54-plus.json` — completed backlog through item `60`
- `backlog-61-plus.json` — completed backlog through item `68`
- `backlog-69-plus.json` — completed backlog through item `76`
- `backlog-77-plus.json` — completed backlog through item `85` (market-ready v1 release)
- `backlog-86-plus.json` — completed backlog through item `92`
- `backlog-93-plus.json` — completed backlog through item `100`
- `backlog-101-plus.json` — completed backlog through item `108` (FR2 repeatable enterprise pilot checkpoint)
- `backlog-109-plus.json` — next backlog for five-family selective wedge expansion
- `AGENTS.md` — loop rules and current validated baseline
- `docs/LOOPS_RUNBOOK.md` — operator-facing guide and prompt templates
- `docs/DEMO_WALKTHROUGH.md` — owner walkthrough for the business use case
- `docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md` — broader product strategy and scope
- `docs/POST_100_FIELD_PILOT_EXECUTION_AND_PROOF_AT_SCALE_PLAN.md` — FR2 direction after pilot conversion and technical proof deepening
- `docs/POST_100_EXECUTION_MAP.md` — task/subtask execution map for items `101–108`
- `docs/POST_108_SELECTIVE_EXPANSION_PLAN.md` — post-FR2 five-family wedge plan
- `docs/POST_108_EXECUTION_MAP.md` — task/subtask execution map for items `109–116`

## Most Important Files For The Next Phase

| File | Why |
|---|---|
| `server/services/incidents.py` | incident packet assembly, exports, governance, execution outcome |
| `server/services/enterprise_runtime.py` | live path runtime, trace, forge, guardian, and memory behavior |
| `server/services/replica_runtime.py` | bounded pack execution, validator, and pack expansion substrate |
| `server/app.py` | app-side runtime execution posture and exported endpoints |
| `frontend/static/incident.js` | incident packet rendering, exports, governance, and replay matrix |
| `frontend/static/training.js` | runtime-host posture and audit/ROI surfaces |
| `frontend/static/styles.css` | design-system continuity as new product surfaces are added |
| `tests/test_api_contract.py` | API truthfulness across new enterprise workflow surfaces |
| `tests/e2e/browser-verification.spec.js` | browser truthfulness and flagship UX |
| `scripts/local_enterprise_smoke.sh` | Docker-path confidence checks |

## Next Recommended Frontier

The active frontier is `backlog-109-plus.json`.

Use these documents together:

- [docs/POST_108_SELECTIVE_EXPANSION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_108_SELECTIVE_EXPANSION_PLAN.md)
- [docs/POST_108_EXECUTION_MAP.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_108_EXECUTION_MAP.md)
- [backlog-109-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-109-plus.json)

This phase is the post-FR2 selective expansion sprint: widen the bounded wedge from three outage families to five while keeping seeded and live paths truthful and coherent.
