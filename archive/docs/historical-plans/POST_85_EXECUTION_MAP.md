# NEXUS Post-85 Execution Map

Current as of 2026-06-15.

This document expands [backlog-86-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-86-plus.json) into concrete execution tasks so future loops can move through wedge strengthening and pilot conversion without random drift.

Use it together with:

- [backlog-86-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-86-plus.json)
- [docs/POST_85_WEDGE_STRENGTHENING_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_85_WEDGE_STRENGTHENING_PLAN.md)

## How To Use This Map

For each backlog item:

1. read the JSON item
2. read the matching execution-map section
3. complete backend and contract work first
4. complete UI work second
5. run targeted validation before the full gates
6. update docs before marking the item done

## Item 86: Third Outage Family — Deploy Regression / 5xx Spike

### Backend tasks

- add a third canonical incident fixture and live-path equivalent:
  - deploy regression / 5xx spike
  - likely affected service
  - suspected deploy window
  - likely owner team
  - customer-facing impact summary
- keep seeded/static and live incident semantics aligned
- add deploy-window and rollback-aware evidence cues without claiming runtime validation yet

### UI tasks

- expose the new outage class cleanly in the queue, incident, and training surfaces
- make the operator immediately understand why this differs from timeout and DB-pool incidents

### Validation tasks

- add API and app coverage for `INC003`
- verify browser flows can open and understand the new incident type

### Documentation tasks

- update demo and operator walkthrough references
- document where deploy-regression reasoning is inferred versus validated

## Item 87: Bounded REPLICA And TRACE Support For INC003

### Backend tasks

- add a curated runtime pack for deploy regression / 5xx spike
- define the replay condition and at least one validated mitigation path
- add bounded TRACE guidance for likely failing module or request path
- ensure packaged-app runtime claims remain verifiable through the runtime-host path

### UI tasks

- surface replay comparison and trace handoff for `INC003`
- make the runtime-backed versus inferred state explicit

### Validation tasks

- add runtime tests for the new pack
- verify packaged-app runtime behavior through Docker and smoke checks

### Documentation tasks

- update walkthroughs with `INC003` runtime and trace behavior
- keep the bounded nature of the pack explicit

## Item 88: LLM-Driven Triage Reasoning Upgrade

### Backend tasks

- strengthen triage generation so raw logs and live incidents produce better:
  - issue framing
  - likely owner
  - likely subsystem
  - customer impact statement
  - next investigation steps
  - uncertainty notes
- keep a truthfulness contract that distinguishes:
  - LLM-inferred
  - memory-backed
  - runtime-backed
- avoid hardcoded-feeling summaries for fresh incidents wherever product state already supports stronger inference

### UI tasks

- render richer triage reasoning without overwhelming the operator
- show confidence and uncertainty in a stable readable format

### Validation tasks

- add contract tests for triage evidence-posture fields
- verify fresh `nxs_...` incidents feel more adaptive while staying honest

### Documentation tasks

- update product and demo docs to explain the stronger LLM contribution model

## Item 89: Agent Deliberation Visibility And Reasoning Timeline

### Backend tasks

- expose a stable, presentation-safe reasoning timeline or contribution packet showing what each agent changed
- keep the output concise and product-readable rather than raw chain-of-thought

### UI tasks

- make the incident surface show:
  - what SENTINEL added
  - what PRISM refined
  - what REPLICA validated
  - what TRACE narrowed
  - why FORGE recommended the chosen action
- improve operator understanding of turning points in the case

### Validation tasks

- add browser checks for the new reasoning visibility
- ensure seeded and live incidents remain semantically aligned

### Documentation tasks

- update demo speaker notes and presentation guidance to use the new reasoning timeline

## Item 90: Pilot Conversion Kit For The Three-Outage Wedge

### Backend tasks

- ensure training and proof surfaces can reference all three flagship outage families
- expose any missing metrics or support-state summaries needed for pilot conversations

### UI tasks

- strengthen buyer and operator proof surfaces around:
  - outage-family coverage
  - value story
  - runtime-backed support state
  - engineering handoff readiness

### Validation tasks

- verify buyer-proof and training surfaces remain grounded in measured or honestly estimated values

### Documentation tasks

- update buyer proof, presentation pack, and operator demo flow to reflect the three-outage wedge

## Item 91: Final Wow-Effect UI Completion Across Core Surfaces

### Backend tasks

- minimal backend support only where presentation-critical surfaces need structured data tweaks

### UI tasks

- complete the premium polish pass across:
  - intake
  - incident
  - training
  - handoff/export
- improve visual continuity, hierarchy, and motion
- keep surfaces legible on desktop and mobile
- make the wow-effect feel intentional rather than decorative

### Validation tasks

- run browser verification and manual visual checks
- confirm the strongest demo path remains easy to explain

### Documentation tasks

- refresh presentation-facing docs or screenshots if the UI changes materially

## Item 92: Post-85 Wedge-Strengthening Checkpoint

### Backend tasks

- no major new product work unless validation uncovers a critical fix

### UI tasks

- tighten any wording or hierarchy issues discovered during verification

### Validation tasks

- run the full validation stack:
  - `pytest tests/ -q`
  - `npm run browser:verify`
  - `python demo.py`
  - `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh`
  - `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh`
- verify `INC001`, `INC002`, `INC003`, and a fresh live incident remain coherent

### Documentation tasks

- refresh `AGENTS.md`
- refresh `WORKING_STATE.md`
- refresh `docs/LOOPS_RUNBOOK.md`
- refresh owner-facing phase docs
- close the backlog cleanly before any broader post-92 roadmap work begins

## Recommended Execution Grouping

### Group 1: Outage-family expansion

- `86`
- `87`

### Group 2: LLM reasoning and agent legibility

- `88`
- `89`

### Group 3: Pilot conversion and presentation strength

- `90`
- `91`

### Group 4: Phase checkpoint

- `92`
