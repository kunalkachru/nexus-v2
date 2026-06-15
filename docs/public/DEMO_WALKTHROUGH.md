# NEXUS Full Manual Walkthrough

Current as of 2026-06-15.

Use this walkthrough to validate the product end to end and to present the current shipped workflow truthfully.

## What This Walkthrough Proves

**NEXUS turns noisy production evidence into a triaged, investigated, engineering-ready case before one final human review point, with bounded runtime validation where supported.**

The walkthrough should make these things obvious:

1. support does not need to relay raw logs across multiple humans first
2. likely issue family and likely owner are surfaced quickly
3. prior incidents and runbooks are reused
4. replay validation is explicit when supported and explicit when unavailable
5. debugging guidance is visible and bounded
6. the final action remains governed

## Current Incident Families

At the current baseline, NEXUS supports five bounded outage families:

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike
4. `INC005` queue / worker backlog affecting transaction completion
5. `INC007` auth dependency slowdown / token validation failures

Use `INC001` as the flagship story unless you specifically want to show queue backlog or auth dependency behavior.

## Setup

Preferred packaged path:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

## Primary Screens

Walk these in order:

1. `/inputs`
2. a created `nxs_...` incident or `/incident?nexus_incident_id=INC001`
3. `/training`

Supporting routes:

- `/queue`
- `/history`
- `/replay`
- `/settings`

## 1. Inputs

What it should communicate:

- this is the intake surface for messy production evidence
- the product is built around real support-triage intake, not prompt demos
- NEXUS evaluates intake quality before pretending confidence

## 2. Incident Detail

What it should communicate:

- the system has already reduced manual relay work
- the operator is reviewing a structured investigation packet
- the final decision remains explicit and governed

What to inspect:

- top summary and working memory
- `Investigation Summary & Operator Path`
- task board and memory context
- REPLICA replay posture
- TRACE debugging packet
- FORGE mitigation ranking
- GUARDIAN review language

### Runtime Evidence Story

The evidence chain is:

1. REPLICA identifies the supported pack and, when available, executes bounded replay
2. FORGE uses that result to weight mitigation choice
3. GUARDIAN distinguishes runtime-backed versus inference-first posture

## 3. Training

What it should communicate:

- what just happened in the latest live triage
- whether the product is healthy and bounded
- what value the product is claiming for a pilot

Inspect:

- `Latest live triage`
- `Pilot scorecard dashboard`
- runtime host and pack coverage surfaces
- product health and governance posture

## Core Story To Tell

Use this sentence:

**NEXUS reduces manual support-to-engineering relay by turning raw evidence into a runtime-aware, debugging-guided, review-ready case.**

Do not overclaim:

- universal debugger
- arbitrary environment reproduction
- autonomous production healing
