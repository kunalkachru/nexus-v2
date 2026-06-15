# NEXUS Loop Memory Contract

This file exists to improve loop discipline, not to let the agent invent new product strategy.

Use it before any long-running Claude or Codex loop.

## What A Loop Is Allowed To Learn

A loop may carry forward only:

- execution discipline learned from repeated failures or validations
- repo-specific safety rules already proven in this codebase
- test and verification requirements that must not be skipped
- truthfulness constraints about runtime-backed versus inferred-only behavior
- backlog hygiene needed to resume without repeating work

## What A Loop Is Not Allowed To Learn

A loop must not:

- invent new roadmap items or reorder the roadmap on its own
- broaden scope beyond the active backlog item
- treat generated text as evidence
- convert scaffold-only inference into runtime validation language
- create product strategy, GTM, or architecture changes without an explicit backlog or owner-approved plan
- write speculative "lessons" that are not tied to observed repo behavior, test output, or established control-doc rules

## How To Use This File

Before coding:

1. read this file
2. read `AGENTS.md`
3. read `WORKING_STATE.md`
4. read `docs/LOOPS_RUNBOOK.md`
5. read the active backlog and execution map

During execution:

- use this file only as a guardrail layer
- do not treat it as authority over the backlog
- if a rule here conflicts with the backlog, stop and surface the conflict

After an item completes:

- update backlog status first
- commit the item
- only append a new lesson if it was learned from a repeated failure, repeated verification need, or a real control-doc correction

## Entry Format For Future Lessons

Only add short entries in this format:

```text
Date:
Item:
Observed issue:
Verified rule:
Evidence:
```

If there is no concrete evidence, do not add the lesson.

## Current Verified Rules

1. Any packaged-app runtime claim must be verified through the Docker app on `:7860` before the item is marked done.
2. Scaffold-only evidence must stay labeled as scaffold-only.
3. Seeded and live incident paths must stay semantically aligned.
4. Do not mark a backlog item done until its listed test gates pass.
5. Update backlog status immediately after the item passes its gates so the same loop can resume from the next pending item.
6. Refresh `AGENTS.md`, `WORKING_STATE.md`, and `docs/LOOPS_RUNBOOK.md` when a backlog is fully closed.

## Current Learned Entries

No additional learned entries recorded yet.
