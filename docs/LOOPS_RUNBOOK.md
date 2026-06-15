# NEXUS Loops Runbook

This document explains how to run Codex or Claude in a controlled implementation loop against NEXUS.

## What A Loop Means Here

A loop is a disciplined backlog drain:

1. pick the next pending item
2. implement it
3. run its tests
4. commit it
5. continue without waiting for more prompts

The goal is speed without losing auditability or product truthfulness.

## When To Use Loops

Use loops when:

- the next work is already broken into ordered items
- each item has concrete completion criteria
- each item has explicit test gates

Do not start a loop against a vague objective like "improve Nexus more." Write a backlog first.

## Current Recommended Scope

The `15–85` backlog is complete.

The market-ready v1 checkpoint (items `77–85`) is finished.

The `backlog-86-plus.json` is complete (items 86–92 wedge-strengthening checkpoint).

The `backlog-93-plus.json` is now complete (items 93–100 pilot conversion and technical proof deepening).

The product is ready for real pilot evaluation with three bounded incident families, runtime-backed investigation paths, and strengthened pilot conversion surfaces.

**Completed in items 86–92:**
1. ✓ added `INC003` deploy regression / 5xx spike as the third outage family
2. ✓ deepened bounded REPLICA and TRACE support across all three families
3. ✓ improved LLM-driven triage quality with adaptive reasoning for deploy regression
4. ✓ improved agent reasoning visibility via workflow timeline
5. ✓ strengthened pilot-conversion proof with three-outage wedge narrative
6. ✓ completed wow-effect UI polish across core surfaces

The product now supports **three-outage bounded wedge** with consistent investigation workflows, runtime-backed validation, and measurable pilot readiness.

## Before Starting A Loop

Make sure the agent reads:

1. [AGENTS.md](/Users/kunalkachru/Documents/nexus-v3/AGENTS.md)
2. [WORKING_STATE.md](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md)
3. [backlog-86-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-86-plus.json)
4. [docs/POST_85_WEDGE_STRENGTHENING_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_85_WEDGE_STRENGTHENING_PLAN.md)
5. [docs/POST_85_EXECUTION_MAP.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_85_EXECUTION_MAP.md)
6. [docs/DEMO_WALKTHROUGH.md](/Users/kunalkachru/Documents/nexus-v3/docs/DEMO_WALKTHROUGH.md)

Recommended local checks before starting:

```bash
git status
pytest tests/ -q
npm run browser:verify
python demo.py
```

If the loop will touch the packaged app path, also run:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

## How To Start A Loop In Codex

1. Open the repo root.
2. Make sure your backlog file exists and has ordered `pending` items.
3. Start a new Codex thread in this repo.
4. Paste a prompt like this:

```text
Read AGENTS.md, WORKING_STATE.md, docs/POST_85_WEDGE_STRENGTHENING_PLAN.md, docs/POST_85_EXECUTION_MAP.md, docs/DEMO_WALKTHROUGH.md, and backlog-86-plus.json.
Run a commit-and-continue loop against the backlog.

Rules:
- always pick the first pending item
- read listed files before editing
- run every listed test gate
- mark items done only after gates pass
- commit once per completed item
- do not stop between items
- if blocked after repeated attempts, mark the item blocked and explain why
- keep seeded/static and live incident paths semantically aligned
- do not treat scaffold-only evidence as runtime validation
- any packaged-app runtime claim must be verified through the :7860 Docker path before the item is marked done
```

5. Let the agent run until the backlog is done or blocked.
6. When the backlog reaches zero pending items, the agent must refresh `AGENTS.md`, `WORKING_STATE.md`, and this runbook before claiming the phase complete.

## How To Start A Loop In Claude

Use the same flow, but keep the grounding stricter:

```text
Read AGENTS.md, WORKING_STATE.md, docs/LOOPS_RUNBOOK.md, docs/POST_85_WEDGE_STRENGTHENING_PLAN.md, docs/POST_85_EXECUTION_MAP.md, docs/DEMO_WALKTHROUGH.md, and backlog-86-plus.json completely before coding.
Resume from the first pending backlog item.
Drain the backlog top to bottom in a build-test-commit loop.
Do not invent scope outside the backlog.
Do not treat scaffold-only evidence as runtime validation.
Commit after each completed item with the item id in the message.
```

## Recommended Prompt Add-Ons

Use these only if relevant:

- For Docker/runtime work:

```text
Any packaged-app runtime claim must be verified through the :7860 Docker path before the item is marked done.
```

- For frontend-heavy work:

```text
Browser verification must stay green, and the key screens should remain legible for INC001, INC002, and a fresh nxs incident.
```

- For seeded-versus-live consistency:

```text
Keep seeded/static and live incident paths semantically aligned. Do not let one overclaim compared with the other.
```

## What The Agent Should Commit

One commit per backlog item.

Recommended format:

```text
feat(#<id>): <title>

- what changed
- tests: <key gates>
```

For documentation-only loop infrastructure updates:

```text
docs: refresh loop control docs for current frontier
```

## How To Monitor A Running Loop

Watch for four failure patterns:

1. The agent is editing before it has read the target files.
2. The agent is claiming success without fresh test output.
3. The agent is broadening scope beyond the backlog item.
4. The agent is blurring scaffold-only inference with validated runtime evidence.

If any of those happen, stop the run and reset the backlog item state before resuming.

## Backlog Completion Hygiene

When a backlog reaches zero pending items, do this before calling the phase complete:

1. confirm the backlog file shows every item as `done` or `blocked`
2. refresh `AGENTS.md` to the new validated baseline
3. refresh `WORKING_STATE.md` so the completed backlog is no longer listed as active
4. refresh this runbook so it points to the real next step
5. commit the cleanup separately if needed
6. only then create the next backlog file

This is mandatory. A backlog is not fully complete while the control docs still describe it as active.

## How To Resume After Interruption

1. Run `git status`.
2. Read the backlog file.
3. Find the first item still marked `pending`.
4. If there are uncommitted changes, decide whether they belong to that item.
5. Resume with the same loop prompt and explicitly say:

```text
Resume from the first pending backlog item. Do not repeat completed items.
```

## NEXUS-Specific Safety Rules

- `INC001` and `INC002` are the canonical demo incidents.
- Scaffold-only inference must be labeled as scaffold-only.
- Docker-unavailable app environments must not be described as if no runtime pack exists.
- Fresh `nxs_...` incidents can be simpler, but they must not contradict the flagship runtime story.
- Do not describe the debugger as universal or interactive unless a backlog item truly implements that.

## Market-Ready v1 Release State

As of the completion of items 77–85:

- **Architecture:** SENTINEL → PRISM → FORGE → GUARDIAN with REPLICA and TRACE bounded to curated packs
- **Seeded and live paths:** Both distinguish scaffold-only versus runtime-backed evidence
- **Deployment:** Docker packaged app on `:7860` with runtime-host relay delegation
- **Testing:** 145 pytest cases pass, 11 browser verification cases pass, demo.py passes, Docker smoke passes
- **Incidents:** INC001 (checkout timeout/retry) and INC002 (DB pool exhaustion) are fully bounded with reproduction and debugging
- **Operator experience:** Training page shows ROI metrics, replay evidence, memory reuse, governance posture
- **Buyer proof:** Before/after narrative with measured relay reduction, triage time savings, approval turnaround
- **Visual design:** Market-facing premium UI with gradient typography, sophisticated shadows, strong hierarchy
- **Product boundaries:** Narrow support-triage workflow, curated incident families, explicit human approval, no autonomous production remediation

The product is ready for v1 release as a narrow, credible support-triage system for recurring checkout and transaction-critical incidents.

The [backlog-86-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-86-plus.json) is now complete (items 86–92 finished). 

The product has been strengthened from two-incident to three-incident bounded wedge with consistent investigation workflows and pilot-ready presentation materials. No further platform work is scheduled until broader strategic direction is decided.
