# NEXUS

NEXUS is an AI-assisted support-to-engineering investigation product for recurring customer-facing application outages.

It is built to reduce the manual relay between support and engineering:

- noisy logs and incident evidence go in
- a structured investigation packet comes out
- one governed human review point remains before action

The shipped workflow is:

`SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

NEXUS is not a universal incident platform, universal debugger, or arbitrary environment reproduction system.

## What Problem It Solves

Support and triage teams still lose time on:

- collecting logs from multiple systems
- guessing likely owners
- searching old incidents manually
- escalating weak cases to engineering
- repeating the same investigation work on recurring outages

NEXUS compresses that relay into one support-to-engineering investigation workflow.

## Current Product Boundary

The current bounded wedge is recurring customer-facing application incidents with strong business impact and repeatable failure patterns.

Supported bounded outage families:

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike
4. `INC005` queue / worker backlog affecting transaction completion
5. `INC007` auth dependency slowdown / token validation failures

Real today:

- fresh incident intake and normalization posture
- memory-backed triage and investigation
- bounded REPLICA runtime replay for curated packs
- bounded TRACE developer handoff and debugger guidance
- runtime-aware mitigation ranking
- explicit Guardian approval
- engineering handoff export and pilot proof surfaces

Still bounded:

- reproduction only works for curated packs
- debugging is packet-based, not a universal live debugger
- execution remains governed and human-approved

## Start Here

- [Documentation index](/Users/kunalkachru/Documents/nexus-v3/docs/README.md)
- [Public docs](/Users/kunalkachru/Documents/nexus-v3/docs/public/README.md)
- [Internal docs](/Users/kunalkachru/Documents/nexus-v3/docs/internal/README.md)
- [Current working state](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md)

## Local Run

Set `OPENAI_API_KEY` when you want live model-backed reasoning instead of fallback-only behavior.

Preferred packaged path:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

Direct server path:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Validation

Core validation commands:

```bash
pytest tests/ -q
npm run browser:verify
python demo.py
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

Current validated baseline:

- `pytest tests/ -q` -> `168 passed`
- `npm run browser:verify` -> `11 passed`
- `python demo.py` -> passes
- Docker rebuild and enterprise smoke path -> passes

## Roadmap Status

The current five-family product objective is wrapped for the present strategy.

Any next work should stay narrow:

- pilot-specific hardening
- bugfixes
- explicitly scoped tenant follow-ups

## Repository Shape

- `server/` backend APIs, incident pipeline, and runtime pack orchestration
- `frontend/` operator UI
- `runtime_host/` Docker-capable replay host for packaged demos
- `docs/public/` market, buyer, demo, and presentation-facing material
- `docs/internal/` operator, pilot, verification, and control docs
