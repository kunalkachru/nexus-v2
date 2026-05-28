# NEXUS v2 Design Document

**Version:** 2.0  
**Date:** May 28, 2026  
**Status:** Working design for Phase 2 production integration

## Purpose

This document turns the product and sprint materials in `design-docs/` into an implementation-facing design for NEXUS v2. Phase 1 established the local deterministic agent loop. Phase 2 extends that loop to production-style observability systems, real incident timelines, reusable runbooks, and policy-enforced execution gates.

## Current Architecture

NEXUS v2 coordinates four agents across a shared incident envelope:

- `SENTINEL` classifies the incident type and priority from alerts, metrics, and service topology.
- `PRISM` correlates logs, metrics, and deployment context to identify the most likely root cause.
- `FORGE` maps the diagnosis to runbook candidates and generates the safest remediation sequence.
- `GUARDIAN` validates the proposed actions against safety policy before execution.

The orchestration contract remains linear for Phase 2:

1. Ingest alerts and observability context.
2. Classify the incident.
3. Correlate supporting evidence.
4. Select or generate a runbook.
5. Approve, deny, or request modification.
6. Emit an auditable response envelope for UI, operators, and downstream execution systems.

## Phase 2: Real Incident Integration

### Objective

Replace demo-only incident summaries with production-shaped context from actual monitoring, logging, and operational systems. Phase 2 does not require NEXUS to execute directly in production, but it does require NEXUS to consume real alerts, reason over real evidence, and produce runbook recommendations and safety decisions that can be reviewed by operators.

### SENTINEL: Real Alert Parsing From Prometheus and Datadog

SENTINEL ingests alerts from Prometheus Alertmanager webhooks and Datadog monitor events. The ingestion layer normalizes both formats into a shared alert envelope:

- `source`: `prometheus` or `datadog`
- `monitor_name` / `alertname`
- `severity`
- `triggered_at`
- `service`, `team`, `environment`
- `metric values`, thresholds, and tags
- `related dashboards`, trace links, and incident URLs

Parsing rules:

- Prometheus alerts map labels and annotations into typed fields, preserving series labels for service, namespace, cluster, and dependency.
- Datadog alerts map monitor metadata, grouped tags, and current values into the same envelope, including query text and monitor state.
- Duplicate alerts are merged by fingerprint so SENTINEL reasons over one incident cluster rather than a page storm.

Classification features used by SENTINEL in Phase 2:

- Current metric values and threshold deltas
- Service and dependency tags
- Alert co-occurrence windows across the last 10 minutes
- Deployment recency
- Similar historical incident fingerprints

Expected output:

- Incident type
- Normalized severity
- Confidence score
- Confidence breakdown by metrics, logs, and topology
- Evidence list explaining why the alert cluster matches a known incident pattern

### PRISM: Log Correlation Through ELK Stack

PRISM uses Elasticsearch-backed log retrieval to gather incident evidence from the last 10 minutes around the initial alert trigger. Queries are anchored by service, namespace, environment, trace IDs, error signatures, and deployment version.

Correlation flow:

1. Pull candidate logs from ELK for affected services and dependencies.
2. Rank log lines by overlap with alert dimensions, error signatures, and historical root-cause tokens.
3. Join matching logs with metrics anomalies and recent deployment events.
4. Produce a root-cause hypothesis with supporting snippets and a correlation narrative.

ELK usage details:

- Elasticsearch provides indexed log search across applications, workers, gateways, and platform services.
- Logstash or equivalent pipelines enrich logs with service, pod, cluster, trace, and release metadata.
- Kibana links are attached to the incident envelope so operators can pivot into raw search results.

Phase 2 PRISM outputs:

- Root cause
- Supporting log snippets
- Correlation analysis narrative
- Queried sources, including `logs`, `metrics`, `deployments`, and `history`
- Confidence score based on evidence density and cross-source agreement

### FORGE: Matching Against Real Runbook Templates

FORGE no longer treats every incident as a blank-slate generation task. It first searches a real runbook catalogue, then decides whether to adapt an existing template or generate a new candidate procedure.

Runbook sources:

- Versioned runbook templates in Git
- Historical incident timelines and outcomes
- Service ownership metadata
- Change-management constraints

Matching strategy:

- Match by incident fingerprint, affected service, root cause, deployment context, and historical success rate
- Prefer runbooks with reversible actions and lower blast radius
- Down-rank runbooks that require broad data mutation, full-cluster operations, or unsafe cleanup patterns
- Generate only when no sufficiently similar runbook reaches the configured similarity threshold

FORGE Phase 2 output:

- Recommended runbook name
- Candidate fixes with historical success rates
- Selection logic explaining why one template outranked the rest
- Estimated execution cost and expected recovery time

### GUARDIAN: Safety Policy Enforcement

GUARDIAN becomes the production gate between generated remediation and any execution system. It enforces both static safety patterns and environment-specific operational policy.

Safety policy categories:

- No destructive storage commands without explicit human approval
- No credential exposure or inline secret handling
- No broad-scope cache flush, topic reset, or database schema mutation during autonomous mode
- Rollbacks must target signed artifacts or approved deployment versions
- Queue and stream operations must preserve offsets, message durability, and replay integrity

Checks performed in Phase 2:

- Command linting against blocklists and regex rules
- Service scope validation against the incident envelope
- Verification that proposed actions are reversible or bounded
- Policy lookup by severity, environment, and maintenance window
- Human-approval escalation when policy confidence falls below threshold

GUARDIAN output:

- `approve`, `reject`, or `request_modification`
- Safety score
- Safety checks performed
- Policy violations, if any
- Reasoning that operators can audit later

### Production Dependencies

Phase 2 requires integration with the following production systems:

- Prometheus + Alertmanager
- Datadog monitors and events API
- Elasticsearch / Logstash / Kibana
- PagerDuty for alert and incident lifecycle handoff
- Git-hosted runbook repository
- Deployment metadata from CI/CD or Kubernetes rollout history
- Service catalog / ownership metadata
- Optional trace links from OpenTelemetry-compatible systems

Recommended supporting components:

- A normalization service for alert and log envelopes
- Redis or SQLite-backed cache for recent incident context during the demo environment
- Secrets management for API tokens
- Audit log storage for agent decisions

### Success Metrics For Phase 2

Primary metrics:

- `>= 90%` of incoming Prometheus and Datadog alerts normalize into the shared incident envelope without manual cleanup
- `>= 85%` of demo incidents include correlated logs from ELK within 5 seconds of alert ingest
- `>= 80%` of FORGE recommendations map to an existing runbook template before freeform generation
- `100%` of dangerous or policy-violating runbooks are rejected by GUARDIAN in test scenarios
- Demo dashboard renders metrics, logs, timelines, history, and agent reasoning for all five core incidents

Operator outcomes:

- Mean triage time under 2 minutes from alert ingest to recommended runbook
- At least 30% reduction in manual evidence gathering during on-call reviews
- Human approval accepted on first pass for at least 70% of low-blast-radius runbooks

### Phase 2 Deliverables

- Shared incident envelope carrying realistic observability context
- Updated backend demo and API responses for five production-shaped incidents
- Dashboard support for metrics, logs, timeline, history, runbook reasoning, and safety review
- Roadmap for live integrations into alerting, logging, and runbook systems
