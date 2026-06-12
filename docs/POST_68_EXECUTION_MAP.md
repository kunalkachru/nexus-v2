# NEXUS Post-68 Execution Map

Current as of 2026-06-12.

This document expands [backlog-69-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-69-plus.json) into real implementation tasks and subtasks so future loops can execute faster and more consistently.

Use it together with:

- [backlog-69-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-69-plus.json)
- [docs/POST_68_MARKET_READINESS_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_68_MARKET_READINESS_PLAN.md)

## How To Use This Map

For each backlog item:

1. read the JSON item first
2. read the matching section in this document
3. implement backend work first
4. land UI changes second
5. run targeted tests before the full suite
6. run browser and Docker validation when listed
7. update docs before marking the item done

The point is to prevent loops from wasting time rediscovering scope.

## Item 69: Pilot Intake Connectors And Durable Case Lifecycle

### Goal

Make intake and case progression feel like a real support workflow, not only a demo incident generator.

### Backend tasks

- define the pilot case-lifecycle states:
  - `created`
  - `triaged`
  - `investigating`
  - `handoff_prepared`
  - `awaiting_review`
  - `approved`
  - `executed`
  - `closed`
- add lifecycle persistence to the existing incident record or normalized evidence path
- add or tighten a second realistic intake path beyond the current raw-log demo path
- ensure queue and history APIs return the lifecycle state and timestamps consistently

### UI tasks

- update `/inputs` so the supported pilot intake paths are obvious
- update `/queue` to show lifecycle state as an operator-facing work-state, not just severity
- update `/history` to show closure and outcome progression
- ensure incident detail shows where the case is in the lifecycle without extra narration

### Validation tasks

- add API assertions for lifecycle persistence
- add app tests for both intake paths
- add browser checks covering:
  - intake
  - queue visibility
  - history visibility
  - incident detail lifecycle rendering

### Manual UI checks

- submit a raw-log intake and verify lifecycle progression
- submit the second intake shape and verify the same progression
- confirm the queue and history screens tell a coherent work-item story

### Documentation tasks

- update `docs/DEMO_WALKTHROUGH.md` for the new intake options
- update any pilot-facing intake notes once the supported paths are fixed

## Item 70: Real Downstream Handoff Actions For Engineering Workflows

### Goal

Turn export-only handoff into at least one real downstream send action.

### Backend tasks

- choose the first real delivery target:
  - recommended first choice: GitHub issue creation
  - second choice: Slack escalation draft or send
- build a bounded send endpoint using the existing handoff packet as the source artifact
- persist delivery target, delivery status, timestamp, and failure reason
- make sure runtime-backed vs inferred evidence posture survives the downstream payload

### UI tasks

- add a real send action in incident detail next to the existing handoff/export area
- show send status:
  - pending
  - delivered
  - failed
- show destination metadata in the case record after send
- prevent the send affordance from looking like a generic mock action

### Validation tasks

- add app tests for successful and failed send flows
- add API contract coverage for delivery status fields
- add browser checks for the send action and delivery state rendering

### Manual UI checks

- send one case to the chosen target
- verify the incident screen shows target and status
- verify the downstream artifact preserves evidence labels and Guardian posture

### Documentation tasks

- update `docs/POST_68_MARKET_READINESS_PLAN.md` with the chosen first delivery target
- document what is truly integrated versus still export-only

## Item 71: Tenant-Specific Ownership And Repository Mapping

### Goal

Make owner and repo cues feel customer-real instead of mostly demo-real.

### Backend tasks

- define tenant mapping inputs for:
  - service owner
  - escalation team
  - repository
  - code-owner slug
- feed those mappings into triage summary and TRACE packet generation
- keep a safe fallback path when tenant mappings are incomplete
- expose mapping provenance in payloads so the UI can say whether a cue is tenant-mapped or fallback

### UI tasks

- show owner/repo provenance in incident detail and training surfaces
- update TRACE handoff blocks so tenant-mapped repo hints are visible
- keep fallback cues usable without overclaiming them as customer-configured

### Validation tasks

- add tests covering mapped and fallback owner resolution
- add API assertions for provenance labels
- add browser checks that mapped cues render differently from fallback cues

### Manual UI checks

- inspect one case with tenant mapping enabled
- inspect one case using fallback behavior
- confirm the difference is obvious and honest

### Documentation tasks

- update `docs/CURATED_PACK_CONTRACT.md` or adjacent ownership docs if the mapping contract changes
- document the fallback-vs-mapped distinction for owner cues

## Item 72: Engineering Feedback Loop And Outcome Ingestion

### Goal

Make engineering handoff bidirectional so outcomes come back into NEXUS.

### Backend tasks

- define a bounded feedback model:
  - accepted
  - edited
  - rejected
  - resolved
  - reopened
- persist feedback entries against the case record
- feed engineering outcome back into:
  - execution outcome
  - memory ranking
  - ROI metrics substrate
- distinguish internal execution outcome from external engineering confirmation

### UI tasks

- add outcome provenance in incident detail
- add engineering-response visibility to training or audit surfaces
- make reopen or rejection states visible so the system does not look falsely optimistic

### Validation tasks

- add app tests for each feedback state
- add API contract coverage for engineering outcome payloads
- add browser checks for feedback visibility and provenance

### Manual UI checks

- simulate one accepted engineering handoff
- simulate one rejected or edited handoff
- confirm the incident and training surfaces reflect the outcome differences

### Documentation tasks

- update `docs/DEMO_WALKTHROUGH.md` with the new feedback loop
- document what counts as engineering-confirmed versus internal-only outcome

## Item 73: Admin Controls For Packs, Policies, And Destinations

### Goal

Add bounded administration so the pilot is operable without code edits for every change.

### Backend tasks

- define an admin-readable config model for:
  - enabled packs
  - approval policies
  - delivery targets
  - runtime-host usage
- expose that config through safe product-facing endpoints
- support enable/disable flows for at least some of those controls
- keep unsupported settings clearly marked as code-managed

### UI tasks

- upgrade `/settings` or a training-adjacent view into a real admin surface
- show active packs, policy posture, and handoff destinations
- make toggles or selectors honest about whether they are editable or read-only

### Validation tasks

- add tests for admin state reads and any bounded updates
- add browser checks for settings visibility and control state
- verify the admin surface does not regress the existing operator flows

### Manual UI checks

- open settings and inspect active packs, policies, and destinations
- change one bounded setting if supported
- verify the product reflects the changed state

### Documentation tasks

- update `docs/OPERATIONS.md`
- document which admin functions are truly product-managed and which still require code/config edits

## Item 74: Operator ROI And Buyer-Value Metrics V2

### Goal

Make the buyer value legible in product terms, not only technical terms.

### Backend tasks

- define ROI metrics such as:
  - relay steps reduced
  - triage time saved
  - replay reuse
  - approval turnaround
  - engineering handoff conversion
- compute metrics from case history, replay, approval, and feedback data
- distinguish measured values from estimated values in the data model

### UI tasks

- extend `/training` or equivalent summary surfaces with buyer-readable metrics
- make the metrics understandable without needing engineering context
- label estimated vs measured clearly

### Validation tasks

- add tests for ROI calculation helpers
- add API assertions for measured/estimated flags
- add browser checks for the metrics surface and labels

### Manual UI checks

- verify that at least one metric is driven by real case history
- verify that estimated metrics are visibly marked
- confirm the surface tells a buyer story, not just a dashboard story

### Documentation tasks

- update `docs/PRODUCT_STRATEGY_AND_GTM.md`
- add a short explanation of which buyer metrics are measured today versus still directional

## Item 75: One Repo-Aware Debugger Handoff For The Pilot Environment

### Goal

Move one debugger flow from generic curated-pack guidance to a believable engineering brief for one real environment.

### Backend tasks

- choose one pilot outage class:
  - recommended first choice: `INC001`
- choose one tenant-aware repo mapping target
- extend TRACE output to include:
  - tenant-mapped repo
  - first file to inspect
  - likely owner
  - function-level debugging path
  - replay provenance
- preserve unsupported behavior for all non-pilot classes

### UI tasks

- strengthen the debugger/handoff block in incident detail
- make the pilot repo-aware path visually distinct from generic bounded fallback
- ensure exports use the repo-aware packet by default for the chosen pilot class

### Validation tasks

- add tests covering repo-aware and fallback debugger packet generation
- add API assertions for debugger provenance and repo-mapped cues
- add browser checks that the repo-aware debugger brief renders correctly
- run Docker-path validation because this item still relies on runtime-backed replay provenance

### Manual UI checks

- open the chosen pilot incident
- confirm the debugger packet names real repo/file/owner cues
- confirm non-pilot cases remain explicitly bounded and fallback-shaped

### Documentation tasks

- update `docs/DEMO_WALKTHROUGH.md`
- update `docs/POST_68_MARKET_READINESS_PLAN.md` once the first pilot debugger target is real

## Item 76: One Tenant-Specific Runtime Pack Upgrade For The Pilot Environment

### Goal

Upgrade one runtime pack so reproduction feels materially closer to one real environment.

### Backend tasks

- choose one flagship outage and one tenant-specific variant
- decide whether to:
  - extend the current curated pack
  - add a pilot-only pack variant
- encode the tenant-specific differences that matter:
  - timeout thresholds
  - retry behavior
  - pool sizing
  - dependency latency pattern
  - traffic profile assumptions
- expose pack provenance so the UI can say whether the generic or pilot-specific pack ran

### UI tasks

- show when the pilot pack is selected instead of the generic curated pack
- explain why the pilot pack is closer to reality
- keep generic-pack UX intact for all non-pilot cases

### Validation tasks

- add runtime tests for pack selection and repeatability
- add API assertions for pack provenance
- add browser checks for pack identity and comparison rendering
- run Docker-path smoke because this item directly changes runtime-pack behavior

### Manual UI checks

- trigger replay on the pilot case
- verify the UI names the pilot pack clearly
- verify the trust or provenance surface explains why this pack is more environment-specific

### Documentation tasks

- update `docs/CURATED_PACK_CONTRACT.md`
- document the pilot-pack boundary clearly so it is not mistaken for broad multi-tenant support

## Recommended Loop Grouping

To move fast without compounding too much risk, use these execution groups:

### Group 1: Workflow readiness

- `69`
- `70`
- `72`

Reason:
- these make the case lifecycle and engineering handoff real

### Group 2: Tenant realism

- `71`
- `73`
- `74`

Reason:
- these make the pilot workflow look and behave like a customer-specific product

### Group 3: Technical depth

- `75`
- `76`

Reason:
- these deepen the debugger and reproduction story only after the workflow layer is usable

## Suggested Future Loop Prompt Add-On

When this phase becomes active, add this to the loop prompt:

```text
Read docs/POST_68_EXECUTION_MAP.md after reading backlog-69-plus.json.
For the current item, complete backend tasks, then UI tasks, then validation tasks, then documentation tasks in that order.
Do not mark the item done until the manual UI checks are also described in the final checkpoint notes.
```
