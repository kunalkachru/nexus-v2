# Operations

This is the runtime companion to the README.
It describes how to start the product, verify the main surfaces, and recover from the most common failures in demo or product mode.

## Modes

- `demo`: Hugging Face Spaces or single-container evaluation mode.
- `product`: tenant-aware deployment with persisted incident state and signed ingress.

## Required Secrets

- `OPENAI_API_KEY`
- platform auth header or gateway credentials
- database or object-store credentials if you are running outside demo mode

## Start Up

- Local product smoke test: `docker compose up --build`
- Direct runtime entrypoint: `uvicorn server.app:app --host 0.0.0.0 --port 7860`
- Kubernetes deployment: apply `ops/kubernetes/configmap.yaml` and then `ops/kubernetes/deployment.yaml`

## Verify

- `GET /health`
- `GET /dashboard`
- `GET /queue`
- `GET /incident?nexus_incident_id=INC001`
- Authenticated `GET /api/v1/incidents/queue` with tenant headers
- Review audit logs after webhook ingestion and incident reads

For the full browser walkthrough and demo script, see [docs/DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md).
For the quick live demo reference, see [docs/DEMO_CHEAT_SHEET.md](DEMO_CHEAT_SHEET.md).

## Recover

- If incident persistence is corrupted, restore the backing store and replay recent webhooks.
- If auth or rate limiting is misconfigured, fail closed on incident reads and rerun the security suite.
- If webhook signature verification fails unexpectedly, check the ingress secret and request signing path first.
