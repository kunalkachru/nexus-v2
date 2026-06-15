# NEXUS Post-85 Wedge-Strengthening Plan

Current as of 2026-06-15.

This document describes the phase after the market-ready v1 checkpoint (`77–85`) is complete.

The goal of this phase is not to broaden NEXUS into a general incident platform.

It is to make the current wedge:

- more repeatable
- more technically credible
- more visibly LLM-driven at triage time
- more persuasive in pilot conversations
- more impressive in the product UI without losing truthfulness

## Product Position After 85

After `77–85`, NEXUS should be described as:

**a market-ready v1 support-triage and incident-investigation product for recurring customer-facing checkout and transaction-critical incidents**

That is good enough for narrow release.

The next gap is not baseline hardening anymore.

The next gap is:

- proving the wedge is repeatable across more than two incident families
- making triage feel genuinely LLM-driven instead of partially fixture-shaped
- making agent collaboration legible to buyers and operators
- improving pilot-conversion readiness for the expanded wedge

## The Problem Still Stays The Same

The product should continue solving one problem:

**too many expensive human relays happen between support and engineering before a confident action exists during recurring customer-facing incidents**

This phase does not change the buyer story.

It strengthens the proof that NEXUS can solve that story across a broader but still bounded set of recurring outage classes.

## Recommended Next Boundary

Use `86–92` for the next short execution phase.

This phase should stay inside the current product category:

**support-to-engineering investigation workflow for recurring customer-facing outages**

It should not drift into:

- broad incident management
- universal debugging
- universal reproduction
- generalized autonomous remediation

## Recommended Scope

The next phase should contain:

- a third flagship outage family: deploy regression / 5xx spike
- bounded REPLICA and TRACE support for that outage family
- stronger LLM-driven triage reasoning for seeded and fresh incidents
- clearer agent deliberation visibility in the operator UI
- pilot-conversion packaging for the three-outage wedge
- a final wow-effect polish pass where the product still feels visually incomplete
- a deliberate post-85 checkpoint

## Why This Is The Right Next Move

After `85`, the biggest risk is not that the product looks too small.

The bigger risk is that it looks:

- too canned
- too dependent on only two seeded scenarios
- too static in how agents appear to reason

This phase directly addresses that by proving:

1. the wedge extends to another real recurring outage class
2. the triage layer is more meaningfully LLM-shaped
3. the UI makes the multi-agent workflow feel real and understandable

## The Third Outage Family

The recommended next outage family is:

**deploy regression / 5xx spike on a customer-facing path**

Why this should be next:

- easy for buyers to understand
- common in real production support
- strong support-to-engineering story
- naturally connected to owner routing, rollback discussion, and deploy-window evidence
- easier to demo than deeper infrastructure scenarios

## LLM-Driven Triage Principle

This phase should improve triage quality by letting the LLM contribute more to:

- issue framing
- customer impact summary
- likely subsystem
- likely owner
- deploy-window suspicion
- likely next investigation steps
- uncertainty and confidence language

But the product must still clearly label:

- inferred reasoning
- memory-backed reasoning
- runtime-backed reasoning

This is critical.

The product should become more intelligently adaptive without becoming less truthful.

## Agent Visibility Principle

The UI should make the crew’s division of labor obvious:

- `SENTINEL` frames the incident
- `PRISM` forms and refines hypotheses
- `REPLICA` validates or fails to validate a failure mode
- `TRACE` narrows the likely code path
- `FORGE` chooses the most credible action
- `GUARDIAN` gates the decision

The operator should be able to see:

- what each agent added
- which evidence changed the direction of the case
- where uncertainty remains

## Pilot Conversion Goal

This phase should also help with real pilot conversations.

That means the product and docs should make it easier to show:

- three supported outage families instead of two
- the exact value story for support leaders
- the exact conditions under which NEXUS is runtime-backed versus inference-only
- a repeatable demo and onboarding motion for the narrow wedge

## UI Goal

The UI should end this phase feeling:

- premium
- modern
- confident
- easier to scan
- easier to present

But the polish should never hide:

- evidence quality
- bounded scope
- approval boundaries

## What This Phase Should Not Do

Do not use this phase to:

- add multiple unrelated outage categories
- add a universal debugger story
- add arbitrary environment reproduction claims
- add wide platform breadth
- rewrite the architecture for its own sake

## Acceptance Criteria

The phase is successful only when all of these are true:

1. `INC003` exists as a coherent third outage family across seeded and live product paths
2. `INC003` has bounded REPLICA and TRACE support consistent with the current product honesty model
3. fresh and seeded incidents show stronger LLM-driven triage framing, not just static summaries
4. the UI makes agent contributions and evidence-state transitions materially clearer
5. the buyer demo now feels like a repeatable wedge product, not a two-incident showcase
6. the visual layer is stronger on intake, incident, training, and handoff surfaces
7. the repo ends the phase with a clean checkpoint and updated control docs

## Recommendation

Treat `86–92` as the **wedge-strengthening and pilot-conversion sprint**.

If this phase lands cleanly, NEXUS should be able to present itself not only as a narrow v1, but as:

**a repeatable support-triage product for recurring customer-facing incident families, with bounded reproduction, bounded debugging, and more visible LLM-driven investigation quality**
