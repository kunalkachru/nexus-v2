# NEXUS v3 Working State

Short handoff for Codex sessions. Keep current and compact.

## Current Phase

Items 0–14: **complete**
Next phase: define the next backlog before starting another loop.

## App In One Sentence

NEXUS is an AI support-triage and incident-investigation product: noisy logs go in, a triaged investigation packet comes out, one human review gate (GUARDIAN) remains.

## Baseline State

- Branch: `master`
- `pytest tests/ -q` → **124 passed**
- `npm run browser:verify` → **10 passed**
- `./scripts/docker_fresh.sh` → passes
- `./scripts/local_enterprise_smoke.sh` → passes
- `python demo.py` → passes

## What Is Complete (items 0–8)

- UI shell: queue, incident console, inputs, replay, training, settings
- SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN pipeline (live graph path)
- REPLICA runtime substrate: `replica_runtime.py`, two Docker Compose packs
- `build_trace_summary`, `build_replica_summary`, `enrich_memory_with_runtime`, `rank_candidate_fixes_with_runtime` all implemented in `enterprise_runtime.py`
- FORGE and GUARDIAN runtime-aware posture: fully implemented in the live graph path (`_forge_node`, `_guardian_node`)
- Deployment-safe runtime behavior (fails closed without Docker)

## What Was Completed In The Last Loop (items 9–14)

See `backlog.json`. Summary:

| # | Title | Key gap |
|---|---|---|
| 9 | Runtime evidence weighting in FORGE | complete |
| 10 | Runtime-aware GUARDIAN posture | complete |
| 11 | TRACE developer handoff packet v2 | complete |
| 12 | Runtime comparison UI refinement | complete |
| 13 | Memory linkage to runtime outcomes | complete |
| 14 | End-to-end demo closure | complete |

## What Is Pending Next

The next real frontier is:

1. real app-triggered runtime replay on a Docker-capable execution host
2. stronger fresh `nxs_...` incident parity with seeded incidents
3. deeper TRACE developer packet with file-level and owner-level cues
4. multi-mitigation REPLICA comparison surfaced in-product
5. final docs/demo sync around the runtime-host model

## Two Code Paths — Critical To Understand

**STATIC/SEEDED path**:
`surface_payloads.py:build_incident_response` → reads from `incident_payloads.py` fixtures

**LIVE GRAPH path**:
`enterprise_runtime.py` LangGraph nodes (`_forge_node`, `_guardian_node`, etc.)

These paths must stay semantically aligned.

## Loop Setup Files

- `backlog.json` — completed reference backlog for items 9–14
- `AGENTS.md` — current loop rules and baseline
- `.agents/skills/nexus-backlog-loop.md` — reusable loop skill
- `docs/LOOPS_RUNBOOK.md` — operator-facing guide and prompt templates
- `BLOCKERS.md` — blocker log if a future loop gets stuck

## Most Important Files For The Next Phase

| File | Why |
|---|---|
| `server/services/enterprise_runtime.py` | live path runtime, trace, forge, guardian behavior |
| `server/services/replica_runtime.py` | bounded pack execution and Docker-backed replay substrate |
| `server/services/incidents.py` | live incident context assembly and packaged app path |
| `frontend/static/api.js` | fresh incident fallback synthesis |
| `frontend/static/incident.js` | visible incident narrative |
| `tests/e2e/browser-verification.spec.js` | browser truthfulness and flagship UX |
| `scripts/local_enterprise_smoke.sh` | Docker-path confidence checks |

## Loop Recommendation

Do not start another loop until a new backlog file is written for the next phase.
