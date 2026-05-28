# NEXUS Operations Runbooks

- Incident replay: replay webhook payloads against `/webhooks/incident` in a staging namespace before production rollout.
- Rollback: revert the last deployment, validate `/health`, then confirm `/incidents/{id}` still returns tenant-scoped data.
- Secrets rotation: rotate `OPENAI_API_KEY` and platform auth secrets together, then restart the deployment.
- Persistence recovery: restore `artifacts/` or the configured product database volume before re-enabling writes.
