# NEXUS Agent Control Instructions

Use this file as the top-level control surface for Codex or Claude working in this repo.

## Current Product State

- Product shape: support triage and incident investigation workspace
- Flagship incidents (five-family wedge):
  - `INC001` checkout timeout / retry amplification
  - `INC002` checkout DB pool exhaustion / session leak
  - `INC003` deploy regression / 5xx spike
  - `INC005` queue / worker backlog affecting transaction completion
  - `INC007` auth dependency slowdown / token validation failures
- Current validated baseline (Updated 2026-06-23):
  - `pytest tests/ --ignore=tests/test_production_gate3.py -q` -> `489 passed` (all tests pass; Docker-coupled replica test runs or skips based on environment)
  - `npm run browser:verify` -> `16 passed`
  - `python demo.py` -> passes (five-family seeded walkthrough plus live graph demo)
  - `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` -> passes
  - `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` -> passes (all smoke checks)
  - **Master setup and testing guide** created with comprehensive coverage
  - **Documentation thoroughly reviewed** and cleaned (50 → 38 active docs)
  - **All environment variables** documented with examples
  - **100+ feature validation** checkpoints created
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
  - **Deepened runtime evidence weighting** showing explicitly why each action won, with clear evidence posture and residual-risk semantics
  - **Weighted evidence explanation** across inference, memory, and runtime sources with measurable confidence boosts
  - **Pilot operations kit** including tenant setup, weekly reviews, and closeout procedures
  - **FR2 repeatable enterprise pilot closure** with bounded onboarding, measured proof, and stronger engineering trust
  - **Guided stakeholder demo bundles** on `/inputs` for all five supported outage families
  - **Fresh incident demo-origin carryover** from `/inputs` into the incident workspace
  - **Queue-first incident access improvements** for both seeded and fresh review paths
  - **Incident-workspace progressive disclosure** that keeps the top decision path primary
  - **Top-brief-first landing** for fresh `nxs_...` incidents opened from `/inputs`
  - **Expanded browser-truth coverage** across queue, inputs, incident, training, and settings

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
   - refresh `AGENTS.md`, `WORKING_STATE.md`, and `docs/internal/LOOPS_RUNBOOK.md`
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

## Governance Rules for Autonomous Sessions

These rules apply to all Claude Code autonomous loop sessions:

- Launch with: `claude --max-turns 30` (hard turn cap)
- Set before launching: `export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`
- 2-failure retry limit per item — mark blocked and move on, never retry a third time
- Checkpoint and report every 3 completed items
- Never call ScheduleWakeup under any circumstances
- Use `--dangerously-skip-permissions` only for bounded repo work (not system commands)
- `/compact` and `/context` must be typed directly by the user — cannot be invoked via bash tool calls
- Compact at 50% context without waiting to be told

## Hard Rules

- Never mark an item `done` without running its listed test gates.
- Never skip browser or Docker gates when they are listed.
- Never rename existing API response keys unless the backlog item explicitly requires it.
- Never treat scaffold-only inference as runtime validation.
- Never stop for confirmation between items unless the backlog says to pause.
- Never overwrite unrelated user work.
- Any packaged-app runtime claim must be verified through the `:7860` Docker path before the item is marked done.
- Keep seeded/static and live incident paths semantically aligned.
- Never leave `AGENTS.md`, `WORKING_STATE.md`, or `docs/internal/LOOPS_RUNBOOK.md` stale after a backlog reaches zero pending items.

## Production Deployments

| Environment | URL | Auto-deploys on |
|---|---|---|
| Oracle Cloud | https://nexus-triage.duckdns.org | git push origin master via GitHub Actions |
| Render | https://nexus-uny5.onrender.com | git push origin master |

SSH access: `ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239`
Smoke test: `bash scripts/test-live.sh https://nexus-triage.duckdns.org`
Release gate: `bash scripts/run-release-gate.sh`

## Current Code Map

| Area | File |
|---|---|
| Seeded/static incident path | `server/services/surface_payloads.py` |
| Live graph incident path | `server/services/enterprise_runtime.py` |
| Runtime pack substrate | `server/services/replica_runtime.py` |
| Packaged app replay + incident context | `server/services/incidents.py` |
| Runtime host service | `Dockerfile.runtime-host` + `server/services/replica_runtime.py` |
| Incident fixtures | `server/incident_payloads.py` |
| Incident UI | `frontend/incident.html` |
| Incident client logic | `frontend/static/incident.js` |
| Shared UI data loading and fallback synthesis | `frontend/static/api.js` |
| Global UI styling | `frontend/static/dashboard.css` |
| API contract tests | `tests/test_api_contract.py` |
| App tests | `tests/test_app.py` |
| Runtime tests | `tests/test_replica_runtime.py` |
| Browser verification | `tests/e2e/browser-verification.spec.js` |
| Docker-path smoke | `scripts/local_enterprise_smoke.sh` |

## Current Frontier

Active backlog:

- `docs/internal/backlog-engineering-cleanup-sprint.json`

Current phase:

- engineering cleanup sprint

The current shipped baseline is:

- five bounded outage families
- bounded REPLICA runtime packs
- bounded TRACE debugging and handoff packets
- packaged runtime-host relay
- operator, pilot, and buyer proof surfaces

The most recently closed implementation target was:

- pilot UX hardening and live-intake trust pass
- queue and incident-access usability
- incident workspace progressive disclosure
- six-agent relay legibility v2
- stronger fresh-incident evidence provenance
- guided raw-log demo path refinement
- final browser-truth and operator-doc sync
- documentation and demo-truth consistency

## Reality Check

Implemented now:

- three real bounded REPLICA runtime packs (auth-redis for INC001, postgres for INC002, catalog for INC003)
- packaged-app replay delegation through a Docker-capable runtime host
- runtime trust and audit packet
- replay lifecycle and replay history visibility
- bounded TRACE ownership and trace-to-code packet for all three outage families
- bounded mitigation ladder across REPLICA, FORGE, and GUARDIAN
- one bounded debugger flow for `INC001` (timeout/retry amplification)
- one bounded debugger flow for `INC002` (DB pool exhaustion)
- one bounded runtime pack for `INC003` (deploy regression with rollback path)
- improved fresh-incident reasoning that distinguishes scaffold-only versus runtime-backed evidence
- runtime-host visibility in the operator UI
- post-approval outcome capture and memory-linked execution context
- end-to-end operator-to-engineering walkthrough that matches the shipped product flow
- engineering handoff export and operator ROI surface
- delivery-target export packages, replay-driven mitigation matrix, runtime guardrails, governance export, and pack validator tooling
- durable replay execution history through the artifact layer
- shared evidence-posture language across seeded and live incident paths
- stricter debugger evidence contract and fresh-incident truth gates
- pilot-ready case lifecycle, downstream sends, tenant-aware routing, engineering feedback, admin visibility, and buyer-facing ROI surfaces
- route transition and submit-progress UX improvements for the `/incident -> /inputs -> fresh incident` flow
- truthful six-agent baton relay in the incident console with explicit handoff_flow contract
- `REPLICA` and `TRACE` as first-class visible relay agents in the UI with bounded scope messaging
- handoff packet cards showing emitted/received packets between agents
- chronological handoff ledger with event details and status
- clearer transfer animations with pulse effects and active state highlighting
- demo-mode handoff chain replay controls for operator walkthroughs
- curated `/inputs` demo bundles for the five bounded outage families
- additive demo-origin guidance on fresh `nxs_...` incidents created from curated bundles

Not implemented yet:

- arbitrary environment reproduction
- universal code debugging across arbitrary stacks
- autonomous multi-step production remediation
- broad third-party workflow coverage beyond the current bounded integrations
- fully durable active runtime queue orchestration beyond app-local in-flight state
- multi-tenant production hardening beyond the current narrow v1 release baseline
- enterprise-grade auth, security, observability, and onboarding maturity beyond the current wrapped five-family strategy

## Checkpoint Note

The five-family market-ready baseline remains wrapped for the present strategy.

The most recent narrow phase also closed cleanly:

- `/inputs` now supports curated stakeholder demo bundles
- fresh incidents can preserve bundle context in the incident workspace
- the owner-facing walkthrough now matches the shipped demo flow

The next active narrow phase is intentionally still inside the same wedge:

- engineering cleanup sprint in progress via `docs/internal/backlog-engineering-cleanup-sprint.json`

Boundaries remain:

- `REPLICA` is still bounded, not a universal reproduction system
- `TRACE` is still bounded, not a universal debugger
- no new outage families or platform broadening landed in this phase

## Reference

See [docs/internal/LOOPS_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/internal/LOOPS_RUNBOOK.md) for the operator-facing loop guide.
