# NEXUS v2 Phase 2 Roadmap

> Current implementation alignment is tracked in [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](NEXUS_v2_DOC_STATUS_MATRIX.md).

## Timeline: Weeks 1-4

### Week 1: Ingestion And Data Normalization

- Integrate Prometheus Alertmanager webhook ingestion.
- Integrate Datadog monitor/event ingestion.
- Define the shared incident envelope used by SENTINEL, PRISM, FORGE, and GUARDIAN.
- Add deployment metadata capture from CI/CD or Kubernetes rollout history.
- Validate five representative incidents end-to-end with recorded payloads.

### Week 2: Correlation And Evidence Retrieval

- Connect PRISM to ELK for the last 10 minutes of logs around each alert.
- Join logs to alert tags, service ownership, release versions, and dependency maps.
- Add timeline construction from alerts, deployments, and key log events.
- Measure retrieval latency and evidence completeness for demo scenarios.

### Week 3: Runbook Matching And Safety Policy

- Index real runbook templates from the operational runbook repository.
- Rank candidate runbooks by incident fingerprint, affected service, and historical success rate.
- Enforce GUARDIAN safety rules for destructive commands, credentials, scope, and rollback provenance.
- Add operator-facing reasoning fields for runbook selection and approval decisions.

### Week 4: UX, Validation, And Operational Readiness

- Finalize the dashboard panels for metrics, logs, timeline, history, and runbook references.
- Run incident playback tests for all five core incidents plus negative safety cases.
- Validate PagerDuty handoff and audit logging.
- Document rollout, ownership, support, and on-call review procedures.

## Data Sources Needed

- Prometheus Alertmanager webhooks
- Datadog monitors, tags, and event payloads
- Elasticsearch log indices with service and release enrichment
- PagerDuty incident metadata
- Deployment history from CI/CD, Kubernetes, or release tooling
- Git-backed runbook templates and historical incident records
- Service catalog and ownership metadata
- Optional trace links from OpenTelemetry-compatible systems

## Agent Integration Points

### SENTINEL

- Alert normalization service
- Metrics threshold and tag extraction
- Historical incident fingerprint lookup

### PRISM

- ELK query layer
- Deployment correlation feed
- Metric and log evidence ranking

### FORGE

- Runbook template index
- Historical success-rate store
- Execution-cost and blast-radius heuristics

### GUARDIAN

- Policy registry
- Command scanning and scope validation
- Approval routing for low-confidence or high-risk actions

## Success Metrics

- 90%+ of alert payloads normalize successfully into the shared incident envelope
- 85%+ of incidents return usable log correlation within 5 seconds
- 80%+ of incidents match an existing runbook template before freeform generation
- 100% rejection rate for policy-violating runbooks in test scenarios
- 70%+ first-pass operator approval for low-blast-radius runbooks
- Dashboard renders full incident details and agent reasoning for all five demo incidents

## Team And Resources Needed

- 1 platform engineer for alert and deployment integrations
- 1 backend engineer for agent payloads, correlation, and runbook matching
- 1 frontend engineer or product engineer for dashboard and operator UX
- 1 SRE partner for runbook validation and safety policy definition
- Access to Prometheus, Datadog, ELK, PagerDuty, CI/CD metadata, and runbook repositories
- Test environment with representative incidents and replayable observability data
