# NEXUS Demo Cheat Sheet

Current as of 2026-06-15.

Use this for the shortest truthful product demo.

## One-Line Pitch

NEXUS compresses the support-to-engineering relay for recurring customer-facing outages by turning noisy evidence into a runtime-aware, debugging-guided, engineering-ready case before one final human review point.

## Product Flow

`SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

Meaning:

- `SENTINEL` frames the incident
- `PRISM` diagnoses likely cause and retrieves prior context
- `REPLICA` validates bounded replay when a curated pack exists
- `TRACE` prepares debugging and handoff cues
- `FORGE` ranks mitigations using the available evidence
- `GUARDIAN` governs the final decision

## Flagship Story

Default to `INC001`:

**customer-facing checkout timeout caused by retry amplification after dependency degradation**

Why this works:

- clear business impact
- believable logs
- meaningful prior-incident reuse
- bounded replay and debugger story are both easy to explain

## Fastest Flow

1. open `/inputs`
2. load example logs
3. submit raw logs
4. open the created `nxs_...` incident
5. show issue framing, memory, replay posture, and debugger path
6. approve the runbook
7. open `/training`
8. show latest triage plus scorecard

## What To Say

### Inputs

- “This is the front door for messy support evidence.”
- “The goal is to structure the case before a human escalation chain starts.”

### Incident Detail

- “This is the operator’s coordination room.”
- “You can see what is inferred, what is runtime-backed, and what the next human decision actually is.”

### Training

- “This closes the loop between one incident and pilot-level proof.”

## Do Not Overclaim

Do not describe the current product as:

- a universal incident platform
- a universal debugger
- arbitrary environment reproduction

Describe it as:

- a bounded support-triage and investigation product
- with real replay/debugging support for curated outage families
