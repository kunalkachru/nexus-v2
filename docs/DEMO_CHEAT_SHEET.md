# NEXUS v2 Demo Cheat Sheet

Current as of 2026-06-05.

This is the short live-demo reference for the current product story.
Use it when you need the fastest, clearest path through the product.

For the full operating picture, use [FINAL_SUBMISSION_GUIDE.md](/Users/kunalkachru/Documents/nexus-v3/docs/FINAL_SUBMISSION_GUIDE.md).

## One-Line Pitch

NEXUS v2 is an AI-assisted support triage and incident investigation product that turns noisy production evidence into a prepared remediation case before one final human review point.

## Product Promise

The story to prove in the demo is:

- a support team does not have to manually relay logs and evidence across multiple tiers
- the system triages the case, investigates likely cause, and prepares the next action
- one human reviewer approves, blocks, or requests a change only after the case is structured

## Current Shipped Agent Flow

`SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

Meaning:

- `SENTINEL` triages and frames the case
- `PRISM` investigates likely cause and historical context
- `REPLICA` runs bounded sandbox runtime testing to validate diagnosis and mitigations
- `TRACE` prepares investigation depth and developer handoff packet
- `FORGE` prepares remediation with runtime-weighted candidate ranking
- `GUARDIAN` governs the final decision, enriched by runtime validation

## Key Innovation: Runtime Evidence Weighting

The runtime layer (REPLICA) feeds outcome classes back into FORGE and GUARDIAN:

- `resolved` — mitigation fully cleared the failure in sandbox
- `improved` — mitigation improved behavior but did not fully resolve
- `inferred_only` — no runtime-backed evidence yet

This outcome class shapes runbook selection priority and GUARDIAN's risk classification.

## Flagship Use Case

Use this story consistently:

**customer-facing checkout outage caused by timeout and retry amplification after dependency degradation and recent deploy ambiguity**

Why this is the best demo:

- obvious business impact
- believable logs
- unclear ownership at first glance
- meaningful role for memory and prior issues
- strong future fit for reproduction and debugging
- clear final review need before action

## Public URL

- [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)

## Safest Demo Mode

- default mode is deterministic
- no project OpenAI key is exposed
- live reasoning is optional through a user-supplied key

## INC001 vs INC002: Runtime Evidence in Action

| Aspect | INC001 (Timeout Cascade) | INC002 (Pool Exhaustion) |
|--------|------------------------|------------------------|
| **Diagnosis** | Runaway retry storm → worker exhaustion | Leaked sessions → pool starvation |
| **REPLICA Status** | reproduced | reproduced |
| **Best Mitigation** | Circuit breaker + cap retries to 1 | Terminate orphaned sessions + restart |
| **Outcome Class** | resolved (confidence_delta 0.08) | resolved (confidence_delta 0.06) |
| **FORGE Cites** | "resolved in the bounded runtime" | "resolved in the bounded runtime" |
| **GUARDIAN Risk** | LOW (resolved→drops high→medium/low) | MEDIUM (improved/resolved keeps medium) |
| **Approval** | Operator level | Operator level |
| **Key Difference** | Retry path fully halted | Pool capacity restored |

Both incidents show the complete runtime flow: REPLICA validates the hypothesis, FORGE weights by outcome, GUARDIAN adjusts risk and confidence accordingly.

## Fastest Demo Flow

1. Open `/inputs` or use `/incident?nexus_incident_id=INC001`
2. Explain each stage: SENTINEL (severity) → PRISM (root cause) → REPLICA (validated outcome)
3. Show TRACE investigation depth and suggested modules
4. Show FORGE reasoning citing runtime evidence
5. Show GUARDIAN risk classification adjusted by runtime validation
6. Click `Approve runbook`
7. Show memory enrichment (why_now_fit for matching runbooks)

## What To Say On Each Screen

### Inputs

- “This is the front door for messy production evidence.”
- “Instead of a support engineer manually relaying logs, the system converts them into a structured case immediately.”

### Incident Detail

- “This is the main operator workspace.”
- “The product is reducing manual escalation work before a human reviewer is pulled in.”
- “SENTINEL frames the case, PRISM investigates it, FORGE prepares the action, and GUARDIAN governs the final decision.”

### Training

- “This page shows how the latest live triage connects to the broader runtime and learning baseline.”
- “It is not just a chart page. It closes the loop between one real incident and the product’s reusable memory and runtime quality.”

## Expected Good Outcomes

- raw-log submission redirects into a populated `nxs_...` incident
- the incident reads like a prepared support triage packet
- Guardian approval visibly changes the execution state
- Training shows the latest live triage and the broader runtime story together

## What Not To Overclaim

Do not present the current product as:

- fully autonomous remediation
- a universal debugger
- arbitrary VM reproduction for every stack

Present it as:

- a support triage and investigation product today
- with a clear path toward reproduction and debugging support

## Local Commands

```bash
./scripts/docker_fresh.sh
python demo.py
pytest tests/ -v
npm run browser:verify
```
