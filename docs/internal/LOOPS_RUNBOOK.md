# NEXUS Loops Runbook

Quick reference for autonomous implementation loops in this repository.

## When to Use a Loop

Use a loop only when all three are true:

1. The work is already decomposed into ordered backlog items.
2. Each item has concrete completion criteria.
3. Each item has explicit test gates.

If those are not true, write the backlog first.

## Required Inputs

Before starting a loop, read:

1. [AGENTS.md](/Users/kunalkachru/Documents/nexus-v3/AGENTS.md)
2. [WORKING_STATE.md](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md)
3. the active backlog file under [docs/internal](/Users/kunalkachru/Documents/nexus-v3/docs/internal/)

If you are looking for support-operator product guidance rather than engineering loop guidance, use [OPERATOR_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/internal/OPERATOR_RUNBOOK.md).

## Loop Procedure

1. Read the backlog file.
2. Find the first item with `status == "pending"`.
3. Read every file listed in `files_likely_touched`.
4. Implement the smallest complete slice that satisfies `done_when`.
5. Run every command in `test_gates`.
6. If all gates pass:
   - mark the item `done`
   - commit once for that item
   - continue
7. If gates fail:
   - debug and retry
   - after the second failed attempt, mark the item `blocked` and document the blocker

## Closeout Rules

When the backlog reaches zero pending items:

- refresh `AGENTS.md`
- refresh `WORKING_STATE.md`
- refresh this runbook if the loop process changed
- mark the finished backlog as completed in `WORKING_STATE.md`
- create the next backlog before beginning another loop

## Mandatory Regression Floor

Unless a backlog item specifies otherwise, preserve this baseline:

- `pytest tests/ --ignore=tests/test_production_gate3.py -q`
- `npm run browser:verify`
- `bash scripts/test-live.sh https://nexus-triage.duckdns.org`
- `bash scripts/run-release-gate.sh`
