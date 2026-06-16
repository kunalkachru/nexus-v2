# NEXUS Working State

Short handoff for Codex or Claude sessions. Keep current and compact.

## Product State

NEXUS is an AI-assisted support-to-engineering investigation product: noisy logs go in, a triaged investigation packet comes out, and one governed human review gate remains.

## Baseline

- Branch: `master`
- Current bounded wedge: five supported outage families
- `pytest tests/ -q` → target baseline: **168 passed**
- `npm run browser:verify` → target baseline: **13 passed**
- `python demo.py` → demo incidents complete
- `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` → should pass
- `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` → should pass

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

- Active backlog: `backlog-125-plus.json`
- Active phase: six-agent handoff UX hardening
- Status: 5/6 items complete (items 125-129 done, item 130 in final validation)

Completed phases:

- `backlog-117-plus.json` closed
- near-production ops maturity closed
- six-agent handoff UX: contract, relay, packets, animations, replay controls added

Current wrapped baseline:

- five-family support-to-engineering wedge
- bounded REPLICA runtime replay
- bounded TRACE debugging and engineering handoff
- pilot-safe observability, governance, exports, resilience, and review packet automation
- visible six-agent handoff with packet flow and demo replay mode

Implemented in this phase:

- visible relay: `SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN` with animated baton transfer
- `handoff_flow` contract across seeded and live incident paths
- current-owner state with previous/next owner visibility
- emitted/received packet cards from handoff events
- chronological handoff ledger with event tracking
- pulse animations for active relay nodes and ledger highlighting
- demo-mode replay controls (start, next, reset) for operator walkthroughs

Truth boundaries maintained:

- `REPLICA` remains bounded to curated reproduction packs (not arbitrary VM reproduction)
- `TRACE` remains bounded to curated debugging (not universal code debugger)
- all handoff packet surfaces include explicit scope messaging about bounded capability
