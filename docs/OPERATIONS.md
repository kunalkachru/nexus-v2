# Operations

## Modes

- `demo`: Hugging Face Spaces or single-container evaluation mode.
- `product`: multi-service deployment with persisted incident state and tenant-aware APIs.

## Required Secrets

- `OPENAI_API_KEY`
- platform auth header or gateway credentials
- any production database or object-store credentials used outside demo mode

## Deployment

- Local product smoke test: `docker compose up --build`
- Kubernetes deployment: apply `ops/kubernetes/configmap.yaml` then `ops/kubernetes/deployment.yaml`
- Runtime entrypoint remains `uvicorn server.app:app --host 0.0.0.0 --port 7860`

## Runbook

- Verify `/health`
- Verify `/dashboard`
- Verify authenticated `GET /incidents/{id}` with tenant headers
- Review audit logs after webhook ingestion and incident reads

## Recovery

- If incident persistence is corrupted, restore the backing store and replay recent webhooks.
- If auth or rate limiting is misconfigured, fail closed on `GET /incidents/{id}` and re-run the security suite.
