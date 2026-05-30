# Operations

This is the runtime companion to the README.
It describes how to start the product, verify the main surfaces, and recover from the most common failures in demo or product mode.

## Modes

- `demo`: Hugging Face Spaces or single-container evaluation mode.
- `product`: tenant-aware deployment with persisted incident state and signed ingress.

## Required Secrets

- `OPENAI_API_KEY` if you enable the optional OpenAI demo path
- platform auth header or gateway credentials
- database or object-store credentials if you are running outside demo mode

Optional demo path settings:
- `NEXUS_USE_OPENAI=1`
- `LLM_MODEL`

For local development, copy [.env.example](../.env.example) to `.env` and keep your tokens there. The app reads `NEXUS_*` environment variables directly.

When the optional OpenAI path is enabled, the seeded incident console and `/run-incident` route will show live LLM-backed SENTINEL, PRISM, and FORGE reasoning while GUARDIAN stays deterministic.
The raw-log intake path uses the same live reasoning mode when OpenAI is enabled, so you can demo the real incident input flow from pasted logs through the agent chain.

## Start Up

- Local product smoke test: `docker compose up --build`
- Direct runtime entrypoint: `uvicorn server.app:app --host 0.0.0.0 --port 7860`
- Kubernetes deployment: apply `ops/kubernetes/configmap.yaml` and then `ops/kubernetes/deployment.yaml`

## Verify

- `GET /health`
- `GET /dashboard`
- `GET /inputs` and submit a raw-log paste incident
- `GET /queue`
- `GET /incident?nexus_incident_id=INC001`
- Authenticated `GET /api/v1/incidents/queue` with tenant headers
- Review audit logs after webhook ingestion and incident reads

For the full browser walkthrough and demo script, see [docs/DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md).
For the browser verification checklist, see [docs/BROWSER_VERIFICATION_CHECKLIST.md](BROWSER_VERIFICATION_CHECKLIST.md).
For the quick pass/fail checklist, see [docs/VERIFICATION_PASS_FAIL_CHECKLIST.md](VERIFICATION_PASS_FAIL_CHECKLIST.md).
For the quick live demo reference, see [docs/DEMO_CHEAT_SHEET.md](DEMO_CHEAT_SHEET.md).
For live presentation notes by screen, see [docs/LIVE_DEMO_SPEAKER_NOTES.md](LIVE_DEMO_SPEAKER_NOTES.md).
For the full presenter pack, see [docs/PRESENTATION_PACK.md](PRESENTATION_PACK.md).
For the agent model matrix, see [docs/AGENT_MODEL_MATRIX.md](AGENT_MODEL_MATRIX.md).

## Recover

- If incident persistence is corrupted, restore the backing store and replay recent webhooks.
- If auth or rate limiting is misconfigured, fail closed on incident reads and rerun the security suite.
- If webhook signature verification fails unexpectedly, check the ingress secret and request signing path first.
