# Operations

Current as of 2026-05-31.

This document is the runtime guide for the shipped NEXUS v2 product.
It focuses on what is actually runnable now.

## Deployment Modes

### 1. Public demo mode

Used for:

- Hugging Face Spaces
- public judging/demo link

Characteristics:

- deterministic by default
- no server OpenAI key required
- safe for public access
- optional user-supplied OpenAI key from the UI

### 2. Local development mode

Used for:

- development
- browser validation
- regression checks

Characteristics:

- Docker-first workflow
- same frontend and backend served together
- easy rebuild path

## Recommended Start Commands

### Fresh local rebuild

```bash
./scripts/docker_fresh.sh
```

This is the preferred local reset path.

### Direct server run

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Public Space

- Space page: [https://huggingface.co/spaces/kunalkachru23/nexus](https://huggingface.co/spaces/kunalkachru23/nexus)
- Public app: [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)

## Key Runtime Rules

- default public posture is deterministic
- `OPENAI_API_KEY` is not required for the public app
- a user can optionally attach their own key in `Incident Detail`
- user keys are request-scoped and masked in the UI

## Health Check

Use:

- `/health`

Expected:

```json
{"status":"ok"}
```

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

## Main Manual Checks

1. `/queue` loads
2. a queue incident opens a populated incident page
3. `/inputs` can create a fresh `nxs_...` incident
4. `Approve runbook` updates Guardian and execution state
5. `/training` shows reward improvement and learning summary

## If The UI Looks Stale Locally

1. run `./scripts/docker_fresh.sh`
2. wait for `Fresh container is ready.`
3. reload the browser tab

## If The Public HF Space Feels Slow

Some extra latency is expected versus local Docker.
Roughly sub-second to low-single-second page transitions are acceptable on Hugging Face Spaces.

If a warm page is repeatedly taking several seconds:

1. reload once
2. retry the route
3. compare with local Docker
4. check whether it is a Space-side cold/warm latency issue

## Related Docs

- [docs/FINAL_SUBMISSION_GUIDE.md](FINAL_SUBMISSION_GUIDE.md)
- [docs/DEMO_CHEAT_SHEET.md](DEMO_CHEAT_SHEET.md)
- [docs/BROWSER_VERIFICATION_CHECKLIST.md](BROWSER_VERIFICATION_CHECKLIST.md)
- [docs/VERIFICATION_PASS_FAIL_CHECKLIST.md](VERIFICATION_PASS_FAIL_CHECKLIST.md)
