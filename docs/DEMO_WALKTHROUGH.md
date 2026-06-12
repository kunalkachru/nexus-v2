# NEXUS v2 Full Manual Browser Walkthrough

Current as of 2026-06-12.

This is the full manual walkthrough for the current NEXUS product story.

Use it when you want to:

- understand the product from the outside in
- validate the end-to-end flagship use case
- present the current shipped workflow
- explain how the product reduces manual support escalation work

## Current Validation Baseline

The current validated baseline for this walkthrough is:

- `pytest tests/ -q` -> `141 passed`
- `npm run browser:verify` -> `11 passed`
- `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` -> passes
- `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` -> passes

## What This Walkthrough Is Proving

The walkthrough is built around one claim:

**NEXUS turns noisy production evidence into a triaged, investigated, remediation-ready case before one final human review point.**

The walkthrough should make these things obvious:

1. a support engineer does not have to manually relay logs across multiple tiers
2. the system identifies likely issue family and likely ownership
3. the system retrieves prior operational context
4. the system prepares a remediation packet
5. Guardian is the final review point before action

## Flagship Use Case

Use this scenario as the anchor for the walkthrough:

**customer-facing checkout outage caused by timeout and retry amplification after dependency degradation and recent deploy ambiguity**

This is the strongest case because it has:

- clear business impact
- believable logs
- a meaningful investigation path
- room for memory-backed reasoning
- a strong future fit for reproduction and debugging

## What The Product Is Today

NEXUS is currently a support triage and incident investigation product with six visible investigation stages:

- `SENTINEL` — incident classification
- `PRISM` — root cause diagnosis
- `REPLICA` — bounded reproduction layer with optional runtime replay
- `TRACE` — investigation depth and developer handoff
- `FORGE` — runbook selection with runtime evidence weighting
- `GUARDIAN` — safety review that distinguishes runtime-backed evidence from scaffold-backed inference

The six-stage flow forms a complete incident response pipeline from classification through remediation readiness, while keeping runtime replay explicitly bounded and optional.

For packaged local demos, runtime replay can now be delegated to a private `runtime-host` service so the product can stay truthful even when the main app container is not Docker-capable.

## Local Setup

### Preferred: Docker

```bash
./scripts/docker_fresh.sh
```

For the packaged relay demo where the UI stays on `:7860` but replay is delegated to a Docker-capable sidecar, use:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

### Direct server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Main Screens To Walk Through

The most important screens are:

1. `/inputs`
2. created `/incident?nexus_incident_id=nxs_...`
3. `/training`

Secondary supporting screens:

- `/queue`
- `/history`
- `/replay`

## 1. Inputs

Open:

- [http://127.0.0.1:7860/inputs](http://127.0.0.1:7860/inputs)

### What this screen should communicate

- this is the front door for messy production evidence
- the raw-log path is the clearest and most important path
- the product is designed for real support-triage intake, not toy inputs

### What to do

1. confirm the raw-log area starts empty
2. click `Load example logs`
3. confirm a realistic outage sample appears
4. click `Submit raw logs`

### Expected outcome

- the system creates a new `nxs_...` incident
- the browser redirects into the incident detail screen
- the incident feels like a structured case, not just dumped text

## 2. Incident Detail

Open the created incident or use:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC001](http://127.0.0.1:7860/incident?nexus_incident_id=INC001)

### What this screen should communicate

- the system has already reduced manual relay work
- the operator is looking at a prepared triage and investigation packet
- Guardian is the final human review point

### What to look for

- incident title and service
- severity and issue framing
- support-triage handoff story
- memory-grounded investigation
- bounded debugger packet for the timeout/retry outage
- proposed action and Guardian posture

### What the six-agent flow should mean

- `SENTINEL`: likely severity, likely service, likely issue family
- `PRISM`: evidence correlation, recent change analysis, and prior issue retrieval
- `REPLICA`: bounded reproduction layer that can validate the diagnosis and mitigation effectiveness when runtime replay is enabled
- `TRACE`: investigation depth, suspected modules, and developer handoff packet
  TRACE owner cues are bounded to a checked-in flagship ownership map, not a universal repository index.
- `FORGE`: action preparation, mitigation comparison weighted by measured runtime evidence when available and scaffold-only inference otherwise
- `GUARDIAN`: review posture, risk posture that distinguishes validated runtime evidence from scaffold-only inference, and final approval or rejection

### Runtime Evidence Flow (REPLICA → FORGE → GUARDIAN)

The runtime evidence narrative connects three stages, but only part of it is measured by default:

1. **REPLICA** maps the incident to a bounded sandbox and, when runtime replay is enabled, reproduces the failure and tests mitigations. It produces:
   - `best_mitigation_outcome_class`: `resolved` / `improved` when replay ran, `inferred_only` otherwise
   - `runtime_comparison_summary`: measured baseline-vs-mitigation text when replay ran, scaffold-only ranking text otherwise
   - `mitigation_comparison`: explicit baseline, selected mitigation, and runner-up mitigation packet for the incident UI and downstream reasoning
   - `runtime_provenance`: whether evidence came from direct replay on the current host or delegated replay through the runtime host

2. **FORGE** uses the outcome class to weight runbook selection:
   - reasoning cites the mitigation outcome: "resolved," "improved," or "inferred"
   - candidate fixes ranked by action overlap with the tested mitigation

3. **GUARDIAN** enriches its safety posture with the current evidence mode:
   - a validated runtime clause only when replay executed
   - scaffold-only inference wording otherwise
   - approval confidence can rise when measured runtime evidence validates the hypothesis

### What the runtime flow validates

- the diagnosis hypothesis maps cleanly into one bounded reproduction path
- when runtime replay is enabled, the proposed mitigation can be measured against the failure signature
- when the packaged app is running in Docker, the same replay can be delegated to the runtime host instead of failing inside the app container
- once a live `nxs_...` incident runs replay, the measured REPLICA and TRACE packet persists across refresh instead of collapsing back to scaffold-only inference
- after that refresh, FORGE reasoning, GUARDIAN posture, memory ranking, and task summaries stay anchored to the persisted replay packet instead of rebuilding from scaffold-only language
- TRACE cites the suspected file path and the checked-in ownership-map source that produced the owner handoff for the flagship packs
- the selected mitigation can be explained against a visible runner-up instead of feeling arbitrary
- escalation to a human reviewer includes evidence-backed confidence in the action

### What is implemented now vs still theoretical

Implemented now:

- `REPLICA` has two real bounded runtime packs for the flagship outage classes
- `TRACE` has a bounded stack-path packet for both flagship outages
- `TRACE` also has one real debugger-style packet for `INC001` / timeout-retry amplification only
  - it references concrete checkpoint variables: `retry_count`, `timeout_budget_ms_remaining`, and `circuit_state`
  - it is tied to the curated pack `checkout-python-fastapi-auth-redis-v1`
- the mitigation ladder is visible as primary step, fallback step, and stop condition

### Bounded debugger flow explained

The INC001 debugger packet is **not** a universal live debugger. It is:
- **Bounded to one curated pack**: `checkout-python-fastapi-auth-redis-v1` only
- **Bounded to one outage class**: timeout/retry amplification only
- **Ordered as a debugging flow**: three checkpoints in sequence with expected state transitions
- **Meant for manual execution**: an engineer breaks in the right place and watches three variables move through expected states

This debugger packet guides the engineer to:
1. Reproduce the baseline failure via bounded replay
2. Break in `apply_retry_policy` and watch `retry_count` respect its cap
3. Step to `await_upstream_auth` and verify `timeout_budget_ms_remaining` stays positive  
4. Inspect `circuit_state` and confirm it opens once the threshold is crossed

The difference from a true debugger:
- **True debugger**: can debug any stack, any repository, any failure mode, with live breakpoints and expressions
- **Bounded debugger**: applies only to this specific curated pack and failure class; relies on pre-calculated checkpoint locations and expected transitions

Still theoretical / not shipped:

- arbitrary environment reproduction outside the curated packs
- universal code debugging across any stack or repository
- live breakpoint attachment into arbitrary production services
- autonomous multi-step production remediation without a human review point

### What to validate

1. read the top summary and confirm the screen feels like a triage console
2. inspect the agent handoff and confirm the workflow is understandable
3. inspect memory and related history if shown
4. inspect the bounded debugger packet and confirm it is explicitly limited to the curated timeout/retry pack
5. inspect the proposed action
6. inspect Guardian’s review language

### Approval path

1. click `Approve runbook`
2. confirm Guardian changes to approved
3. confirm execution moves to executed
4. confirm the outcome is visible without hunting

### What success looks like

- you can explain the likely issue and likely next action quickly
- you can explain how the product reduced manual escalation work
- the screen feels like a real operator workspace, not an architecture demo

## 3. Training

Open:

- [http://127.0.0.1:7860/training](http://127.0.0.1:7860/training)

### What this screen should communicate

- what the latest live triage was
- how the runtime is behaving
- how the broader learning and memory layer is evolving

### What to validate

1. confirm the page shows the latest live triage in this browser when available
2. confirm the navigation pills work
3. confirm the runtime summary is understandable
4. confirm the page distinguishes:
   - latest live run
   - runtime health
   - broader learning baseline

### What success looks like

- the page closes the loop between one incident and future improvement
- it does not feel like an unrelated analytics screen

## 4. Queue

Open:

- [http://127.0.0.1:7860/queue](http://127.0.0.1:7860/queue)

Validate:

- incidents feel operational and actionable
- clicking one opens a populated incident detail page
- the queue feels like a triage backlog, not a placeholder list

## 5. History

Open:

- [http://127.0.0.1:7860/history](http://127.0.0.1:7860/history)

Validate:

- older incidents open quickly
- history behaves like deterministic review mode by default
- history feels like operational memory, not a dead archive

## 6. Replay

Open:

- [http://127.0.0.1:7860/replay](http://127.0.0.1:7860/replay)

Validate:

- scenarios are understandable
- replay feels like a validation and learning tool
- the feature supports the future reproduction story naturally

## Manual Verification Checklist

Use this as the compact pass/fail list:

1. `/inputs` creates a fresh incident
2. incident detail explains the support-triage case clearly
3. Guardian is visibly the final review point
4. approval updates the state and outcome visibly
5. `/training` maps the live run correctly
6. `/history` opens older incidents quickly
7. `/queue` and `/replay` remain coherent

## What Not To Overclaim During The Walkthrough

Do not claim that the current shipped product already:

- reproduces arbitrary environments
- universally debugs code
- executes production remediations autonomously

Do say:

- the current product proves the support-triage workflow
- memory and governance are already visible
- bounded reproduction is real today for two flagship outage classes
- one bounded debugger packet is real today for the timeout/retry outage class
- broader reproduction and debugging are still the next major product expansions

## Related Docs

- [README.md](/Users/kunalkachru/Documents/nexus-v3/README.md)
- [FINAL_SUBMISSION_GUIDE.md](/Users/kunalkachru/Documents/nexus-v3/docs/FINAL_SUBMISSION_GUIDE.md)
- [LIVE_DEMO_SPEAKER_NOTES.md](/Users/kunalkachru/Documents/nexus-v3/docs/LIVE_DEMO_SPEAKER_NOTES.md)
- [SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md)
