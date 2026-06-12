# NEXUS Agent Loop Instructions

Use this file when running Codex or Claude in a commit-and-continue loop against a written backlog.

## Current Product State

- Product shape: support triage and incident investigation workspace
- Flagship incidents:
  - `INC001` checkout timeout / retry amplification
  - `INC002` checkout DB pool exhaustion / session leak
- Current validated baseline (post items 61–68 hardening phase):
  - `pytest tests/ -q` -> `141 passed`
  - `npm run browser:verify` -> `11 passed`
  - `python demo.py` -> passes
  - `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` -> passes
  - `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` -> passes
  - **Premium visual system** across queue, inputs, incident, training, replay
  - **Improved incident console** with clearer operator story from triage to Guardian approval
  - **Fresh incident parity** with explicit scaffold-only vs runtime-backed language
  - **Ordered INC001 debugger flow** with concrete checkpoints and expected state transitions
  - **Runtime-host visibility** in UI showing which host executed replay
  - **Operator-triggered bounded replay** from the incident console with live refresh
  - **Post-approval outcome capture** visible in incident detail and training page with memory context
  - **Operator-to-engineering demo closure** with updated owner walkthrough and post-approval flow
  - **Engineering handoff export** for support-to-engineering case packaging
  - **Bounded debugger parity** for both `INC001` and `INC002`
  - **Operator ROI and audit surface** plus the larger visual reinvention pass
  - **Delivery-target exports, governance packet export, and runtime guardrail surfaces** across the enterprise workflow

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
2. the active backlog file for the next execution frontier
3. any referenced docs for the target phase

## Required Backlog Shape

Each backlog item should include:

- `id`
- `title`
- `priority`
- `status` (`pending`, `done`, or `blocked`)
- `description`
- `implementation_tasks`
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
9. When the backlog reaches zero pending items:
   - refresh `AGENTS.md`, `WORKING_STATE.md`, and `docs/LOOPS_RUNBOOK.md`
   - mark the finished backlog file as completed in `WORKING_STATE.md`
   - create the next backlog file before starting another loop
   - do not claim the phase complete until those control docs are current

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
- Any packaged-app runtime claim must be verified through the `:7860` Docker path before the item is marked done.
- Keep seeded/static and live incident paths semantically aligned.
- Never leave `AGENTS.md`, `WORKING_STATE.md`, or `docs/LOOPS_RUNBOOK.md` stale after a backlog reaches zero pending items.

## Current Code Map

| Area | File |
|---|---|
| Seeded/static incident path | `server/services/surface_payloads.py` |
| Live graph incident path | `server/services/enterprise_runtime.py` |
| Runtime pack substrate | `server/services/replica_runtime.py` |
| Packaged app replay + incident context | `server/services/incidents.py` |
| Runtime host service | `runtime_host/server/app.py` |
| Incident fixtures | `server/incident_payloads.py` |
| Incident UI | `frontend/incident.html` |
| Incident client logic | `frontend/static/incident.js` |
| Shared UI data loading and fallback synthesis | `frontend/static/api.js` |
| Global UI styling | `frontend/static/styles.css` |
| API contract tests | `tests/test_api_contract.py` |
| App tests | `tests/test_app.py` |
| Runtime tests | `tests/test_replica_runtime.py` |
| Browser verification | `tests/e2e/browser-verification.spec.js` |
| Docker-path smoke | `scripts/local_enterprise_smoke.sh` |

## Current Frontier

The `15–60` backlog is complete.

The active next execution backlog is `backlog-61-plus.json`.

This phase is a hardening and truthfulness checkpoint for the bounded support-triage product.

## Reality Check

Implemented now:

- two real bounded REPLICA runtime packs
- packaged-app replay delegation through a Docker-capable runtime host
- runtime trust and audit packet
- replay lifecycle and replay history visibility
- bounded TRACE ownership and trace-to-code packet for both flagship outages
- bounded mitigation ladder across REPLICA, FORGE, and GUARDIAN
- one bounded debugger flow for `INC001`
- one bounded debugger flow for `INC002`
- improved fresh-incident reasoning that distinguishes scaffold-only versus runtime-backed evidence
- runtime-host visibility in the operator UI
- post-approval outcome capture and memory-linked execution context
- end-to-end operator-to-engineering walkthrough that matches the shipped product flow
- engineering handoff export and operator ROI surface
- delivery-target export packages, replay-driven mitigation matrix, runtime guardrails, governance export, and pack validator tooling

Not implemented yet:

- arbitrary environment reproduction
- universal code debugging across arbitrary stacks
- autonomous multi-step production remediation
- arbitrary external ticketing or messaging integrations

## Reference

See [docs/LOOPS_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/LOOPS_RUNBOOK.md) for the operator-facing guide and prompt templates.
