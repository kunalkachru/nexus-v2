# NEXUS v2 Final Submission Guide

Current as of 2026-06-05.

This is the primary operating guide for presenting and validating the shipped NEXUS product with the current narrative baseline.

## Submission Summary

NEXUS v2 is a public-safe support triage and incident investigation product built around four visible specialists:

1. `SENTINEL` frames the case
2. `PRISM` investigates likely cause and prior context
3. `FORGE` prepares the remediation path
4. `GUARDIAN` governs the final human review point

The submission is designed to prove one idea:

**noisy production evidence can be turned into one triaged, investigated, remediation-ready case before final human review.**

## What Is Actually Shipped

The shipped repo includes:

- a FastAPI backend
- a multi-page frontend
- deterministic-by-default incident reasoning
- optional request-scoped live reasoning using a user-supplied OpenAI key
- visible queue, incident, history, replay, and training surfaces
- memory overlays for similar incidents, runbooks, and unresolved work
- Docker packaging for Hugging Face Spaces
- automated tests and browser verification

## What The Product Is Claiming Today

The current product claims:

- support-triage workflow compression
- visible evidence-backed investigation
- memory-backed incident review
- one governed human review point

The current product does not claim to have fully shipped:

- arbitrary VM-based reproduction
- universal code debugging
- autonomous production healing

Those are the next product layers represented by `REPLICA` and `TRACE`.

## Why Reviewers Should Care

This is stronger than a generic AI demo because:

- it solves a real support-triage overhead problem
- it makes the workflow visible instead of hiding it in one opaque answer
- it is safe to deploy publicly
- it has a believable expansion path into reproduction and debugging support

## Product Narrative

The strongest way to present NEXUS is:

- support engineers and triage responders waste too much time relaying logs and evidence manually
- NEXUS turns that into one prepared case
- the operator reviews a structured incident, not raw chaos

The strongest flagship scenario is:

**customer-facing checkout outage caused by timeout and retry amplification after dependency degradation and recent deploy ambiguity**

## Public URLs

### Production

- Hugging Face Space: [https://huggingface.co/spaces/kunalkachru23/nexus](https://huggingface.co/spaces/kunalkachru23/nexus)
- Public app URL: [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)

### Staging

- Hugging Face Space: [https://huggingface.co/spaces/kunalkachru23/nexus-staging](https://huggingface.co/spaces/kunalkachru23/nexus-staging)
- Public app URL: [https://kunalkachru23-nexus-staging.hf.space](https://kunalkachru23-nexus-staging.hf.space)

## Runtime Posture

The public deployment is intentionally safe by default:

- deterministic by default
- no server-side `OPENAI_API_KEY` required
- optional user-supplied key only
- user key stored only in browser session
- user key masked in UI
- user key sent only on the requests that need it

## Core Product Surfaces

### Inputs

Purpose:

- accept messy production evidence quickly
- turn raw logs into a structured case

### Incident Detail

Purpose:

- show the support-triage handoff
- show how a messy case becomes a prepared action packet
- keep Guardian as the final review surface

### Training

Purpose:

- connect the latest live triage to broader runtime quality and learning posture

### Supporting Surfaces

- `/queue`
- `/history`
- `/replay`
- `/settings`

## Fastest Demo Path

1. Open `/inputs`
2. Click `Load example logs`
3. Click `Submit raw logs`
4. Let the app redirect to the created incident
5. Explain the support-triage handoff:
   - `SENTINEL`
   - `PRISM`
   - `FORGE`
   - `GUARDIAN`
6. Explain how the system reduced manual relay work
7. Show `GUARDIAN` as the final review point
8. Click `Approve runbook`
9. Show the outcome
10. Open `/training`
11. Show the latest run and the broader runtime story

## Expected Demo Outcomes

### Inputs to Incident

Expected:

- a new `nxs_...` incident is created
- the browser redirects to a populated incident
- title, reasoning, and Guardian posture are visible

### Incident Review

Expected:

- the incident page feels like a triage and investigation workspace
- likely issue and likely next action are understandable
- Guardian is visibly in control of the final step

### Guardian Action

Expected:

- `Approve runbook` changes Guardian to approved
- execution changes to executed
- the result area updates visibly

### Training

Expected:

- the latest live triage is visible when one exists
- runtime and learning summaries remain understandable

## Local Run Instructions

### Fresh Docker Start

```bash
./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

### Direct Server Start

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Demo Script

```bash
python demo.py
```

## Verification Commands

```bash
pytest tests/ -v
npm run browser:verify
python demo.py
./scripts/docker_fresh.sh
```

## Manual Runbook

Use this sequence for manual verification:

1. open `/inputs`
2. create a fresh incident from raw logs
3. inspect the incident
4. approve the runbook
5. open `/training`
6. open `/history`
7. optionally review `/replay`

## Source Of Truth Docs

- [README.md](/Users/kunalkachru/Documents/nexus-v3/README.md)
- [PRODUCT_STRATEGY_AND_GTM.md](/Users/kunalkachru/Documents/nexus-v3/docs/PRODUCT_STRATEGY_AND_GTM.md)
- [SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md)
- [VISUAL_ARCHITECTURE_AND_FLOWS.md](/Users/kunalkachru/Documents/nexus-v3/docs/VISUAL_ARCHITECTURE_AND_FLOWS.md)
