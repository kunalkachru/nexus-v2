# NEXUS Working State

Short handoff for Codex or Claude sessions. Keep current and compact.

## Product State

NEXUS is an AI-assisted support-to-engineering investigation product: noisy logs go in, a triaged investigation packet comes out, and one governed human review gate remains.

## Baseline

- Branch: `master`
- Current bounded wedge: five supported outage families
- `pytest tests/ -q` → target baseline: **169 passed**
- `npm run browser:verify` → target baseline: **16 passed**
- `python demo.py` → demo incidents complete
- `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` → passes
- `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` → passes

## Supported Bounded Families

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike
4. `INC005` queue / worker backlog affecting transaction completion
5. `INC007` auth dependency slowdown / token validation failures

## Real Versus Bounded

Real today:

- bounded REPLICA runtime replay for curated packs
- bounded TRACE debugging and engineering handoff
- runtime-host relay for the packaged app
- runtime-backed versus inference-first posture in seeded and live paths
- approval, audit, delivery, and pilot proof surfaces

Still bounded:

- reproduction only works for curated packs
- TRACE is not a universal debugger
- execution remains governed and human-approved

## Control Surface

- [AGENTS.md](/Users/kunalkachru/Documents/nexus-v3/AGENTS.md)
- [docs/README.md](/Users/kunalkachru/Documents/nexus-v3/docs/README.md)
- [docs/public/README.md](/Users/kunalkachru/Documents/nexus-v3/docs/public/README.md)
- [docs/internal/README.md](/Users/kunalkachru/Documents/nexus-v3/docs/internal/README.md)

## Current Frontier

- Active backlog: `backlog-145-plus.json` in progress
- Active phase: documentation and demo-truth consistency pass
- Status: items `145-147` are complete; internal control-surface sync and final checkpoint remain

Completed phases:

- `backlog-117-plus.json` closed
- `backlog-125-plus.json` closed
- `backlog-131-plus.json` closed
- `backlog-137-plus.json` closed
- near-production ops maturity closed
- six-agent handoff UX closed
- guided demo-intake phase closed
- pilot UX hardening and live-intake trust pass closed

Current wrapped baseline:

- five-family support-to-engineering wedge
- bounded REPLICA runtime replay
- bounded TRACE debugging and engineering handoff
- pilot-safe observability, governance, exports, resilience, and review packet automation
- visible six-agent handoff with packet flow and demo replay mode
- curated `/inputs` demo bundles for the five-family wedge
- fresh-incident demo-origin guidance for stakeholder walkthroughs
- queue-first access choices for seeded and fresh incident review
- progressive disclosure on the incident workspace
- top-brief-first landing for fresh `nxs_...` incidents created from `/inputs`
- browser-truth coverage across queue, inputs, incident, training, and settings

Most recently implemented:

- seeded and fresh incident access improvements on `/queue`
- progressive-disclosure refactor on the incident workspace
- six-agent relay legibility improvements with clearer baton ownership and packet flow
- fresh-incident evidence provenance and live-intake truth surfaces
- refined `/inputs -> fresh incident` transition with top-brief-first landing
- operator-facing walkthrough and doc index sync
- browser-truth and smoke coverage across the core demo surfaces

Next execution target:

- `backlog-145-plus.json`
- focus: documentation truth, route guidance consistency, and control-surface sync
- current pending items: `148` then `149`
- the next session can resume from the first pending item

Truth boundaries maintained:

- `REPLICA` remains bounded to curated reproduction packs (not arbitrary VM reproduction)
- `TRACE` remains bounded to curated debugging (not universal code debugger)
- all handoff packet surfaces include explicit scope messaging about bounded capability
