# NEXUS v2 Technical Roadmap

Current as of 2026-06-05.

This roadmap describes the most practical next steps for the shipped NEXUS v2 codebase over the next few weeks.
It is intentionally short-horizon and engineering-focused.

For the broader support-triage product direction, flagship outage demo, and the implementation plan for memory, reproduction, and debugging agents, use:

- [SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md)

## Goal

Move NEXUS v2 from:

- a polished, public, deterministic-by-default demo product

to:

- a faster
- more reliable
- more production-shaped
- more measurable

support-triage and investigation system without breaking the current demo flow.

## Guiding Principles

- keep the public demo safe by default
- preserve the current 4-agent mental model
- improve real backend behavior without regressing the support-triage UI story
- prefer additive hardening over risky rewrites
- keep verification and demo reproducibility strong

## Week 1: Performance And Demo Reliability

### Objectives

- reduce perceived latency on the public HF Space
- make the incident flow feel faster and more stable
- tighten the demo path before deeper backend work

### Work Items

1. Reduce incident page load fan-out
   - review duplicate API calls on incident load
   - render primary content first, defer secondary panels
   - cache stable incident context where safe

2. Improve navigation responsiveness
   - prefetch likely next routes from queue and inputs
   - preload incident context for the first queue item
   - reduce blocking layout work in page scripts

3. Harden hosted demo performance
   - measure HF route timings per screen
   - compare hosted vs local latency regularly
   - tune page controllers for faster first meaningful paint

4. Clean top-level shell details
   - remove any remaining confusing secondary controls from primary nav
   - make the main 3-screen information architecture feel tighter

### Exit Criteria

- warm route transitions feel closer to `~1 second` than `4–5 seconds`
- queue to incident remains reliable
- inputs to incident remains reliable
- browser verification still passes

## Week 2: Backend Realism And Evidence Quality

### Objectives

- make incident reasoning feel less fixture-shaped
- improve the realism of evidence, diagnosis, and governance outputs

### Work Items

1. Enrich live incident evidence
   - expand normalized raw-log extraction
   - improve signature extraction and service inference
   - add stronger provenance summaries for evidence sources

2. Strengthen diagnosis and runbook outputs
   - tighten deterministic PRISM reasoning quality
   - improve FORGE runbook selection and explanation text
   - make Guardian reasoning more explicit and policy-grounded

3. Improve incident lifecycle fidelity
   - refine workflow stage transitions
   - tighten queue ordering and ETA behavior
   - preserve more context across replay/history/manual flows

4. Expand regression coverage
   - add more live-incident context tests
   - add more raw-log parsing cases
   - add more browser checks for agent state transitions

### Exit Criteria

- incident detail pages feel more evidence-grounded
- raw-log flows produce better parsed context
- Guardian decisions remain visible and understandable
- the flagship checkout outage reads more like a support case than a seeded demo fixture

## Week 3: Safe Live Reasoning And Operator Controls

### Objectives

- mature the BYO-key path
- keep the live path safe, explicit, and well-governed

### Work Items

1. Improve BYO-key UX
   - make live-mode state clearer in the UI
   - surface when deterministic fallback is used
   - improve validation and error messaging for user-supplied keys

2. Constrain live reasoning carefully
   - ensure only intended paths attach the request-scoped key
   - keep logs and persistence layers free of secret material
   - add stronger test coverage around bad-key and no-key flows

3. Make operator controls clearer
   - improve Guardian review affordances
   - make execution state transitions clearer in the UI
   - improve explanation around blocked vs approved outcomes

### Exit Criteria

- BYO-key flow is obvious and trustworthy
- deterministic vs live behavior is clearly visible
- no regression in public-safe posture

## Week 4: Productization And Submission Hardening

### Objectives

- make the repo easier to hand off, review, and extend
- strengthen the operational path beyond the demo

### Work Items

1. Expand observability for the app itself
   - add lightweight request timing instrumentation
   - log page-critical backend timings in a safe way
   - make hosted performance regressions easier to spot

2. Improve deployment and release hygiene
   - formalize rebuild/redeploy checks
   - add a reproducible release checklist
   - make HF deployment verification a documented standard step

3. Strengthen documentation and assets
   - keep screenshots and video assets refreshed
   - update technical diagrams when flows change
   - maintain one source of truth for the current shipped state

4. Prepare the next execution branch
   - identify which integrations should become real first
   - define the first post-demo backend milestone clearly

### Exit Criteria

- the repo remains submission-clean
- deployment and verification remain reproducible
- next-phase engineering work is easier to prioritize

## Recommended Order Of Execution

If only a small amount of time is available, do the work in this order:

1. performance and hosted-demo latency
2. incident evidence and reasoning quality
3. BYO-key clarity and live-mode safety
4. productization and release hardening

## What Not To Do Immediately

To avoid unnecessary risk, do not prioritize these first:

- a full frontend rewrite
- replacing the current product shell with a SPA
- deep infrastructure scaling work before demo reliability is stable
- broad enterprise integrations before the current evidence flow is tighter

## Success Markers

At the end of the next few weeks, the codebase should show:

- faster hosted page transitions
- better incident reasoning quality
- safer and clearer live reasoning behavior
- stronger test and browser regression coverage
- a cleaner path from public demo to support-triage product hardening
