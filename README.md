# NEXUS

NEXUS is an AI-assisted support-to-engineering investigation product for recurring customer-facing application outages.

The product is intentionally narrow:

- noisy logs and support evidence go in
- a structured investigation packet comes out
- one governed human review point remains before action

Today the shipped product is a bounded six-stage workflow:

`SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

It is not a universal incident platform, universal debugger, or arbitrary environment reproduction system.

## What Problem It Solves

Support and triage teams still waste too much time:

- collecting logs from multiple places
- checking prior incidents manually
- guessing likely owners
- escalating incomplete cases to engineering
- repeating the same investigation work on recurring outages

NEXUS reduces that relay work by preparing a review-ready case before engineering has to start from raw evidence.

## Current Product Boundary

The current bounded wedge is recurring customer-facing application incidents with clear business impact and repeatable failure patterns.

Shipped incident families at the current baseline:

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike

What is real today:

- structured intake for fresh incidents
- memory-backed triage and investigation
- bounded REPLICA runtime replay for the curated outage packs
- bounded TRACE developer handoff and debugger-style guidance
- runtime-weighted remediation selection
- explicit Guardian approval
- engineering handoff export, delivery, and pilot reporting surfaces

What is still bounded:

- reproduction only works for curated packs
- debugging is packet-based, not a universal live debugger
- execution remains governed and human-approved

## Start Here

- [Current documentation map](/Users/kunalkachru/Documents/nexus-v3/docs/README.md)
- [Product strategy and GTM](/Users/kunalkachru/Documents/nexus-v3/docs/PRODUCT_STRATEGY_AND_GTM.md)
- [Full manual walkthrough](/Users/kunalkachru/Documents/nexus-v3/docs/DEMO_WALKTHROUGH.md)
- [Operations guide](/Users/kunalkachru/Documents/nexus-v3/docs/OPERATIONS.md)
- [Pilot operations runbook](/Users/kunalkachru/Documents/nexus-v3/docs/PILOT_OPERATIONS_RUNBOOK.md)
- [Buyer proof package](/Users/kunalkachru/Documents/nexus-v3/docs/BUYER_PROOF_PACKAGE.md)
- [Working state / current validated baseline](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md)

## Local Run

Preferred local path:

```bash
./scripts/docker_fresh.sh
```

If you want packaged-app replay delegated through the runtime host:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

Direct server path:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Live Reasoning And Keys

NEXUS stays deterministic by default.

- local or hosted users can optionally provide `OPENAI_API_KEY`-backed live reasoning through the request-scoped BYO-key flow
- if no key is attached, the product remains fully usable in deterministic mode
- the public contract does not require a server-side key to keep the product operable

## Validation

Use the current validated baseline recorded in [WORKING_STATE.md](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md).

Core validation commands:

```bash
pytest tests/ -q
npm run browser:verify
python demo.py
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

## Repository Shape

- `server/` FastAPI backend, incident pipeline, runtime packs, and APIs
- `frontend/` operator UI
- `runtime_host/` Docker-capable replay host for packaged demos
- `docs/` active product, demo, ops, and roadmap docs
- `archive/` historical plans, submission-era assets, and superseded materials

## Current Planning Frontier

The current active expansion frontier is tracked in:

- [docs/POST_108_SELECTIVE_EXPANSION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_108_SELECTIVE_EXPANSION_PLAN.md)
- [docs/POST_108_EXECUTION_MAP.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_108_EXECUTION_MAP.md)
- [backlog-109-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-109-plus.json)
