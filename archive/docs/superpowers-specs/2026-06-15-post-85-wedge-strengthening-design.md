# Post-85 Wedge Strengthening Design

Current as of 2026-06-15.

## Goal

Strengthen NEXUS after the market-ready v1 checkpoint by proving the product wedge is more repeatable, more visibly LLM-driven at triage time, and more credible in pilot conversations without broadening into a universal platform story.

## Selected Approach

Chosen approach: **wedge strengthening plus pilot conversion**

This phase stays inside the current product category:

- recurring customer-facing incidents
- bounded reproduction
- bounded debugging
- governed human approval

It does not expand into arbitrary incident types or generic autonomous operations.

## Why This Approach

The current product is credible but still vulnerable to three objections:

1. it may look too dependent on two curated incidents
2. triage may still look partly canned instead of intelligently adaptive
3. the UI may not yet make the agent workflow feel as strong as the underlying product story

The post-85 phase should solve those objections directly.

## Scope

### Included

- third flagship outage family: deploy regression / 5xx spike
- bounded REPLICA and TRACE coverage for that outage family
- stronger LLM-driven triage reasoning for seeded and fresh incidents
- clearer agent contribution visibility in the UI
- pilot-conversion proof improvements for the three-outage wedge
- final wow-effect UI completion on the most buyer-visible surfaces

### Not included

- universal incident response
- universal debugger
- arbitrary environment reproduction
- broad autonomous remediation
- general platform broadening

## Product Truth Model

The phase must preserve a strict distinction between:

- inferred reasoning
- memory-backed reasoning
- runtime-backed reasoning

This distinction should become clearer, not weaker, as triage becomes more LLM-shaped.

## Product Surfaces Most Affected

- queue and incident detail
- fresh incident intake
- training / ROI surfaces
- handoff and export surfaces
- supporting docs and walkthroughs

## Main Risks

### Risk 1: Overclaiming LLM intelligence

Mitigation:

- keep evidence posture explicit
- do not present inference as runtime validation
- do not expose raw chain-of-thought; expose concise contribution summaries

### Risk 2: Expanding too broadly

Mitigation:

- add exactly one new outage family in this phase
- keep new runtime and trace support bounded to curated packs

### Risk 3: UI polish masking truthfulness

Mitigation:

- keep evidence-state language and approval boundaries visually prominent
- evaluate polish against operator comprehension, not only aesthetics

## Acceptance Criteria

The phase is complete only when:

1. `INC003` exists and is coherent across seeded and live paths
2. `INC003` has bounded reproduction and debugging support
3. fresh incidents produce stronger adaptive triage reasoning
4. the UI shows which agent contributed what and why the recommendation changed
5. buyer and pilot-facing materials now reflect a three-outage wedge
6. the wow-effect pass feels complete on the key demo surfaces
7. the repo ends with a clean checkpoint and current control docs

## Deliverables

- [docs/POST_85_WEDGE_STRENGTHENING_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_85_WEDGE_STRENGTHENING_PLAN.md)
- [docs/POST_85_EXECUTION_MAP.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_85_EXECUTION_MAP.md)
- [backlog-86-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-86-plus.json)
