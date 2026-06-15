# NEXUS Post-92 Execution Map

Current as of 2026-06-15.

This document expands [backlog-93-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-93-plus.json) into concrete execution tasks so future loops can move through pilot conversion and technical proof deepening without random drift.

Use it together with:

- [backlog-93-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-93-plus.json)
- [docs/POST_92_PILOT_CONVERSION_AND_TECHNICAL_PROOF_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_92_PILOT_CONVERSION_AND_TECHNICAL_PROOF_PLAN.md)

## How To Use This Map

For each backlog item:

1. read the JSON item
2. read the matching execution-map section
3. complete backend and contract work first
4. complete UI work second
5. run targeted validation before the full gates
6. update docs before marking the item done

## Item 93: Tenant Onboarding v2 And Pilot Setup Kit

### Backend tasks

- deepen tenant bootstrap to include pilot-specific readiness:
  - supported outage families
  - owner mappings
  - downstream destinations
  - reviewer expectations
  - pack availability
- define missing-readiness semantics clearly

### UI tasks

- show pilot-readiness status as a clear operator/admin state
- make setup gaps actionable instead of implicit

### Validation tasks

- test complete and incomplete pilot-setup states
- verify settings/training surfaces explain readiness clearly

### Documentation tasks

- update operations and pilot setup docs
- document the minimum viable tenant path for a real pilot

## Item 94: Pilot ROI Instrumentation And Case-Based Proof Capture

### Backend tasks

- make ROI and case-proof capture more durable per tenant and per incident family
- expose metrics and evidence used in buyer or pilot proof surfaces

### UI tasks

- strengthen training/proof surfaces around:
  - relay reduction
  - triage quality
  - runtime-backed coverage
  - handoff completion

### Validation tasks

- verify product claims stay tied to measured or honestly estimated values
- add tests around proof-surface payloads where needed

### Documentation tasks

- update buyer proof and pilot conversation materials

## Item 95: Delivery And Feedback Closure v2

### Backend tasks

- deepen downstream delivery lifecycle and engineering feedback capture
- make the post-handoff lifecycle more complete and auditable

### UI tasks

- improve visibility into:
  - sent
  - acknowledged
  - acted on
  - rejected
  - needs follow-up

### Validation tasks

- verify delivery and outcome states remain coherent in incident and training surfaces

### Documentation tasks

- update operational guidance for post-handoff follow-through

## Item 96: Operator Workflow Simplification And Role Clarity v2

### Backend tasks

- minimal backend work unless workflow simplification requires extra surface contracts

### UI tasks

- simplify the operator path from intake to review to handoff
- clarify role-specific views and next actions
- reduce friction and explanation debt in repeated pilot use

### Validation tasks

- verify operator flow remains readable in browser checks
- test role-aware behavior where impacted

### Documentation tasks

- update operator runbook and demo walkthroughs

## Item 97: Repo-Aware Debugger Handoff Deepening

### Backend tasks

- strengthen trace-to-repo cues:
  - likely modules
  - likely owners
  - likely inspection files or boundaries
- keep the handoff bounded and honest

### UI tasks

- make the engineering packet feel more actionable for a real engineering reviewer
- improve "inspect here first" readability

### Validation tasks

- verify trace packets stay grounded and do not overclaim universal debugging

### Documentation tasks

- update technical proof messaging and handoff examples

## Item 98: Runtime Evidence Weighting And Mitigation Confidence v2

### Backend tasks

- deepen mitigation ranking so runtime deltas more strongly drive recommendation posture
- distinguish:
  - inferred best action
  - runtime-improved action
  - runtime-resolved action
- improve residual-risk framing

### UI tasks

- show why the chosen action won more clearly
- make confidence and residual-risk language easier to understand

### Validation tasks

- add reasoning and ranking assertions
- verify runtime-backed cases feel more decision-driven

### Documentation tasks

- update release and buyer-facing truthfulness references where needed

## Item 99: Fresh-Incident Triage Quality Calibration And Evaluation

### Backend tasks

- improve evaluation of fresh-incident triage quality
- calibrate issue framing, owner routing, next-step quality, and uncertainty language
- add a bounded evaluation harness or reference cases where useful

### UI tasks

- keep fresh-incident reasoning readable and explicitly bounded
- show where confidence is lower on non-curated incidents

### Validation tasks

- add tests covering better fresh-incident variation and evidence-posture output
- verify product does not regress into canned summaries or overclaiming

### Documentation tasks

- update owner-facing docs about how fresh incidents should be interpreted during pilots

## Item 100: Post-92 Pilot Conversion And Technical Proof Checkpoint

### Backend tasks

- no major new product work unless validation uncovers critical fixes

### UI tasks

- tighten any wording or hierarchy issues discovered during validation

### Validation tasks

- run the full validation stack:
  - `pytest tests/ -q`
  - `npm run browser:verify`
  - `python demo.py`
  - `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh`
  - `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh`
- verify the three flagship incidents and a fresh live incident remain coherent

### Documentation tasks

- refresh owner-facing phase docs
- refresh `AGENTS.md`
- refresh `WORKING_STATE.md`
- refresh `docs/LOOPS_RUNBOOK.md`
- close the backlog cleanly before any broader outage-expansion plan begins

## Recommended Execution Grouping

### Group 1: Pilot setup and proof

- `93`
- `94`
- `95`

### Group 2: Workflow simplification and engineering trust

- `96`
- `97`
- `98`

### Group 3: Fresh-incident quality and checkpoint

- `99`
- `100`
