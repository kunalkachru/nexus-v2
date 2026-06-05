# NEXUS Support Triage Product Execution Plan

Current as of 2026-06-05.

This is the implementation-grade plan for turning NEXUS from a broad incident-response demo into a support triage and investigation product that can be built, demoed, and sold around one real enterprise problem.

It is written so the next step after reading it is implementation.

## Product Thesis

NEXUS should be built and presented as:

**an AI-assisted support triage and incident investigation system that reduces the manual relay chain before final human review**

The product is not primarily selling:

- multi-agent architecture
- RL
- generic "AI ops"
- autonomous healing

It is selling:

- less log pasting and manual evidence gathering
- fewer support-to-support and support-to-engineering relays
- faster time to likely owner and likely cause
- reuse of prior incidents and known fixes
- reproduction and debugging support when needed
- one governed human review point before action

## The First Problem We Are Solving

The first-class problem for the product and the demo is:

**a customer-facing checkout outage caused by timeout and retry amplification after dependency degradation and recent deploy ambiguity**

This is the right flagship problem because it has:

- obvious business impact
- noisy but believable logs
- unclear ownership at first glance
- value from memory and prior-issue retrieval
- a meaningful reproduction story
- a meaningful debugging story
- a remediation path that should be reviewed before approval

## Demo Promise

The end-to-end demo should prove one clear claim:

**NEXUS compresses a multi-step manual support escalation into one AI-prepared, human-reviewed incident packet.**

At the end of the flagship flow, the viewer should believe that:

1. a support engineer no longer has to manually collect and relay evidence across multiple tiers
2. the product can identify the likely service, likely issue family, and likely next action
3. the product can retrieve prior incidents and known fixes
4. the product can reproduce and investigate the issue more deeply when needed
5. the final human approver reviews a prepared case, not raw chaos

## What Exists Today Vs What This Plan Adds

### Shipped foundation

Today NEXUS already has:

- `SENTINEL` classification
- `PRISM` diagnosis and branch-style investigation
- `FORGE` remediation proposal
- `GUARDIAN` approval and policy posture
- memory overlays for similar incidents, runbooks, and unresolved items
- deterministic and optional live reasoning paths
- incident, training, replay, queue, and history surfaces

### What this plan adds

This plan turns the product into a fuller support triage workflow by adding:

- stronger support-triage and ownership framing in the UI and docs
- better evidence and memory quality for the flagship outage type
- a first reproduction agent: `REPLICA`
- a first debugging agent: `TRACE`
- a unified investigation-to-action contract across all agents
- one polished end-to-end outage demo that proves the product story

## Product Workflow

The target workflow for the flagship problem is:

1. outage evidence arrives through raw logs or incident intake
2. `SENTINEL` classifies severity, likely service, likely owner, and issue family
3. `PRISM` investigates the likely cause using logs, deploy context, memory, and evidence correlation
4. `REPLICA` reproduces the failure in a production-like sandbox when confidence needs to be raised
5. `TRACE` narrows the likely code path or state deviation when code-level ambiguity remains
6. `FORGE` prepares the safest remediation and rollback-aware action plan
7. `GUARDIAN` governs the final human review and execution decision
8. the learning layer captures the outcome for future retrieval and ranking

## Primary User Journey

The operator journey should feel like this:

1. paste logs or open an incoming case
2. see the incident normalized and owned quickly
3. watch the investigation packet form
4. inspect similar prior incidents and known fixes
5. inspect reproduction and debugging findings if available
6. review one prepared remediation packet
7. approve, block, or request modification

The user should not have to:

- manually re-paste logs between tools
- manually chase previous incident records
- manually reconstruct recent deploy context
- manually prepare the first draft of the remediation packet

## Epics

## Epic 0: Product Narrative And Demo Alignment

### Goal

Make the product read and behave like a support triage and investigation product before adding major new backend depth.

### Why it comes first

Without this, every later capability will still look like generic "incident AI."

### Feature slices

1. Rewrite primary UI copy
   - queue, inputs, incident, training, replay, and history should talk about triage, investigation, prepared action, and final review

2. Align hero and section labels to the new story
   - incident page should emphasize:
     - likely owner
     - likely issue family
     - investigation status
     - prepared action packet

3. Update demo surfaces
   - demo narration, walkthrough, and replay content should all use the same support-triage language

4. Add explicit "manual relay removed" moments
   - show where the product replaced the old support handoff chain

### Exit criteria

- a new viewer can understand the product category in under 15 seconds
- the incident page reads like support triage and investigation, not generic agent choreography
- the demo story uses one vocabulary across docs, UI, and narration

## Epic 1: Flagship Outage Demo Hardening

### Goal

Make one outage scenario excellent from intake to approval.

### Scope

The flagship case is the checkout timeout and retry cascade.

### Feature slices

1. Strengthen intake realism
   - raw logs should show:
     - timeout pattern
     - retry amplification
     - worker saturation
     - recent deploy ambiguity
     - dependency hints

2. Strengthen `SENTINEL`
   - classify:
     - severity
     - likely impacted customer path
     - likely owning service
     - likely responder team
     - issue family

3. Strengthen `PRISM`
   - explicitly separate:
     - evidence correlation
     - deploy/change analysis
     - historical analog lookup
   - produce a synthesized investigation packet

4. Strengthen `FORGE`
   - compare mitigation options, not just propose one
   - include rollback readiness and blast-radius considerations

5. Strengthen `GUARDIAN`
   - make the final review point feel operational and consequential
   - explain:
     - why this action is safe enough or not
     - what approval level is needed
     - what rollback path exists

### Exit criteria

- one live run from `/inputs` to approval feels coherent without verbal coaching
- the checkout outage has a clear owner, cause hypothesis, and recommended next action
- the approval step feels like the final manual intervention point

## Epic 2: Memory And RAG Deepening

### Goal

Make the investigation packet feel grounded in prior operational knowledge instead of generic reasoning.

### Scope

Memory should serve the flagship outage class first.

### Feature slices

1. Similar incident retrieval
   - rank by:
     - service match
     - issue family match
     - severity match
     - deploy/change overlap
     - resolution success rate

2. Runbook retrieval
   - retrieve historical mitigations
   - rank by:
     - similarity
     - prior success
     - current environment fit

3. Unresolved follow-up retrieval
   - surface deferred work that may explain recurrence

4. Retrieval explanation layer
   - every memory hit should answer:
     - why this case matched
     - what prior action worked
     - what prior risk remained

5. Memory ingestion contract
   - define how completed incidents become retrievable:
     - evidence summary
     - root cause summary
     - runbook outcome
     - guardian decision
     - unresolved follow-ups

### Exit criteria

- the viewer can tell why a prior case was retrieved
- `PRISM` and `FORGE` visibly cite memory, not just mention that memory exists
- the flagship case feels more like a known operational class than a one-off LLM guess

## Epic 3: REPLICA Reproduction Agent V1

### Goal

Add the first reproduction capability for the flagship outage type.

### Product role

`REPLICA` is the production-like validation agent. It recreates likely failure conditions and raises or lowers confidence in the current hypothesis and mitigation.

### V1 boundary

Do not start with arbitrary cloud VMs or every tech stack.

V1 should be:

- Docker-based
- tightly scoped to the flagship checkout outage
- built from curated environment packs
- able to replay known request and dependency failure patterns

### Feature slices

1. Environment pack catalog
   - define environment descriptors for:
     - service
     - runtime
     - dependency stubs
     - retry settings
     - worker or thread pool settings
     - recent deploy configuration toggles

2. Reproduction orchestrator
   - choose a pack based on incident evidence
   - launch a local sandbox
   - inject the failure pattern

3. Hypothesis validation
   - test whether the issue reproduces under the suspected conditions
   - record what changed confidence up or down

4. Candidate remediation validation
   - apply the likely fix in the sandbox when safe
   - check whether the error pattern improves

5. UI integration
   - incident page should show:
     - reproduction status
     - reproduction confidence
     - conditions used
     - validation outcome

### REPLICA V1 acceptance criteria

- the flagship checkout outage can be replayed in a curated sandbox
- `REPLICA` reports reproduced or not reproduced with reasoning
- `FORGE` can cite `REPLICA` findings
- `GUARDIAN` can see that the proposed fix was or was not validated

## Epic 4: TRACE Debugging Agent V1

### Goal

Add the first debugging capability for the flagship outage type.

### Product role

`TRACE` is the code-aware investigation agent. It narrows the likely failing path and explains where execution diverges from the expected flow.

### V1 boundary

Do not attempt to build a universal debugger.

V1 should focus on:

- suspected module and function narrowing
- stack-trace interpretation
- recent deploy diff awareness
- runtime state clues from the reproduction environment

### Feature slices

1. Service-to-code mapping
   - map flagship incident evidence to likely modules and handlers

2. Debug context builder
   - collect:
     - stack traces
     - recent deploy hints
     - relevant source paths
     - runtime-state clues from `REPLICA`

3. Suspected path narrowing
   - identify:
     - suspect branch or function
     - expected vs actual behavior difference
     - likely variable/state anomalies

4. Developer-ready packet
   - output:
     - suspected location
     - probable deviation
     - supporting runtime clues
     - confidence

5. UI integration
   - show debugging findings as part of the investigation packet, not as a separate developer-only silo

### TRACE V1 acceptance criteria

- the flagship outage produces a developer-facing debugging summary
- `TRACE` can narrow the likely code path for the retry amplification issue
- `FORGE` can use `TRACE` output to justify safer mitigation choices

## Epic 5: Unified Action Preparation And Governance

### Goal

Make the post-investigation step feel like one prepared operational packet.

### Feature slices

1. Unified incident packet
   - combine outputs from:
     - `SENTINEL`
     - `PRISM`
     - memory
     - `REPLICA`
     - `TRACE`
     - `FORGE`

2. Prepared action review surface
   - operator sees:
     - likely issue
     - likely owner
     - evidence summary
     - prior incident matches
     - reproduction result
     - debugging summary
     - proposed mitigation
     - rollback path
     - approval needed

3. Guardian decision quality
   - `GUARDIAN` should explain:
     - what risk remains
     - what is validated vs inferred
     - what conditions block execution

### Exit criteria

- the operator reviews one composed case packet, not scattered panels
- the final manual review point becomes the product's most credible screen

## Epic 6: Learning And Memory Closure

### Goal

Make every completed flagship incident improve future triage.

### Feature slices

1. Outcome capture
   - store:
     - approved action
     - execution result
     - reproduction result
     - debugging findings
     - post-incident unresolved work

2. Retrieval improvement loop
   - use completed cases to improve future ranking

3. Training page clarity
   - distinguish:
     - latest live triage
     - enterprise runtime health
     - broader learned baseline

### Exit criteria

- the latest run has a clear path into future retrieval
- the training page explains what this incident contributed to the system

## Exact Feature Slices By Implementation Phase

## Phase 1: Narrative And Demo Alignment

Implement now:

- rewrite UI copy on core screens
- tighten demo docs and walkthrough
- make the flagship outage the central demo story

Do not block on:

- new backend infrastructure
- reproduction or debugging code

## Phase 2: Flagship Outage Hardening

Implement next:

- better intake data for the checkout outage
- stronger `SENTINEL`, `PRISM`, `FORGE`, `GUARDIAN` outputs
- clearer incident packet presentation

## Phase 3: Memory And RAG Deepening

Implement next:

- better retrieval ranking
- stronger retrieval explanations
- incident completion ingestion model

## Phase 4: REPLICA V1

Implement next:

- environment pack definitions
- sandbox orchestration
- reproduction result contract

## Phase 5: TRACE V1

Implement next:

- code-path narrowing
- debug packet builder
- integration with reproduction signals

## Phase 6: Unified Product Loop

Implement next:

- composed incident packet
- tightened Guardian review surface
- learning closure

## Agent Contracts

These contracts are intended to extend the current runtime shape instead of replacing it.

## Shared Agent Result Contract

Every agent should emit:

```json
{
  "agent": "PRISM",
  "status": "completed",
  "confidence": 0.88,
  "reasoning": "Correlated retry amplification with auth dependency degradation and recent retry middleware rollout.",
  "evidence_ids": ["log:timeout:1", "metric:latency:p95", "deploy:auth-middleware:2026-06-05T09:00:00Z"],
  "input_refs": ["incident:INC001", "memory:INC004", "sandbox:replica-run-003"],
  "handoff_to": "REPLICA",
  "duration_ms": 420,
  "fallback_used": false,
  "retry_count": 0
}
```

## SENTINEL Contract

Purpose:

- classify severity and likely ownership

Required fields:

- `incident_id`
- `severity`
- `likely_service`
- `likely_team`
- `issue_family`
- `customer_impact`
- `confidence`
- `reasoning`

Maps onto current code:

- extend the current `SentinelClassification` shape

## PRISM Contract

Purpose:

- produce the investigation packet

Required fields:

- `incident_id`
- `root_cause_hypothesis`
- `supporting_evidence`
- `deploy_analysis`
- `historical_analogs`
- `confidence`
- `reasoning`
- `next_investigation_step`

Maps onto current code:

- extend the current `PrismDiagnosis` shape

## REPLICA Contract

Purpose:

- reproduce the issue and validate hypotheses

Required fields:

- `incident_id`
- `environment_pack_id`
- `reproduction_status`
- `reproduced_symptoms`
- `hypothesis_supported`
- `confidence_delta`
- `tested_mitigations`
- `reasoning`

Example:

```json
{
  "incident_id": "INC001",
  "environment_pack_id": "checkout-python-fastapi-auth-redis-v1",
  "reproduction_status": "reproduced",
  "reproduced_symptoms": ["gateway timeout spike", "worker saturation", "retry budget exceeded"],
  "hypothesis_supported": true,
  "confidence_delta": 0.12,
  "tested_mitigations": [
    {
      "action": "cap retries to 1",
      "result": "latency improved"
    }
  ],
  "reasoning": "The failure pattern reproduced only when the recent retry middleware configuration was enabled under downstream auth degradation."
}
```

## TRACE Contract

Purpose:

- narrow likely code path and debugging clues

Required fields:

- `incident_id`
- `service`
- `suspected_modules`
- `suspected_functions`
- `expected_flow`
- `observed_divergence`
- `state_anomalies`
- `confidence`
- `reasoning`

## FORGE Contract

Purpose:

- prepare the recommended action packet

Required fields:

- `incident_id`
- `recommended_action`
- `alternatives`
- `rollback_plan`
- `blast_radius`
- `evidence_basis`
- `memory_basis`
- `reproduction_basis`
- `debugging_basis`
- `confidence`
- `reasoning`

Maps onto current code:

- extend `ForgeRunbookResult`

## GUARDIAN Contract

Purpose:

- govern the final human review point

Required fields:

- `decision`
- `risk_class`
- `required_approval_level`
- `validated_signals`
- `inferred_signals`
- `blocked_controls`
- `rollback_readiness`
- `simulation_readiness`
- `reasoning`

Maps onto current code:

- extend the current `GuardianReviewResult`

## Data And Platform Contracts

## Memory record contract

Each completed incident should persist:

- issue family
- likely service
- root cause summary
- reproduction summary
- debugging summary
- chosen action
- execution outcome
- guardian decision
- unresolved follow-ups

## Environment pack contract for REPLICA

Each pack should define:

- stack identifier
- service topology
- dependency stubs
- runtime settings
- load or replay profile
- failure injection toggles
- supported mitigation checks

## Source map contract for TRACE

TRACE needs:

- service-to-module map
- route or handler map
- recent deploy change summary
- stack-trace normalizer

## Order Of Implementation

Build in this order.

1. Narrative and core UI copy alignment
2. Flagship outage hardening
3. Memory and RAG quality
4. REPLICA V1
5. TRACE V1
6. Unified action-review packet
7. Learning closure and retrieval improvement

That order matters because:

- it gets one credible product loop visible early
- it avoids building speculative infrastructure before the demo story works
- reproduction should exist before debugging tries to use runtime evidence

## Demo Acceptance Criteria

The flagship demo is successful only if all of the following are true.

## Operator understanding

- a new viewer can explain the product in one sentence after the first minute
- the viewer can tell who currently owns the case and why
- the viewer can tell what manual relay work was removed

## Triage quality

- `SENTINEL` identifies the likely service, likely team, issue family, and impact
- the incident does not feel like a generic "logs in, answer out" toy flow

## Investigation quality

- `PRISM` clearly separates evidence, deploy context, and historical analogs
- memory hits explain why they matched

## Reproduction quality

- `REPLICA` can reproduce the flagship failure class in a curated sandbox
- the viewer can see whether reproduction increased or decreased confidence

## Debugging quality

- `TRACE` narrows the likely failing path enough to help an engineer start in the right place

## Remediation quality

- `FORGE` compares multiple actions, not just one
- the chosen path has rollback and blast-radius context

## Governance quality

- `GUARDIAN` is visibly the final human review point
- the operator can explain what was validated and what remains inferred

## Product value

- the viewer believes the product reduced the number of humans needed before the final review
- the viewer believes this would shorten time to confident action in a real support organization

## Non-Goals For V1

Do not turn the first implementation into:

- a universal ITSM platform
- a universal debugger for any codebase
- arbitrary VM provisioning across every environment
- unsupervised production execution
- a broad "AI operations" suite

The first real product should win on one outage class, one support workflow, and one crisp buyer story.

## Recommended Immediate Build Backlog

The next build sprint should start with these slices in order:

1. update incident, queue, inputs, replay, and training copy to the support-triage narrative
2. tighten the checkout outage data and scripted outputs
3. upgrade `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN` contracts for the flagship case
4. upgrade memory ranking and explanations for the flagship case
5. define `REPLICA` environment packs and result contract
6. define `TRACE` source-map and debug packet contract
7. build the composed incident packet UI

## Definition Of Ready For Implementation

We are ready to start implementation when:

- the checkout outage is accepted as the flagship use case
- the support-triage narrative is the product source of truth
- the six-agent target workflow is accepted:
  - `SENTINEL`
  - `PRISM`
  - `REPLICA`
  - `TRACE`
  - `FORGE`
  - `GUARDIAN`
- `REPLICA` V1 is accepted as Docker-based and curated, not arbitrary VM orchestration
- `TRACE` V1 is accepted as code-path narrowing and debugging packet generation, not a universal debugger

Once those decisions hold, implementation should proceed directly from this plan.
