# FR2 Repeatable Enterprise Pilot Design

Current as of 2026-06-15.

## Goal

Define the next phase after `93–100` so NEXUS can support 2–3 repeatable enterprise pilots without broadening beyond the current three-outage wedge.

## Selected Approach

Chosen approach: **repeatable enterprise pilot product**

This includes the strong narrow product and the pilot-ready improvements already shipped, but adds the structure needed for multi-tenant repeatability, proof durability, engineering trust, and safer fresh-incident handling.

## Why This Approach

After `100`, the product already has:

- three bounded outage families
- bounded reproduction and debugging
- stronger triage reasoning
- stronger buyer proof
- stronger pilot-conversion posture

The next risk is not lack of product story.

The next risk is inability to repeat that story across multiple tenants with real incidents.

## Scope

### Included

- customer log intake normalization v2
- per-tenant coverage matrix and downgrade path
- fresh-incident evaluation harness
- pilot scorecard dashboard
- case-based proof export
- engineering handoff trust v3
- runtime evidence weighting v3
- pilot operations kit and checkpoint

### Not included

- broad outage-family expansion
- universal debugger claims
- arbitrary reproduction claims
- platform broadening

## Product Truth Model

FR2 must preserve explicit boundaries between:

- runtime-backed support
- inference-first support
- unsupported incident classes

The product should become more useful without becoming less honest.

## Acceptance Criteria

FR2 is complete only when:

1. 2–3 bounded pilot tenants can be configured with lower setup friction
2. fresh incidents are handled more credibly and more transparently
3. per-tenant coverage and unsupported-case behavior are visible
4. pilot scorecards and case-based proof are durable and exportable
5. engineering handoffs are stronger and more trusted
6. runtime evidence more clearly drives recommendations
7. the pilot operations kit exists
8. the phase closes with a clean checkpoint

## Deliverables

- [docs/POST_100_FIELD_PILOT_EXECUTION_AND_PROOF_AT_SCALE_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_100_FIELD_PILOT_EXECUTION_AND_PROOF_AT_SCALE_PLAN.md)
- [docs/POST_100_EXECUTION_MAP.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_100_EXECUTION_MAP.md)
- [backlog-101-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-101-plus.json)
