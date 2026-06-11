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

The first loop backlog (`items 9–14`) is complete.

If you want to continue now, the next backlog should cover:

1. app-triggered runtime replay on a Docker-capable execution host
2. fresh `nxs_...` incident parity with `INC001` and `INC002`
3. deeper TRACE developer handoff packet
4. multi-mitigation REPLICA comparison
5. final runtime-host demo and docs closure

## Before Starting A Loop

Make sure the agent reads:

1. [AGENTS.md](/Users/kunalkachru/Documents/nexus-v3/AGENTS.md)
2. [WORKING_STATE.md](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md)
3. the active backlog file

Recommended local checks before starting:

```bash
git status
pytest tests/ -q
npm run browser:verify
python demo.py
```

If the loop will touch the packaged app path, also run:

```bash
./scripts/docker_fresh.sh
BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

## How To Start A Loop In Codex

1. Open the repo root.
2. Make sure your backlog file exists and has ordered `pending` items.
3. Start a new Codex thread in this repo.
4. Paste a prompt like this:

```text
Read AGENTS.md, WORKING_STATE.md, and <backlog file>.
Run a commit-and-continue loop against the backlog.

Rules:
- always pick the first pending item
- read listed files before editing
- run every listed test gate
- mark items done only after gates pass
- commit once per completed item
- do not stop between items
- if blocked after repeated attempts, mark the item blocked and explain why
```

5. Let the agent run until the backlog is done or blocked.

## How To Start A Loop In Claude

Use the same flow, but be stricter about grounding:

```text
Read AGENTS.md, WORKING_STATE.md, and <backlog file> completely before coding.
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
Browser verification must stay green and the incident page must remain legible for both INC001 and INC002.
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
docs: tighten loop runbook and agent instructions
```

## How To Monitor A Running Loop

Watch for four failure patterns:

1. The agent is editing before it has read the target files.
2. The agent is claiming success without fresh test output.
3. The agent is broadening scope beyond the backlog item.
4. The agent is blurring scaffold-only inference with validated runtime evidence.

If any of those happen, stop the run and reset the backlog item state before resuming.

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

## Current Reality

As of the latest validated state:

- seeded and live incident narratives distinguish scaffold-only versus runtime-backed evidence
- browser verification is green
- Docker smoke is green
- runtime replay inside the packaged app is still not truly end-to-end; it requires a Docker-capable execution host outside the app container

That last point is the correct next loop frontier.
