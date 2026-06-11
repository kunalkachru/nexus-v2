# NEXUS Agent Loop Instructions

Use this file when running Codex or Claude in a commit-and-continue loop against a written backlog.

## Current Product State

- Product shape: support triage and incident investigation workspace
- Flagship incidents:
  - `INC001` checkout timeout / retry amplification
  - `INC002` checkout DB pool exhaustion / session leak
- Current validated baseline:
  - `pytest tests/ -q` -> `124 passed`
  - `npm run browser:verify` -> `10 passed`
  - `python demo.py` -> passes
  - `./scripts/docker_fresh.sh` -> passes
  - `BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` -> passes

## What Loops Are For

Loops are for draining a backlog file without stopping after every slice.

Use a loop only when all three are true:

1. The work is already decomposed into ordered backlog items.
2. Each item has concrete completion criteria.
3. Each item has explicit test gates.

If those are not true, write the backlog first. Do not improvise broad product work in a loop.

## Loop Inputs

Before starting, the agent must read:

1. `WORKING_STATE.md`
2. the active backlog file, for example `backlog.json` or `backlog-next.json`
3. any referenced docs for the target phase

## Required Backlog Shape

Each backlog item should include:

- `id`
- `title`
- `priority`
- `status` (`pending`, `done`, or `blocked`)
- `description`
- `done_when`
- `test_gates`
- `files_likely_touched`

## The Loop

Run this exactly:

1. Read the backlog file.
2. Find the first item with `status == "pending"`.
3. If none remain, stop and report backlog completion.
4. Read every file listed in `files_likely_touched`.
5. Implement the smallest complete slice that satisfies `done_when`.
6. Run every command in `test_gates`.
7. If all gates pass:
   - update the item to `done`
   - commit the slice
   - continue to the next pending item
8. If gates fail:
   - debug and retry
   - after repeated failure, mark the item `blocked`, document the blocker, commit the backlog state, then continue only if explicitly allowed by the backlog rules

## Commit Rules

- Commit once per completed backlog item.
- Keep commit messages intentional.
- Recommended format:

```text
feat(#<id>): <title>

- what changed
- tests: <key gates that passed>
```

## Hard Rules

- Never mark an item `done` without running its listed test gates.
- Never skip browser or Docker gates when they are listed.
- Never rename existing API response keys unless the backlog item explicitly requires it.
- Never treat scaffold-only inference as runtime validation.
- Never stop for confirmation between items unless the backlog says to pause.
- Never overwrite unrelated user work.

## Current Code Map

| Area | File |
|---|---|
| Seeded/static incident path | `server/services/surface_payloads.py` |
| Live graph incident path | `server/services/enterprise_runtime.py` |
| Runtime pack substrate | `server/services/replica_runtime.py` |
| Incident fixtures | `server/incident_payloads.py` |
| Incident UI | `frontend/incident.html` |
| Incident client logic | `frontend/static/incident.js` |
| Incident data loading and fallback synthesis | `frontend/static/api.js` |
| API contract tests | `tests/test_api_contract.py` |
| App tests | `tests/test_app.py` |
| Runtime tests | `tests/test_replica_runtime.py` |
| Browser verification | `tests/e2e/browser-verification.spec.js` |

## Current Frontier

The `9–14` backlog is complete. New loop runs should target a new backlog for the next frontier:

1. real app-triggered runtime replay on a Docker-capable execution host
2. stronger parity for fresh `nxs_...` incidents versus seeded incidents
3. deeper TRACE developer packet with file-level and owner-level cues
4. multi-mitigation REPLICA comparison surfaced in the decision packet
5. final demo/docs sync for the runtime-host model

## Reference

See [docs/LOOPS_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/LOOPS_RUNBOOK.md) for the operator-facing guide and prompt templates.
