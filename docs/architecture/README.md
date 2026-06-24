# NEXUS Architecture Documentation

Visual documentation of NEXUS system architecture, data flows, agent interactions, and deployment topology. All diagrams use Mermaid syntax and render natively on GitHub.

## Diagrams

| # | Document | What it shows |
|---|---|---|
| 1 | [System Overview](01-system-overview.md) | External inputs (webhooks, UI), NEXUS boundary, 6-agent pipeline, storage layers (SQLite, packs, artifacts), Oracle Cloud context |
| 2 | [Agent Pipeline](02-agent-pipeline.md) | Agent-by-agent handoff chain, SENTINEL→PRISM→REPLICA→TRACE→FORGE→GUARDIAN, evidence posture decision tree, input/output contracts |
| 3 | [Data Flow](03-data-flow.md) | Fresh incident submission flow, webhook ingestion, Guardian approval/rejection loops, out-of-scope handling, database schema |
| 4 | [Class Structure](04-class-structure.md) | Key models: IncidentRecord, IncidentLifecycleResponse, SentinelClassification, GuardianDecision; API request/response contracts |
| 5 | [Deployment](05-deployment.md) | Oracle Cloud E2.1.Micro VM (1GB RAM, Frankfurt), nginx reverse proxy with SSL, Docker containerization, GitHub Actions CI/CD (test→build→deploy→smoke) |
| 6 | [Sequence Diagrams](06-sequence-diagrams.md) | Pilot customer first incident, webhook-triggered incident, Guardian rejection & retry loop, out-of-scope incident handling, runtime-backed evidence flow |

## Quick Navigation

**New to NEXUS?** Start with [System Overview](01-system-overview.md) — high-level view of the entire system.

**Understanding the agents?** See [Agent Pipeline](02-agent-pipeline.md) — how each agent processes data and hands off to the next.

**Tracing an incident?** Follow [Data Flow](03-data-flow.md) — sequence diagrams showing incident lifecycle from submission to Guardian approval.

**Integrating with NEXUS?** Check [Class Structure](04-class-structure.md) — API data models and request/response contracts.

**Deploying to Oracle Cloud?** See [Deployment](05-deployment.md) — VM specs, Docker setup, SSL/TLS, CI/CD pipeline.

**Seeing user workflows?** Review [Sequence Diagrams](06-sequence-diagrams.md) — step-by-step interactions for common scenarios.

## 7-Family Supported Incident Pipeline

| ID | Family | Severity | Evidence Posture | Deployment |
|---|---|---|---|---|
| INC001 | API Timeout / Retry Amplification | P2 | 🟢 Runtime-backed | Docker replay pack |
| INC002 | Database Connection Pool Exhaustion | P1 | 🟢 Runtime-backed | Docker replay pack |
| INC003 | Deploy Regression / 5xx Spike | P1 | 🟢 Runtime-backed | Docker replay pack |
| INC004 | Cache Cardinality Explosion | P2 | 🟡 Inference-first | Pattern only |
| INC005 | Queue Backlog Surge | P1 | 🟢 Runtime-backed | Pattern only |
| INC006 | Expired TLS Certificate | P0 | 🟡 Inference-first | Pattern only |
| INC007 | Auth Dependency Slowdown | P1 | 🟢 Runtime-backed | Pattern only |

**Catalogued but not yet wired (Phase 4 roadmap):** INC008, INC009, INC010, INC011

## Back to Documentation

- Back to [docs/README.md](../README.md) — full documentation index
- Back to [README.md](../../README.md) — repository root

---

Generated from source code analysis. Current implementation: 7-family pipeline with 3 Docker replay packs, 6-agent handoff, Guardian approval gate. Updated: 2026-06-24.
