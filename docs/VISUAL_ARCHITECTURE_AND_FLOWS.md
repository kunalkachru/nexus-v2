# NEXUS v2 Visual Architecture And Flows

Current as of 2026-06-05.

This document explains what the product looks like, how the current shipped workflow works, and how the architecture expands into reproduction and debugging.

## Product Screenshots

### Command Center

![Command Center](/Users/kunalkachru/Documents/nexus-v3/docs/assets/screenshots/command-center.png)

### Incident Detail

![Incident Detail](/Users/kunalkachru/Documents/nexus-v3/docs/assets/screenshots/incident-detail.png)

### Raw Log To Incident Flow

![Raw Log Flow](/Users/kunalkachru/Documents/nexus-v3/docs/assets/screenshots/raw-log-incident-flow.png)

### Learning & Controls

![Learning and Controls](/Users/kunalkachru/Documents/nexus-v3/docs/assets/screenshots/learning-controls.png)

## What The Product Is Designed To Show

NEXUS is not a generic AI-for-incidents surface.

It is a support triage and incident investigation product designed to reduce manual relay work before one final human review point.

The product should answer these questions on screen:

1. what is most likely happening?
2. who likely owns the issue?
3. what prior cases matter?
4. what should happen next?
5. who approves it?

## Current Shipped Product Flow

```mermaid
flowchart LR
    A["Raw logs or queue incident"] --> B["Normalize incident context"]
    B --> C["SENTINEL triage"]
    C --> D["PRISM investigation"]
    D --> E["FORGE action preparation"]
    E --> F["GUARDIAN final review"]
    F --> G["Execution outcome"]
    G --> H["Learning and memory update"]
```

### Why this flow matters

- intake becomes one structured case
- investigation becomes visible
- action preparation becomes explicit
- governance becomes a product feature rather than a hidden rule

## Target Product Flow

```mermaid
flowchart LR
    A["Raw logs, alerts, tickets"] --> B["SENTINEL triage"]
    B --> C["PRISM investigation and memory"]
    C --> D["REPLICA reproduction"]
    D --> E["TRACE debugging"]
    E --> F["FORGE remediation packet"]
    F --> G["GUARDIAN approval"]
    G --> H["Execution or escalation"]
    H --> I["Learning and retrieval update"]
```

This is the full product direction:

- triage
- investigation
- reproduction
- debugging
- remediation
- governance

## Why The Architecture Is Shaped This Way

### Why FastAPI

- compact backend
- serves both HTML and JSON contracts
- easy single-container public deployment

### Why a multi-page frontend

- easier to reason about screen by screen
- easier to demo and validate route by route
- lower failure surface than a full SPA rewrite

### Why deterministic-by-default

- safe public demo
- reproducible judging flow
- live reasoning remains optional, not required

### Why visible agent roles

- the product needs to show work, not just answer
- support organizations care about traceability and trust

## System Architecture

```mermaid
flowchart TD
    A["Frontend experience layer"] --> B["FastAPI orchestration layer"]
    B --> C["Triage and investigation services"]
    B --> D["Training and learning surfaces"]
    C --> E["Incident persistence and audit"]
    C --> F["Deterministic reasoning path"]
    C --> G["Optional BYO-key live reasoning path"]
    C --> H["Incident memory and retrieval"]
    C --> I["Future reproduction sandboxes"]
    C --> J["Future debugging and source analysis"]
```

## Architecture Layers

### Frontend experience layer

The user-facing surfaces:

- `Command Center`
- `Inputs`
- `Incident Detail`
- `Training`
- `History`
- `Replay`

Their job is to present one coherent support-triage product, not backend fragments.

### Orchestration layer

This layer:

- receives normalized incident requests
- serves the queue and incident surfaces
- coordinates the visible agent flow
- handles Guardian review actions

### Persistence and audit layer

This layer stores:

- incident records
- audit history
- execution outcomes
- retrieval and learning artifacts

### Memory layer

This layer is already visible in the product through:

- similar incidents
- runbook memories
- unresolved follow-ups

It becomes even more important as the product moves toward support-triage specialization.

### Future reproduction layer

This is the `REPLICA` direction.

Its job is to:

- recreate likely failure conditions
- validate or reject hypotheses
- test likely mitigations in a controlled environment

### Future debugging layer

This is the `TRACE` direction.

Its job is to:

- narrow likely code paths
- identify state or control-flow anomalies
- prepare developer-ready debugging context

## End-To-End Data Flow

```mermaid
sequenceDiagram
    participant U as Support engineer or operator
    participant I as Inputs or Queue
    participant S as SENTINEL
    participant P as PRISM
    participant F as FORGE
    participant G as GUARDIAN
    participant L as Learning and memory

    U->>I: provide raw logs or open a case
    I->>S: normalized incident context
    S->>P: severity, ownership, issue family
    P->>F: investigation packet and memory
    F->>G: prepared action packet
    G-->>U: approve, reject, or request modification
    G-->>L: persist outcome for future retrieval
```

## Agent Design

### SENTINEL

- job: triage the incident and frame the case
- output: severity, likely service, likely team, issue family, confidence

### PRISM

- job: investigate likely cause and historical context
- output: root-cause hypothesis, evidence summary, deploy analysis, memory hits

### FORGE

- job: prepare the remediation path
- output: proposed action, alternatives, rollback context, rationale

### GUARDIAN

- job: govern the final review point
- output: approve, reject, or request modification with policy posture

### REPLICA

- product-direction job: reproduce the issue in a production-like environment
- output: reproduction result, validation notes, confidence shift

### TRACE

- product-direction job: narrow likely code path and debugging state
- output: suspected modules, divergence summary, debugging notes

## What Makes This Production-Shaped

Even in its current shipped form, NEXUS already has:

- explicit human review before action
- deterministic fallback for public stability
- visible memory and history
- auditable decisions
- a credible path from triage into deeper investigation

That is what makes it feel closer to a real product than a generic model wrapper.
