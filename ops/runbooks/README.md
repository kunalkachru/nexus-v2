# NEXUS Operations Runbooks

- Incident replay: replay webhook payloads against `/webhooks/incident` in a staging namespace before production rollout.
- Rollback: revert the last deployment, validate `/health`, then confirm `/incidents/{id}` still returns tenant-scoped data.
- Secrets rotation: rotate `OPENAI_API_KEY` and platform auth secrets together, then restart the deployment.
- Persistence recovery: restore `artifacts/` or the configured product database volume before re-enabling writes.

Active operator and pilot docs:

- [docs/OPERATIONS.md](/Users/kunalkachru/Documents/nexus-v3/docs/OPERATIONS.md)
- [docs/OPERATOR_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/OPERATOR_RUNBOOK.md)
- [docs/PILOT_OPERATIONS_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/PILOT_OPERATIONS_RUNBOOK.md)
