# NEXUS v2 Live Demo Speaker Notes

Current as of 2026-06-05.

These notes are for presenting NEXUS with the new support-triage narrative.
Use them to keep the story focused on the operator problem, not just the architecture.

## Core Story

The product is solving this problem:

- too many support and production engineers touch the same incident before anyone reaches a confident next action
- logs get pasted around
- known failures are rediscovered manually
- remediation gets drafted too late and too inconsistently

NEXUS reduces that relay chain by preparing one investigated case before the final human review point.

## Demo Structure

Move through the product in this order:

1. `Inputs`
2. created `Incident Detail`
3. `Training`
4. optional `History` or `Replay`

## 1) Inputs

### What to say

- “This is where the support-triage workflow starts.”
- “Instead of passing raw logs between multiple people, we bring noisy evidence into one system.”
- “The product normalizes that evidence before the final human reviewer ever has to step in.”

### What the audience should notice

- the raw-log intake path is clear
- the page feels like an operator entrypoint, not a toy prompt box
- the product is built around messy evidence, not clean benchmark inputs

### If asked

- explain that the current MVP starts with raw logs because that is the fastest way to prove value
- explain that the same model later expands to Slack, webhooks, and other intake channels

## 2) Incident Detail

### What to say

- “This is the core operator workspace.”
- “The system is building an action-ready support case.”
- “SENTINEL triages the case, PRISM investigates likely cause and prior history, FORGE prepares the remediation, and GUARDIAN governs the final review.”
- “The goal is not to replace human judgment. The goal is to remove the repetitive relay work before human judgment is needed.”

### What the audience should notice

- ownership and issue framing are visible
- the investigation story is readable
- memory and historical context are visible
- Guardian is clearly the final decision point

### If asked

- explain that the current shipped flow is four visible agents
- explain that the future product adds reproduction and debugging support through `REPLICA` and `TRACE`
- explain that the approval step is intentional because enterprises care about trust, policy, and auditability

## 3) Training

### What to say

- “This page shows how one live triage run connects to the broader runtime and learning story.”
- “The top of the page answers what just happened in this browser.”
- “The lower sections answer whether the system is behaving reliably and improving over time.”

### What the audience should notice

- the latest live triage is visible
- runtime quality is visible
- learning is attached to a real incident workflow, not abstract model metrics alone

### If asked

- explain that the current product exposes a visible learning story even though the strongest product value today is support-triage workflow compression
- explain that memory and retrieval are what matter most near term, with deeper training loops following behind

## 4) History

### What to say

- “History is not a dead archive.”
- “It is operational memory.”
- “Past incidents are meant to reduce repeated investigation work.”

## 5) Replay

### What to say

- “Replay is how we validate scenario quality and keep the product story repeatable.”
- “It is also how the future reproduction story becomes natural instead of bolted on.”

## Flagship Use Case

Keep returning to this:

**customer-facing checkout outage caused by timeout and retry amplification after dependency degradation and recent deploy ambiguity**

Why we use it:

- it is easy to understand
- it is expensive for a business
- it generates messy evidence
- it is the kind of recurring issue where memory, reproduction, and debugging all matter

## What Not To Say

Avoid leading with:

- “autonomous agents”
- “AI ops platform”
- “RL”
- “self-healing”

Lead with:

- support overhead
- repetitive escalation work
- faster time to confident action
- one prepared case before final review

## Closing Line

Use this if you want a short close:

- “NEXUS turns noisy production evidence into a triaged, investigated, and remediation-ready case before one final human review point.”

## Related Docs

- [README.md](/Users/kunalkachru/Documents/nexus-v3/README.md)
- [FINAL_SUBMISSION_GUIDE.md](/Users/kunalkachru/Documents/nexus-v3/docs/FINAL_SUBMISSION_GUIDE.md)
- [DEMO_WALKTHROUGH.md](/Users/kunalkachru/Documents/nexus-v3/docs/DEMO_WALKTHROUGH.md)
- [SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md)
