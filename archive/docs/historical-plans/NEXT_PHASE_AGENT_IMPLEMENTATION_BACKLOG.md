# Next-Phase Agent Implementation Backlog

Current as of 2026-06-08.

This document turns the `REPLICA` and `TRACE` design into implementation-ready work so the next step is coding, not re-planning.

## Scope

This backlog covers the next build phase after Epic 0, 1, and 2:

- `REPLICA` V1 contract and runtime slice
- `TRACE` V1 contract and runtime slice
- orchestration placement
- incident UI placement
- tests and demo acceptance

## Build Order

1. Land additive payload contracts for `REPLICA` and `TRACE`
2. Expose those contracts in seeded, live, and fallback incident payloads
3. Surface the investigation depth cards in Incident Detail
4. Implement `REPLICA` V1 runtime behavior for the flagship checkout outage
5. Feed `REPLICA` findings into `FORGE` and `GUARDIAN`
6. Implement `TRACE` V1 narrowing logic
7. Feed `TRACE` findings into `FORGE` and `GUARDIAN`
8. Re-run browser and backend validation

## REPLICA V1

### Product goal

Show whether the flagship outage can be recreated in a curated production-like sandbox and whether that changes confidence in the current hypothesis.

### Files to touch

- `server/models.py`
- `server/services/enterprise_runtime.py`
- `server/services/incidents.py`
- `server/services/surface_payloads.py`
- `server/services/live_demo.py`
- `frontend/incident.html`
- `frontend/static/incident.js`
- `frontend/static/api.js`
- `tests/test_app.py`
- `tests/test_api_contract.py`
- `tests/e2e/browser-verification.spec.js`

### Contract fields

- `incident_id`
- `environment_pack_id`
- `reproduction_status`
- `reproduced_symptoms`
- `hypothesis_supported`
- `confidence_delta`
- `tested_mitigations`
- `reasoning`

### V1 implementation slice

Use deterministic environment-pack selection and reproduction outcomes for the flagship outage classes.

Rules:

- checkout retry / timeout cascade -> `checkout-python-fastapi-auth-redis-v1`
- checkout DB pool exhaustion -> `checkout-python-fastapi-postgres-v1`
- public certificate outage -> `edge-nginx-acme-v1`

V1 output rules:

- seeded flagship incidents can return deterministic reproduction results
- live raw-text incidents can derive reproduction status from parsed signatures and issue family
- non-flagship incidents can return `not_run`

### Acceptance criteria

- `replica_summary` is present in incident context
- flagship checkout incident shows a non-empty environment pack
- reproduction status is visible in the incident UI
- tested mitigations are visible for the flagship case

## TRACE V1

### Product goal

Narrow the likely code path enough that an engineer knows where to start, without claiming to be a universal debugger.

### Files to touch

- `server/models.py`
- `server/services/enterprise_runtime.py`
- `server/services/incidents.py`
- `server/services/surface_payloads.py`
- `server/services/live_demo.py`
- `frontend/incident.html`
- `frontend/static/incident.js`
- `frontend/static/api.js`
- `tests/test_app.py`
- `tests/test_api_contract.py`

### Contract fields

- `incident_id`
- `service`
- `trace_status`
- `suspected_modules`
- `suspected_functions`
- `expected_flow`
- `observed_divergence`
- `state_anomalies`
- `confidence`
- `reasoning`

### V1 implementation slice

Use issue-family-aware narrowing for the flagship outage classes.

Rules:

- retry amplification -> point at retry middleware, auth timeout handler, circuit-breaker path
- DB pool exhaustion -> point at checkout session lifecycle, retry patch, pool checkout path
- certificate expiry -> point at certificate loader, trust chain validator, edge listener config

V1 should be:

- deterministic
- evidence-driven
- additive to current diagnosis
- safe to render even when no deeper debug state exists

### Acceptance criteria

- `trace_summary` is present in incident context
- flagship incident shows suspected modules/functions
- the UI explains what engineering should inspect first
- `FORGE` and `GUARDIAN` can later consume this without another contract change

## Orchestration Placement

### Current shipped flow

`SENTINEL -> PRISM -> FORGE -> GUARDIAN`

### Next-phase flow

`SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

### Practical sequencing

- `REPLICA` should run after PRISM synthesis
- `TRACE` should run after `REPLICA`
- `FORGE` should cite:
  - memory basis
  - reproduction basis
  - debugging basis
- `GUARDIAN` should distinguish:
  - validated signals
  - inferred signals

## Incident UI Placement

The Incident Detail page should gain one new grouped surface:

- `Investigation Depth`

Cards:

1. `REPLICA`
   - environment pack
   - reproduction status
   - confidence delta
   - tested mitigations

2. `TRACE`
   - suspected modules
   - suspected functions
   - observed divergence
   - engineering starting point

This surface should sit below memory and above collapsed technical detail.

## Validation Tasks

### Backend

- payload contains `replica_summary`
- payload contains `trace_summary`
- flagship incident populates deterministic values
- fallback incident still remains valid

### Browser

- incident page shows the new investigation depth cards
- the cards render for seeded flagship incidents
- raw-text intake can still open into the same incident workspace

### Manual verification

Update:

- `docs/LOCAL_ENTERPRISE_ONE_SHOT_TEST.md`

Add checks for:

- reproduction pack is visible
- reproduction status is visible
- debugging hints are visible
- operator can explain how these findings influence the recommended action
