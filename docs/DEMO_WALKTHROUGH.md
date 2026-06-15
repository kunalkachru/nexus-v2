# NEXUS Full Manual Walkthrough

Current as of 2026-06-15.

Use this walkthrough to understand the product end to end, validate the bounded business use case, and demo the current shipped workflow truthfully.

## Before You Start

Check the current validated baseline in [WORKING_STATE.md](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md).

Core commands:

```bash
pytest tests/ -q
npm run browser:verify
python demo.py
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

## What This Walkthrough Proves

The claim is:

**NEXUS turns noisy production evidence into a triaged, investigated, engineering-ready case before one final human review point, with bounded runtime validation where supported.**

The walkthrough should make these things obvious:

1. support does not need to relay raw logs across multiple humans first
2. the likely issue family and likely owner are surfaced quickly
3. prior incidents and runbooks are reused
4. replay validation is explicit when supported and explicit when unavailable
5. debugging guidance is visible and bounded
6. the final action remains governed

## Current Incident Families

At the current baseline, NEXUS supports three bounded outage families:

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike

Use `INC001` as the flagship story unless you specifically want to show DB or rollback behavior.

## What The Product Is Today

The visible workflow is:

- `SENTINEL`: classification and issue framing
- `PRISM`: diagnosis, memory, and evidence correlation
- `REPLICA`: bounded replay and mitigation comparison
- `TRACE`: bounded developer handoff and debugger guidance
- `FORGE`: mitigation ranking and runbook selection
- `GUARDIAN`: final review and governed execution posture

Important boundary:

- replay is only real when the runtime posture says it executed
- TRACE is a bounded handoff/debugging layer, not a universal debugger

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

Open:

- [http://127.0.0.1:7860/inputs](http://127.0.0.1:7860/inputs)

What it should communicate:

- this is the intake surface for messy production evidence
- the product is built around real support-triage intake, not prompt demos
- NEXUS evaluates intake quality before pretending confidence

What to do:

1. click `Load example logs`
2. click `Submit raw logs`

Expected:

- a fresh `nxs_...` incident is created
- the app redirects into the incident console
- the incident reads like a shaped case, not a raw log dump

## 2. Incident Detail

Open:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC001](http://127.0.0.1:7860/incident?nexus_incident_id=INC001)

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

The operator should be able to answer:

- was replay actually run?
- if yes, what changed?
- if no, what is still inference-first?

### What Is Implemented Now

Implemented now:

- runtime-backed replay for curated packs
- runtime-host delegation for packaged demos
- persisted replay packet for live incidents
- mitigation comparison and trust packet
- bounded debugger-style packets for the supported curated paths

Still bounded:

- no arbitrary environment reproduction
- no universal live debugger
- no autonomous remediation without review

## 3. Training

Open:

- [http://127.0.0.1:7860/training](http://127.0.0.1:7860/training)

What it should communicate:

- what just happened in the latest live triage
- whether the product is healthy and bounded
- what value the product is claiming for a pilot

Inspect:

- `Latest live triage`
- `Pilot scorecard dashboard`
- runtime host and pack coverage surfaces
- product health / governance posture

Expected:

- the same fresh incident appears in the training bridge
- the outcome, Guardian decision, and runtime posture are visible
- the page reads like operator learning plus pilot proof, not a raw metrics wall

## Approval Flow

From the incident detail page:

1. click `Approve runbook`
2. confirm Guardian changes state
3. confirm execution outcome becomes visible
4. return to `/training`
5. confirm the outcome is reflected in the latest live triage section

## The Core Story To Tell

Use this sentence:

**NEXUS reduces manual support-to-engineering relay by turning raw evidence into a runtime-aware, debugging-guided, review-ready case.**

Do not overclaim:

- universal debugger
- arbitrary environment reproduction
- autonomous production healing

## Related Docs

- [DEMO_CHEAT_SHEET.md](/Users/kunalkachru/Documents/nexus-v3/docs/DEMO_CHEAT_SHEET.md)
- [LIVE_DEMO_SPEAKER_NOTES.md](/Users/kunalkachru/Documents/nexus-v3/docs/LIVE_DEMO_SPEAKER_NOTES.md)
- [BUYER_PROOF_PACKAGE.md](/Users/kunalkachru/Documents/nexus-v3/docs/BUYER_PROOF_PACKAGE.md)
