# Operations

Current as of 2026-06-05.

This document is the runtime guide for the shipped NEXUS v2 product and the current support-triage demo flow.

It focuses on what is runnable now while staying aligned with the broader product direction.

## Runtime Posture

Today’s shipped product is:

- deterministic by default
- safe for public demo
- able to use request-scoped BYO-key live reasoning when a user explicitly opts in
- built around the visible four-agent flow:
  - `SENTINEL`
  - `PRISM`
  - `FORGE`
  - `GUARDIAN`

The broader product direction adds:

- `REPLICA` for reproduction
- `TRACE` for debugging

Those are not required for current runtime operation.

## Deployment Modes

### 1. Public demo mode

Used for:

- Hugging Face Spaces
- public product review
- live walkthroughs

Characteristics:

- deterministic by default
- no server OpenAI key required
- safe for public access
- optional user-supplied OpenAI key from the UI

### 2. Local development mode

Used for:

- feature work
- browser validation
- regression checks
- end-to-end flagship use case review

Characteristics:

- Docker-first workflow
- same frontend and backend served together
- easy rebuild path

## Recommended Start Commands

### Fresh local rebuild

```bash
./scripts/docker_fresh.sh
```

### Direct server run

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Public Spaces

### Production

- Space page: [https://huggingface.co/spaces/kunalkachru23/nexus](https://huggingface.co/spaces/kunalkachru23/nexus)
- Public app: [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)

### Staging

- Space page: [https://huggingface.co/spaces/kunalkachru23/nexus-staging](https://huggingface.co/spaces/kunalkachru23/nexus-staging)
- Public app: [https://kunalkachru23-nexus-staging.hf.space](https://kunalkachru23-nexus-staging.hf.space)

## Key Runtime Rules

- default public posture is deterministic
- `OPENAI_API_KEY` is not required for the public app
- a user can optionally attach their own key in `Incident Detail`
- user keys are request-scoped and masked in the UI
- history and archive review should stay deterministic by default

## Health Check

Use:

- `/health`

Expected:

```json
{"status":"ok"}
```

## Primary Manual Checks

Use the flagship support-triage story while validating:

1. `/inputs` can create a fresh `nxs_...` incident from raw logs
2. the created incident reads like a prepared support case
3. `GUARDIAN` approval visibly changes the execution state
4. `/training` maps the latest live triage into the broader runtime summary
5. `/history` opens archived incidents quickly in deterministic review mode

## Local Verification Commands

### Python tests

```bash
pytest tests/ -v
```

### Browser tests

```bash
npm run browser:verify
```

### Judge demo script

```bash
python demo.py
```

## If The UI Looks Stale Locally

1. run `./scripts/docker_fresh.sh`
2. wait for `Fresh container is ready.`
3. reload the browser tab

## If The Public HF Space Feels Slow

The product should behave like a review and triage surface, not a hidden re-analysis path.

If a warm page is repeatedly taking several seconds:

1. reload once
2. retry the route
3. compare with local Docker
4. check whether the route is hitting a Space-side cold/warm latency issue
5. confirm the flow is not accidentally re-triggering expensive live reasoning on review screens

## Source Of Truth Docs

- [README.md](/Users/kunalkachru/Documents/nexus-v3/README.md)
- [PRODUCT_STRATEGY_AND_GTM.md](/Users/kunalkachru/Documents/nexus-v3/docs/PRODUCT_STRATEGY_AND_GTM.md)
- [SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md)
- [FINAL_SUBMISSION_GUIDE.md](/Users/kunalkachru/Documents/nexus-v3/docs/FINAL_SUBMISSION_GUIDE.md)
