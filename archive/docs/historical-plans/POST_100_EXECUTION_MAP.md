# NEXUS Post-100 Execution Map

Current as of 2026-06-15.

This document expands [backlog-101-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-101-plus.json) into concrete execution tasks so future loops can move through FR2 without random drift.

Use it together with:

- [backlog-101-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-101-plus.json)
- [docs/POST_100_FIELD_PILOT_EXECUTION_AND_PROOF_AT_SCALE_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_100_FIELD_PILOT_EXECUTION_AND_PROOF_AT_SCALE_PLAN.md)

## How To Use This Map

For each backlog item:

1. read the JSON item
2. read the matching execution-map section
3. complete backend and contract work first
4. complete UI work second
5. run targeted validation before the full gates
6. update docs before marking the item done

## Item 101: Customer Log Intake Normalization v2

### Backend tasks

- improve parsing and normalization for messier tenant-provided logs
- add tenant-aware hints or bounded input-profile support where useful
- improve fallback behavior for partial or low-signal inputs

### UI tasks

- make unsupported or incomplete input quality visible at intake time
- show clearer intake-to-triage normalization results

### Validation tasks

- add fresh-input coverage beyond curated demo patterns
- verify intake remains understandable on weak evidence

### Documentation tasks

- update operator intake guidance and pilot usage notes

## Item 102: Coverage Matrix And Unsupported-Incident Downgrade Path

### Backend tasks

- define per-tenant support-state representation:
  - runtime-backed
  - inference-first
  - unsupported
- attach downgrade semantics to unsupported or weakly supported incidents

### UI tasks

- show per-tenant coverage matrix clearly
- make downgrade states explicit and actionable

### Validation tasks

- test support-state rendering and unsupported-case flows
- verify product does not bluff when runtime support is absent

### Documentation tasks

- document the supported wedge and downgrade behavior per tenant

## Item 103: Fresh-Incident Quality Evaluation Harness

### Backend tasks

- add a bounded review/evaluation harness for fresh incidents
- score issue framing, owner routing, next-step quality, and uncertainty quality
- capture reviewer feedback where helpful

### UI tasks

- expose enough quality-review context for operators or reviewers
- keep evaluation lightweight and bounded

### Validation tasks

- add tests for evaluation payloads and fresh-incident scoring structure
- verify product stays honest on low-confidence incidents

### Documentation tasks

- document how to evaluate fresh-incident quality during pilots

## Item 104: Pilot Scorecard Dashboard

### Backend tasks

- expose per-tenant pilot scorecard signals:
  - incidents handled
  - runtime-backed ratio
  - triage time saved
  - handoff completion
  - repeat-incident reuse

### UI tasks

- add a pilot scorecard view or section to training/admin surfaces
- keep scorecard legible to both buyers and operators

### Validation tasks

- verify scorecard signals remain grounded in measured or honestly estimated evidence

### Documentation tasks

- update proof and pilot conversation materials with scorecard usage

## Item 105: Case-Based Proof Export

### Backend tasks

- add exportable proof packaging based on real handled incidents
- support before/after case framing and evidence-backed value summaries

### UI tasks

- expose case-based proof export affordances where appropriate
- keep the export buyer-usable without weakening product honesty

### Validation tasks

- test export payload completeness and bounded claims

### Documentation tasks

- update buyer proof and presentation pack usage guidance

## Item 106: Engineering Handoff Trust v3

### Backend tasks

- strengthen repo-aware inspection briefs further
- improve next-step guidance and residual-risk framing
- make the engineering packet more concrete about what to inspect and why

### UI tasks

- improve the engineering handoff surface readability
- make inspect-first and evidence posture easier to scan

### Validation tasks

- verify handoff remains bounded and avoids universal debugging claims

### Documentation tasks

- update handoff examples and engineering-facing product explanation

## Item 107: Runtime Evidence Weighting v3

### Backend tasks

- deepen weighting between inference, memory, and runtime evidence
- improve recommendation posture on resolved, improved, and unvalidated cases
- tighten residual-risk and confidence semantics

### UI tasks

- make recommendation quality and evidence weighting more visible
- improve why-this-action-won clarity

### Validation tasks

- add ranking assertions and runtime-backed decision checks
- verify Docker path still tells the same story as the product UI

### Documentation tasks

- update truthfulness and buyer-proof references where needed

## Item 108: Pilot Operations Kit And FR2 Checkpoint

### Backend tasks

- no major new product work unless validation uncovers critical fixes

### UI tasks

- tighten any wording or workflow issues found during final validation

### Validation tasks

- run the full validation stack:
  - `pytest tests/ -q`
  - `npm run browser:verify`
  - `python demo.py`
  - `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh`
  - `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh`
- verify multi-tenant pilot surfaces, the three flagship incidents, and fresh incidents remain coherent

### Documentation tasks

- add the pilot operations kit:
  - tenant setup runbook
  - operator quickstart
  - weekly pilot review checklist
  - pilot closeout template
- refresh `AGENTS.md`
- refresh `WORKING_STATE.md`
- refresh `docs/LOOPS_RUNBOOK.md`
- close the backlog cleanly before any selective outage expansion phase begins

## Recommended Execution Grouping

### Group 1: Fresh input and support boundaries

- `101`
- `102`
- `103`

### Group 2: Proof and trust

- `104`
- `105`
- `106`
- `107`

### Group 3: Pilot operations and checkpoint

- `108`
