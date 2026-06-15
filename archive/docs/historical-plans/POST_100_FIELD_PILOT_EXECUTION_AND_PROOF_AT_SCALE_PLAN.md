# NEXUS Post-100 Field Pilot Execution And Proof-at-Scale Plan

Current as of 2026-06-15.

This document describes the phase after pilot conversion and technical proof deepening (`93–100`) is complete.

The purpose of this phase is to move NEXUS from a strong bounded pilot candidate into a product that can support **2–3 repeatable enterprise pilots** without heavy founder dependence.

This phase is FR2:

**repeatable enterprise pilot product**

It includes the strong narrow product from FR1, but adds the operational, evaluative, and commercial structure needed to make it work across multiple real pilot tenants.

## Product Position After 100

After `93–100`, NEXUS should be described as:

**a pilot-ready support-to-engineering investigation workflow for recurring customer-facing outage families, with bounded reproduction, bounded debugging, and stronger proof for support and engineering teams**

That is good enough for initial pilots.

The next gap is:

- repeatability across multiple pilot tenants
- real fresh-incident handling under noisier tenant inputs
- durable value proof at the tenant and weekly level
- stronger engineering trust in the handoff
- clearer downgrade behavior when incidents fall outside the supported wedge

## FR2 Goal

The goal of FR2 is:

**make NEXUS usable across 2–3 pilot tenants with bounded onboarding, bounded outage support, stronger pilot proof, and more trustworthy engineering handoff**

This phase should not broaden the category.

It should make the current wedge repeatable.

## The Problem Still Stays The Same

The product still solves one problem:

**too many expensive human relays happen between support and engineering before a confident action exists during recurring customer-facing incidents**

FR2 does not change the problem statement.

It makes the product strong enough that multiple tenants can run the workflow, evaluate it, and measure value without the system collapsing into founder-led setup and interpretation.

## Recommended Next Boundary

Use `101–108` for the FR2 execution phase.

This phase should stay inside the same product category:

**support-to-engineering investigation workflow for recurring customer-facing outages**

It should not drift into:

- generalized ITSM
- universal incident response
- universal debugging
- arbitrary environment reproduction
- platform-level breadth expansion

## Recommended Scope

The FR2 phase should contain:

- customer log intake normalization v2
- coverage matrix and unsupported-incident downgrade path
- fresh-incident quality evaluation harness
- pilot scorecard dashboard
- case-based proof export
- engineering handoff trust v3
- runtime evidence weighting v3
- pilot operations kit and checkpoint

## Why This Is The Right Next Move

After `100`, the biggest risk is no longer product credibility inside the current wedge.

The bigger risks are:

- a second or third tenant exposes too much hidden setup work
- fresh customer incidents are harder to parse than curated demos
- buyer proof is still too presentation-shaped instead of operational
- engineering teams still question whether the handoff is concrete enough
- unsupported incidents do not downgrade clearly enough

FR2 directly addresses those risks.

## Multi-Tenant Pilotability Principle

The product should become usable across multiple tenants by making these explicit:

- supported incident families per tenant
- runtime-backed versus inference-first coverage
- owner mappings and escalation expectations
- setup prerequisites and missing readiness
- downgrade path when incidents fall outside bounded support

## Pilot Proof Principle

The product should become easier to prove by surfacing:

- incidents handled
- runtime-backed versus inferred-only ratio
- triage time saved
- handoff completion
- repeat-incident reuse
- weekly pilot value summaries

These should be visible and exportable.

## Engineering Trust Principle

The product should become more credible to engineering reviewers by improving:

- repo-aware inspection cues
- mitigation rationale
- residual-risk framing
- runtime evidence weighting
- “inspect here first” guidance

This should stay bounded to the supported wedge rather than overclaim universal debugging coverage.

## Fresh-Incident Principle

The product should handle real incoming incidents better by:

- improving input normalization
- making uncertainty more explicit
- calibrating triage quality on non-curated cases
- degrading honestly when evidence or support coverage is weaker

## What This Phase Should Not Do

Do not use FR2 to:

- add many new outage families
- create a universal platform story
- promise arbitrary repository debugging
- promise arbitrary reproduction
- add autonomous production remediation

## Acceptance Criteria

FR2 is successful only when all of these are true:

1. 2–3 pilot tenants can be configured with bounded repeatable setup
2. fresh real incidents are handled more consistently and more honestly
3. the product makes supported versus unsupported coverage visible per tenant
4. pilot scorecards and case-based proof are durable and exportable
5. engineering handoff packets are more actionable and trusted
6. runtime evidence more strongly drives recommendations
7. unsupported incidents degrade clearly instead of bluffing
8. the repo ends the phase with a clean checkpoint and current control docs

## Recommendation

Treat `101–108` as the **FR2 field pilot execution and proof-at-scale sprint**.

If this phase lands cleanly, NEXUS should be able to present itself as:

**a repeatable enterprise pilot product for recurring customer-facing outage investigation, usable across multiple tenants with bounded support, measurable value proof, and stronger engineering trust**
