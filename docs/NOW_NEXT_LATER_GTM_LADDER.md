# NEXUS Now / Next / Later GTM Ladder

Current as of 2026-06-15.

This is the owner-facing go-to-market ladder for NEXUS.

It is intentionally narrow.

The purpose of this document is to keep product, demo, UI, and roadmap decisions aligned to one sellable problem instead of drifting toward a broad "AI incident platform" claim.

## One-Line Positioning

**NEXUS is a support-to-engineering investigation product for recurring customer-facing application outages.**

It helps support and triage teams turn noisy incidents into runtime-backed, debugging-guided, engineering-ready cases before one final human review point.

## The Exact Problem We Solve

**Support teams spend too much manual effort collecting logs, checking prior incidents, guessing ownership, reproducing failures, and escalating incomplete cases before engineering can take a confident action.**

This is most painful when the issue affects:

- checkout
- payments
- authentication
- signup
- other revenue or conversion-critical customer paths

## The Exact Wedge

NEXUS should lead with:

**recurring checkout-path and customer-facing transaction incidents**

The current flagship outage families are:

1. checkout timeout / retry amplification
2. checkout DB pool exhaustion / session leak

These are strong because they are:

- expensive
- understandable to buyers
- repeatable enough for memory and reproduction
- technical enough to show real agent value

## Now

### Exact audience

- Heads of Support Engineering at mid-market SaaS and commerce companies
- Technical Support leaders who own escalation quality
- CTOs or engineering heads at smaller companies where support and engineering are tightly coupled

### Exact user

- support engineers
- support triage engineers
- incident coordinators
- support leads who approve escalations

### Exact message

**NEXUS cuts the manual relay between support and engineering for recurring customer-facing outages.**

It does this by:

- structuring raw incident evidence
- checking prior cases and runbooks
- reproducing bounded failures
- preparing debugging guidance
- generating an engineering-ready action packet

### Exact problem statement

**When a checkout-path or other customer-facing outage happens, support teams waste time pasting logs, checking old tickets, guessing likely owners, and escalating weak cases. Engineering then repeats the same investigation work from scratch. NEXUS compresses that relay into one investigation workflow and one review packet.**

### What we are selling now

- faster support-to-engineering triage
- lower escalation churn
- better first-pass incident quality
- runtime-backed evidence for bounded outage classes
- clearer debugging handoff

### What we are not selling now

- a universal incident-response platform
- a universal debugger
- a universal reproduction engine
- autonomous production remediation across arbitrary stacks

## Next

### Exact audience

- the same buyer set, but across companies with multiple recurring outage families
- support engineering teams that already believe the first wedge works and want broader operational coverage

### Exact message

**NEXUS standardizes how recurring production issues are triaged, reproduced, debugged, and handed off across a small catalog of outage families.**

### Exact problem statement

**Companies do not only suffer from one outage. They suffer from the same few high-friction incident families repeating, with no consistent workflow for investigating them quickly and truthfully.**

### What expands in this phase

- a second and third curated outage family
- stronger tenant-specific routing and ownership
- stronger delivery and audit flows
- broader runtime packs inside the same bounded product category

### What still stays narrow

- customer-facing application incidents
- bounded curated environments
- governed human approval

## Later

### Exact audience

- larger engineering organizations with support, platform, SRE, and application teams
- enterprises that want one investigation layer across recurring operational incidents

### Exact message

**NEXUS becomes the investigation control plane for recurring application incidents across support, engineering, and operations.**

### Exact problem statement

**Large organizations lack a common system that connects intake, memory, reproduction, debugging guidance, approval, outcome capture, and downstream engineering handoff into one auditable investigation workflow.**

### What becomes possible later

- broader outage-family coverage
- deeper repo-aware debugging
- deeper runtime pack catalog
- stronger governance, audit, and buyer reporting

### What should not be claimed until later work exists

- arbitrary environment reproduction
- arbitrary repository debugging
- universal multi-stack production troubleshooting

## Exact Buyer Story

The buyer story should stay simple:

**Too many expensive humans touch the same incident before a confident next action exists.**

NEXUS reduces that cost by preparing:

- a triaged incident packet
- a memory-backed hypothesis set
- a bounded reproduction result
- a bounded debugging trail
- a governed recommendation
- an engineering-ready handoff

## Exact Demo Story

The strongest demo should show:

1. a real-looking customer-facing outage enters from support intake
2. NEXUS classifies the incident and frames likely ownership
3. memory retrieves similar past cases and known mitigation patterns
4. REPLICA reproduces the bounded failure mode
5. TRACE generates a debugging path with concrete checkpoints
6. FORGE recommends the best mitigation based on evidence
7. GUARDIAN gates the action behind explicit approval
8. the case is exported downstream in engineering-ready form

## Exact Market Category

If we have to name the category in a crisp way, use:

**AI-assisted support triage and incident investigation**

If we need the even sharper version, use:

**support-to-engineering investigation workflow for recurring customer-facing outages**

## The Rule For Product Decisions

If a feature does not make the current wedge stronger, it should not be prioritized.

The current wedge is:

**recurring customer-facing checkout and transaction-path incidents where support teams need faster, more truthful triage, reproduction, debugging guidance, and engineering handoff.**
