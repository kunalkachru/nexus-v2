# NEXUS Post-108 Execution Map

Current as of 2026-06-15.

This document expands [backlog-109-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-109-plus.json) into concrete execution tasks so future loops can move through the selective expansion phase without random drift.

Use it together with:

- [backlog-109-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-109-plus.json)
- [docs/POST_108_SELECTIVE_EXPANSION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_108_SELECTIVE_EXPANSION_PLAN.md)

## How To Use This Map

For each backlog item:

1. read the JSON item
2. read the matching execution-map section
3. complete backend and contract work first
4. complete UI work second
5. run targeted validation before the full gates
6. update docs before marking the item done

## Item 109: Auth Dependency Family Packet Across Seeded And Live Paths

### Backend tasks

- add the auth dependency family to seeded and live incident framing
- define buyer-legible issue-family, owner, and customer-path language
- keep support-state language honest before runtime pack support exists

### UI tasks

- expose the new family cleanly in incident and training surfaces
- keep the outage family readable without adding product clutter

### Validation tasks

- verify seeded and live auth-family incidents tell the same story
- confirm runtime-backed language does not appear before the pack lands

### Documentation tasks

- update demo and operator-facing wording for the new family

## Item 110: Bounded REPLICA And TRACE Support For Auth Dependency Family

### Backend tasks

- add the auth dependency runtime pack
- define replay outcome classes and mitigation ladder for the pack
- add a bounded TRACE inspection path for dependency boundary failures

### UI tasks

- surface REPLICA and TRACE details for the new family
- keep runtime-backed versus inferred-only posture obvious

### Validation tasks

- verify runtime replay and trace packet are visible and truthful
- run Docker-path validation for the packaged app

### Documentation tasks

- update product and demo docs with the bounded auth dependency story

## Item 111: Queue And Worker Backlog Family Packet Across Seeded And Live Paths

### Backend tasks

- add the queue or worker backlog family to seeded and live framing
- define owner, customer-path, and backlog-specific incident packet language
- keep fresh-incident downgrade language honest where evidence is weak

### UI tasks

- expose queue backlog framing in the core incident surfaces
- keep the product category visually coherent

### Validation tasks

- verify seeded and live queue-family incidents remain semantically aligned

### Documentation tasks

- update buyer and demo wording for the queue backlog story

## Item 112: Bounded REPLICA And TRACE Support For Queue And Worker Backlog Family

### Backend tasks

- add the queue or worker backlog runtime pack
- define replay comparison and mitigation ladder for the backlog pack
- add a bounded TRACE inspection path for backlog-processing failures

### UI tasks

- surface REPLICA and TRACE details for the backlog family
- keep runtime-backed posture visible and strict

### Validation tasks

- verify runtime replay and trace packet through tests and the Docker path

### Documentation tasks

- update docs with the bounded backlog debugging story

## Item 113: Coverage Matrix And Pilot Scorecard Extension For The Five-Family Wedge

### Backend tasks

- extend tenant coverage matrix to all five supported families
- extend pilot scorecard metrics and proof surfaces to the five-family wedge

### UI tasks

- make the widened wedge legible in settings, training, and buyer-facing surfaces

### Validation tasks

- verify support-state and proof surfaces stay evidence-backed

### Documentation tasks

- refresh buyer-proof and presentation materials with five-family coverage

## Item 114: Fresh-Incident Routing And Owner Inference Calibration Across The Five-Family Wedge

### Backend tasks

- improve routing and owner inference across five families
- calibrate uncertainty language when multiple families overlap

### UI tasks

- expose routing quality and uncertainty without creating clutter

### Validation tasks

- verify fresh incidents stay honest on overlap and weak evidence

### Documentation tasks

- update operator and demo guidance for the widened wedge

## Item 115: Buyer And Demo Material Refresh For The Five Supported Outage Families

### Backend tasks

- no major backend work unless validation uncovers a truthfulness issue

### UI tasks

- tighten buyer-facing and demo-facing wording if product surfaces need polish

### Validation tasks

- confirm the five-family demo story is understandable and still narrow

### Documentation tasks

- refresh buyer, demo, and GTM material to match the widened wedge

## Item 116: Five-Family Wedge Checkpoint And Control-Doc Refresh

### Backend tasks

- no new product work unless validation uncovers a blocking issue

### UI tasks

- tighten wording or labels found during final validation

### Validation tasks

- run the full validation stack:
  - `pytest tests/ -q`
  - `npm run browser:verify`
  - `python demo.py`
  - `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh`
  - `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh`
- verify all five families remain bounded and truthful in seeded and live paths

### Documentation tasks

- refresh `AGENTS.md`
- refresh `WORKING_STATE.md`
- refresh `docs/LOOPS_RUNBOOK.md`
- close the backlog cleanly before any ops-maturity backlog begins

## Recommended Execution Grouping

### Group 1: New family framing

- `109`
- `111`

### Group 2: Runtime and trace support

- `110`
- `112`

### Group 3: Wedge calibration and checkpoint

- `113`
- `114`
- `115`
- `116`
