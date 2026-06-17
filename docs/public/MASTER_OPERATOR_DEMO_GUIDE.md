# NEXUS Master Operator Demo Guide

Current as of 2026-06-17 (Updated: Test baselines and database path corrected)

This is the single document to use when you want to:

- set up the product locally
- understand what NEXUS actually does
- walk every major screen in the right order
- test the main functionality manually
- prepare to demo the product truthfully to buyers, pilot users, or internal reviewers

Use this guide as the main operating document. The other public docs are supporting material, not the primary walkthrough.

If you only want the fastest truthful live path, use:

`/queue -> flagship seeded incident -> Inspect intake -> /inputs -> guided demo bundle -> fresh nxs incident -> /training -> /settings`

## 1. What NEXUS Is

NEXUS is an **AI-assisted support-to-engineering investigation product** for recurring customer-facing application outages.

The product is designed to reduce the manual relay loop between support and engineering:

- noisy logs and incident evidence go in
- a structured investigation packet comes out
- one governed human review point remains before action

The shipped workflow is:

`SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

## 2. What Problem The Product Solves

The core problem is:

**too many people touch the same outage before a confident next action exists.**

Typical support-triage pain looks like this:

1. support receives raw logs or alerts
2. someone guesses likely ownership
3. someone else searches prior incidents manually
4. engineering receives a weak escalation
5. the case gets re-investigated from scratch

NEXUS compresses that relay into one workspace.

## 3. What Is Real Today

Real today:

- fresh log intake and normalization posture
- memory-backed triage and investigation
- bounded runtime replay for curated outage packs
- bounded debugging and engineering handoff packets
- runtime-aware mitigation ranking
- explicit governance and approval
- engineering export, delivery, audit, and pilot proof surfaces

Still bounded:

- reproduction only works for curated packs
- TRACE is not a universal debugger
- the product is not a universal incident-response platform
- execution remains governed and human-approved

## 4. Current Supported Outage Families

The current five-family wedge is:

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike
4. `INC005` queue / worker backlog affecting transaction completion
5. `INC007` auth dependency slowdown / token validation failures

For demos, use:

- seeded flagship story: `INC001`
- seeded second story: `INC002`
- breadth proof: `INC003`, `INC005`, `INC007`
- fresh-log stakeholder story 1: `Checkout timeout / retry amplification`
- fresh-log stakeholder story 2: `DB pool exhaustion / session leak`

## 5. Before You Start

### Recommended environment

Use the packaged Docker path, because this is the most truthful way to evaluate the shipped product:

```bash
export OPENAI_API_KEY=your_key_here
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

### Why the OpenAI key matters

If `OPENAI_API_KEY` is set:

- the product can use live model-backed reasoning where supported
- your review is closer to the intended buyer-demo experience

If `OPENAI_API_KEY` is not set:

- the product still works
- some reasoning will stay deterministic or fallback-oriented
- the demo is still valid, but less representative of the strongest product story

## 6. Optional Pre-Demo Validation

Run these if you want a confidence pass before reviewing:

```bash
pytest tests/ -q
npm run browser:verify
python demo.py
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

Expected baseline:

- `pytest tests/ -q` -> `410 passed` (76 core + 334 production readiness/load testing/DR/ops training tests)
- `npm run browser:verify` -> `16 passed`
- `python demo.py` -> passes
- Docker smoke path -> passes

## 7. The Best Review Order

Review the product in this order:

1. `/queue`
2. `/inputs`
3. `/incident?nexus_incident_id=INC001`
4. `/incident?nexus_incident_id=INC002`
5. `/incident?nexus_incident_id=INC003`
6. `/training`
7. `/settings`
8. `/history`
9. `/replay`

This order mirrors how a buyer or operator should understand the system:

- first the problem
- then intake
- then flagship incident handling
- then breadth
- then value, health, governance, and archive surfaces

Important:

- this is the **review order**
- it is **not always the direct clickable order from the current page**
- in the shipped UI, `/inputs` is reached through the incident workspace, not directly from the queue top nav

Use the exact UI path instructions in each step below rather than assuming every route is directly linked from the current screen.

## 8. Screen Map

| Route | Purpose | What it should prove | Next route |
|---|---|---|---|
| `/queue` | landing and focal-incident selection | this is an operating room, not a dashboard zoo | open seeded incident first, then go to `/inputs` through `Inspect intake` if needed |
| `/inputs` | noisy evidence intake | raw logs become a shaped case | fresh `nxs_...` incident |
| `/incident?...` | core investigation workspace | one structured case packet replaces manual relay | `/training` |
| `/training` | proof, health, ROI, runtime, learning | the product is measurable and operationally bounded | `/settings` |
| `/settings` | trust, readiness, onboarding, runtime host | this is deployable and governed, not only attractive | `/history` |
| `/history` | reusable operational memory | prior incidents are first-class memory | seeded incident review |
| `/replay` | deterministic scenario rehearsal | known failures can be rehearsed repeatedly | seeded or fresh incident |

## 9. Step-By-Step Product Review

## Step 1: Open Command Center

Open:

- [http://127.0.0.1:7860/queue](http://127.0.0.1:7860/queue)

### What this screen is doing

This is the operating-room landing page. It should communicate:

- one focal incident is active
- the rest of the queue exists but stays secondary
- the specialist crew is visible and legible

### What to look for

- header navigation:
  - `Command Center`
  - `Incident Detail`
  - `Learning & Controls`
- hero copy about turning support chaos into one focused operating room
- current focal incident, current stage, urgency, and response clock
- the specialist crew strip:
  - `SENTINEL`
  - `PRISM`
  - `FORGE`
  - `GUARDIAN`
- compact queue rail showing multiple incidents

### Expected response

You should feel that:

- the product has a clear focal case
- agent roles are understandable without explanation
- the queue does not dominate the experience

### How to navigate from here

There is **no direct `/inputs` link on the queue page top navigation**.

If you want to go to intake through the UI:

1. click `Open incident detail`
2. wait for the incident workspace to open
3. click `Inspect intake`
4. you will land on `/inputs`

Expected transition cue:

- the app now shows a brief route-opening state such as `Opening incident detail...` or `Opening input channels...` while preserving context for the next screen

If you want to jump straight to the flagship seeded incident:

1. click `Open incident detail`

### Where to go next

- intake path through the UI:
  - `/queue` -> `Open incident detail` -> `Inspect intake` -> `/inputs`
- flagship incident path through the UI:
  - `/queue` -> `Open incident detail` -> `INC001`

## Step 2: Open Inputs

Recommended UI path:

- from `/queue`, click `Open incident detail`
- from the incident page, click `Inspect intake`
- expect a short `Opening input channels...` transition state before `/inputs` renders

Direct URL fallback:

- [http://127.0.0.1:7860/inputs](http://127.0.0.1:7860/inputs)

### What this screen is doing

This screen proves that NEXUS starts with messy support evidence, not prompt theater.

### What to look for

- hero copy about starting with the mess
- the `Guided demo bundles` block
- the `Bundle proof` panel
- supported channels and normalized output stats
- the intake source cards:
  - `Paste Raw Logs`
  - `Webhook`
  - `Manual Form`
  - additional sources under `More Sources`
- raw incident textarea
- `Load example logs`
- parsed evidence section
- visible three-step submit progress strip:
  - `Normalize intake`
  - `Create incident`
  - `Open workspace`
- browser parse fields:
  - detected service
  - severity hint
  - error signature
  - expected action
- `Submit raw logs`
- `Open incident workspace`

### Recommended stakeholder demo path

Use the curated bundle path first instead of random logs:

1. in `Guided demo bundles`, click `Checkout timeout / retry amplification`
2. verify the `Bundle proof` panel updates with the expected family, likely owner, runtime posture, and agent path
3. verify the raw textarea is populated automatically
4. verify the browser parse still reads like a timeout-oriented case
5. click `Submit raw logs`
6. wait for the fresh `nxs_...` incident workspace to open
7. start at the top incident brief before replaying the handoff chain or opening deep technical detail

For the second fresh-log demo, repeat the same path with `DB pool exhaustion / session leak`.

### Main manual test

1. click either `Checkout timeout / retry amplification` or `DB pool exhaustion / session leak`
2. verify the textarea is populated
3. verify the parsed evidence panel updates
4. click `Submit raw logs`
5. watch the progress state move through intake normalization, incident creation, and workspace opening
6. wait for the fresh incident page to open
7. verify the incident page shows a `Demo intake origin` card near the top

### Expected response

After submit:

- a fresh incident with an `nxs_...` id should be created
- the input screen should show a staged transition rather than a silent freeze:
  - `Step 1 of 3: shaping the raw evidence into one bounded incident case...`
  - `Step 2 of 3: created ... Hydrating the top incident brief now...`
  - `Step 3 of 3: opening ...`
- the three-step progress strip should visibly advance with that same flow
- the route transition should read like an intentional handoff into the top incident brief, not like a blank page reload
- the UI should open the incident workspace for that new incident
- the created incident should preserve the intake context
- the fresh incident should land at the **top incident brief first**
- if the logs came from a guided bundle, the fresh incident should preserve that bundle story in the `Demo intake origin` card
- it should **not** auto-jump down to the Guardian card on initial load
- the relay banner should explain that `Replay handoff` is optional if you want to inspect the specialist sequence

### What this proves

- the browser can shape raw evidence before the deeper reasoning pass
- fresh incidents can enter the same workflow as seeded ones
- the operator can start from realistic, buyer-legible outage evidence without extra explanation

## Step 3: Review The Flagship Incident (`INC001`)

Open:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC001](http://127.0.0.1:7860/incident?nexus_incident_id=INC001)

This is the most important review path in the whole product.

### The business scenario

`INC001` represents a checkout timeout / retry amplification outage.

The story to tell:

- customers are timing out during checkout
- support has noisy logs and paging signals
- NEXUS identifies likely ownership, likely issue family, and likely next action
- the product assembles the prepared review packet before engineering starts from scratch

### What this screen is doing

This screen is the main support-to-engineering investigation workspace.

It should communicate:

- one production incident is in focus
- the agent crew has already reduced manual relay work
- runtime validation and debugging guidance appear where supported
- final action stays behind explicit human review

### What to inspect, top to bottom

#### 1. Hero and working memory

Look at:

- incident title
- incident severity
- Guardian state
- execution state
- working memory card
- live reasoning status
- next operator action

Expected response:

- the screen should immediately explain what the case is
- likely owner and next action should feel legible
- the operator should not need to dig for the first read
- for fresh `nxs_...` incidents created from `/inputs`, this top summary is now the intended first landing point

#### 2. Specialist crew and governance surface

Look at:

- crew relay strip
- `Replay handoff`
- `Export to engineering`
- `Send to engineering`
- `Export governance`
- `Export case proof`
- BYO key card
- Guardian approval buttons

Expected response:

- the crew should feel like a coordinated chain, not independent widgets
- Guardian should feel like a real gate
- the product should make execution subordinate to review
- `Replay handoff` should now feel optional, not like something that hijacks the first landing experience

#### 3. Investigation Summary & Operator Path

Look at:

- `What is the incident?`
- `What went wrong?`
- `What should we do?`
- `Is it safe to execute?`

Expected response:

- this should read like a prepared escalation packet
- each agent handoff should answer one understandable question

#### 4. Enterprise Task Board

Look at:

- orchestration state
- task board
- memory-grounded context
- reliability posture
- fallback and retries

Expected response:

- the system should look like it decomposed the incident into explicit workstreams
- memory should support, not distract from, the core path

#### 5. REPLICA section

Look at:

- environment pack
- status
- hypothesis
- confidence delta
- replay capability
- replay host
- runtime-host posture
- runtime queue recovery
- `Run bounded replay`
- replay lifecycle
- replay trust packet
- runtime comparison block

Expected response:

- the UI should be explicit about whether replay is supported
- if runtime replay is available, the host posture should be visible
- the comparison block should explain baseline versus mitigated outcome
- nothing should imply universal or arbitrary reproduction

#### 6. TRACE section

Look at:

- trace status
- confidence
- replay evidence
- inspect-here-first guidance
- developer handoff details
- residual risk and boundaries

Expected response:

- TRACE should feel like bounded debugging guidance
- it should help an engineer know where to look first
- it should not pretend to be a universal debugger

#### 7. Technical detail disclosure

Expand `Expand technical detail`.

Inspect:

- source payload
- normalized evidence
- recent logs
- alert timeline
- recent deployments
- similar past incidents
- workflow internals
- audit ledger
- delivery history
- engineering feedback

Expected response:

- the deeper detail should exist without overwhelming the primary operator path
- the system should preserve provenance, audit, and execution context

### Main manual actions to try on `INC001`

1. read the top summary only, without opening technical detail
2. verify you can explain the likely incident family and owner
3. click `Run bounded replay`
4. watch the replay lifecycle state and status text update
5. use `Export to engineering`
6. use `Export governance`
7. optionally click `Approve runbook`
8. review the outcome state and then go to `/training`

### What this proves

- NEXUS can turn a real support-style outage into a review-ready case
- runtime-backed evidence is visible where supported
- governance remains explicit

## Step 4: Review The Second Core Incident (`INC002`)

Open:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC002](http://127.0.0.1:7860/incident?nexus_incident_id=INC002)

### The business scenario

`INC002` represents checkout DB pool exhaustion / session leak.

Use this to prove the product is not overfit to one retry-storm story.

### What to focus on

- different issue family
- different likely owner
- different mitigation ladder
- different debugging packet
- different replay comparison story

### Expected response

You should be able to say:

- NEXUS can handle a customer-facing outage that is operationally and technically different from `INC001`
- the system still produces a structured packet with runtime posture, debugging guidance, and governed action

## Step 5: Review Breadth Incidents

Use these as supporting proof, not the primary story.

### `INC003`

Open:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC003](http://127.0.0.1:7860/incident?nexus_incident_id=INC003)

What it proves:

- deploy regression / 5xx spike handling
- release-aware reasoning
- rollback-oriented mitigation logic

### `INC005`

Open:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC005](http://127.0.0.1:7860/incident?nexus_incident_id=INC005)

What it proves:

- queue / worker backlog framing
- broader operational outage coverage inside the same product category

### `INC007`

Open:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC007](http://127.0.0.1:7860/incident?nexus_incident_id=INC007)

What it proves:

- auth dependency slowdown / token validation failure coverage
- a distinct family that still belongs to the same wedge

## Step 6: Review Learning & Controls

Open:

- [http://127.0.0.1:7860/training](http://127.0.0.1:7860/training)

### What this screen is doing

This page proves that the product is measurable, bounded, and operable.

### What to inspect

#### 1. Latest live triage

Expected response:

- the page should connect back to the last incident you actually ran
- it should not feel disconnected from the main incident workspace

#### 2. Pilot scorecard dashboard

Inspect:

- incidents handled
- runtime-backed
- inference-first
- triage time saved
- handoff completion
- repeat reuse
- `Download weekly review`
- `Download closeout package`

Expected response:

- this should feel like pilot proof, not vanity analytics

#### 3. Product health and observability

Inspect:

- overall pilot-safe posture
- application health
- replay execution
- queue health
- downstream integrations
- service posture list
- what-to-check-next guidance

Expected response:

- the operator should understand health without reading logs
- degraded language should be bounded and non-magical

#### 4. Runtime capability and execution posture

Inspect:

- runtime-host posture
- supported incident packs
- bounded scope explanation
- current execution state
- execution guardrails
- recent replay activity

Expected response:

- replay should look controlled and bounded
- the product should not imply arbitrary environment recreation

#### 5. ROI and wedge coverage

Inspect:

- manual relay reduction
- replay coverage
- approval outcomes
- memory reuse
- five-family wedge coverage

Expected response:

- you should leave the page understanding why a buyer would care

## Step 7: Review Settings

Open:

- [http://127.0.0.1:7860/settings](http://127.0.0.1:7860/settings)

### What this screen is doing

This page proves that the product has a trust, onboarding, deployment, and governance posture.

### What to inspect

- tenant onboarding and deployment readiness
- operational status
- runtime host
- runtime queue recovery
- deployment readiness
- pilot observability
- admin controls
- backend contract surface

### Expected response

You should come away believing:

- the product has explicit operational boundaries
- replay and governance are not hidden
- deployment posture is honest

## Step 8: Review History

Open:

- [http://127.0.0.1:7860/history](http://127.0.0.1:7860/history)

### What this screen is doing

History turns past incidents into reusable operational memory.

### What to inspect

- resolved versus blocked counts
- archive filters
- incident archive rows
- links back into incident detail

### Expected response

- history should feel like working memory, not dead storage
- you should be able to explain how repeated issue families get easier over time

## Step 9: Review Replay

Open:

- [http://127.0.0.1:7860/replay](http://127.0.0.1:7860/replay)

### What this screen is doing

Replay is the controlled rehearsal surface for known scenarios.

### What to inspect

- scenario cards
- selected scenario summary
- replay evidence
- `Launch replay run`
- open-console path

### Expected response

- this should feel like rehearsal for known outage classes
- it should not feel like universal test generation

## 10. The Exact Demo Story To Use

If you are presenting the product live, use this narrative:

1. support starts with noisy evidence
2. NEXUS shapes the case
3. NEXUS identifies likely ownership and issue family
4. NEXUS reuses memory and past cases
5. NEXUS validates bounded hypotheses where supported
6. NEXUS prepares debugging guidance and engineering handoff
7. NEXUS ranks mitigations
8. a governed human review remains before action

Use this sentence:

**NEXUS reduces manual support-to-engineering relay by turning raw evidence into a runtime-aware, debugging-guided, review-ready case.**

## 11. What To Say And What Not To Say

### Say

- AI-assisted support triage and incident investigation
- support-to-engineering investigation workflow
- bounded runtime replay
- bounded debugging guidance
- governed human approval
- runtime-backed versus inference-first posture

### Do not say

- universal incident-response platform
- universal debugger
- arbitrary environment reproduction
- autonomous production remediation

## 12. If Something Looks Wrong

If the review does not match this guide, note which category the issue falls into:

- setup issue
- stale copy / wording issue
- seeded incident quality issue
- fresh `nxs_...` incident quality issue
- runtime-host or replay issue
- debugging packet clarity issue
- governance or export issue
- UI clarity or navigation issue

That is exactly how the next narrow backlog should be shaped.

## 13. Supporting Documents

Use these only if you need deeper material after the main walkthrough:

- [README](/Users/kunalkachru/Documents/nexus-v3/README.md)
- [Demo Walkthrough](/Users/kunalkachru/Documents/nexus-v3/docs/public/DEMO_WALKTHROUGH.md)
- [Demo Cheat Sheet](/Users/kunalkachru/Documents/nexus-v3/docs/public/DEMO_CHEAT_SHEET.md)
- [Buyer Proof Package](/Users/kunalkachru/Documents/nexus-v3/docs/public/BUYER_PROOF_PACKAGE.md)
- [Product Strategy and GTM](/Users/kunalkachru/Documents/nexus-v3/docs/public/PRODUCT_STRATEGY_AND_GTM.md)
