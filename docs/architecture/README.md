# NEXUS Architecture Documentation

Complete visual documentation of the NEXUS 7-family incident investigation platform.

## Overview

This directory contains Mermaid diagrams showing:
- System architecture and component boundaries
- The 6-agent pipeline and handoff flows
- Data flow from incident intake through Guardian decision
- Class relationships and data models
- Deployment topology on Oracle Cloud
- Key user journey sequences

## Diagrams

1. **[System Overview](01-system-overview.md)** — High-level architecture
   - External inputs (webhooks, UI, adapters)
   - NEXUS application boundary
   - 6-agent pipeline
   - Storage and outputs
   - Oracle Cloud deployment context

2. **[Agent Pipeline](02-agent-pipeline.md)** — 6-agent handoff flow
   - Agent-by-agent data transformation
   - Evidence posture decision logic
   - Input/output contracts for each agent
   - Capability boundaries (what's real vs. bounded)

3. **[Data Flow](03-data-flow.md)** — End-to-end incident lifecycle
   - Fresh raw-text submission flow
   - Webhook ingestion flow
   - Guardian approval and handoff packet creation
   - Sequence diagrams with real function calls

4. **[Class Structure](04-class-structure.md)** — Key data models
   - `IncidentRecord` — Primary incident data
   - `IncidentLifecycleResponse` — API contract
   - `SentinelClassification`, `GuardianDecision`, etc.
   - Relationships and inheritance

5. **[Deployment Architecture](05-deployment.md)** — Oracle Cloud setup
   - VM specs and network layer
   - Docker containerization
   - nginx reverse proxy with SSL
   - GitHub Actions CI/CD pipeline
   - Named volumes and persistence

6. **[Sequence Diagrams](06-sequence-diagrams.md)** — User journeys
   - New pilot customer first incident
   - Webhook-triggered incident (Datadog)
   - Guardian rejection flow
   - Out-of-scope incident handling

## 7-Family Pipeline

**Supported families with full investigation payloads:**

| ID | Family | Severity | Evidence | Payloads |
|---|---|---|---|---|
| INC001 | API Timeout / Retry Amplification | P2 | 🟢 Runtime-backed | Docker replay pack |
| INC002 | Database Connection Pool Exhaustion | P1 | 🟢 Runtime-backed | Docker replay pack |
| INC003 | Deploy Regression / 5xx Spike | P1 | 🟢 Runtime-backed | Docker replay pack |
| INC004 | Cache Cardinality Explosion | P2 | 🟡 Inference-first | Diagnosis pattern only |
| INC005 | Queue Backlog Surge | P1 | 🟢 Runtime-backed | Diagnosis pattern only |
| INC006 | Expired TLS Certificate | P0 | 🟡 Inference-first | Diagnosis pattern only |
| INC007 | Auth Dependency Slowdown | P1 | 🟢 Runtime-backed | Diagnosis pattern only |

**Catalogued but not yet wired (Phase 4):**
- INC008 — Primary Region Message Queue Outage
- INC009 — CDN / Cache Invalidation Failure
- INC010 — ML Model Degradation
- INC011 — Geographic / Routing Failure

## Key Concepts

**Pipeline:** SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN

- **SENTINEL** — Deterministic keyword-based incident family classification
- **PRISM** — LLM-based root cause hypothesis from classification context
- **REPLICA** — Bounded runtime reproducer (only 3 Docker packs: INC001, INC002, INC003)
- **TRACE** — Bounded debugging and code inspection (limited to classified families)
- **FORGE** — Mitigation ranker using runtime outcomes + inference + memory
- **GUARDIAN** — Human approval gate with governance and audit trails

**Evidence Postures:**
- 🟢 **Runtime-backed** — REPLICA can reproduce; FORGE uses actual runtime outcomes
- 🟡 **Inference-first** — PRISM diagnosis only; FORGE ranks using inference + memory
- 🔴 **Unsupported** — Not in supported families (will be rejected explicitly)

## Navigation

- **New to NEXUS?** Start with [System Overview](01-system-overview.md)
- **Understanding the agents?** See [Agent Pipeline](02-agent-pipeline.md)
- **Tracing an incident?** Follow [Data Flow](03-data-flow.md)
- **Integrating with NEXUS?** Check [Class Structure](04-class-structure.md) for API contracts
- **Deploying or scaling?** See [Deployment Architecture](05-deployment.md)
- **Building workflows?** Review [Sequence Diagrams](06-sequence-diagrams.md)

---

Generated from source code analysis. All diagrams reflect the current 7-family implementation as of 2026-06-24.
