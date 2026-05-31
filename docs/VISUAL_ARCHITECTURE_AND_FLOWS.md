# NEXUS v2 Visual Architecture And Flows

Current as of 2026-05-31.

This document collects the core visual assets for final submission:

- product screenshots
- user-flow diagrams
- technical architecture diagrams
- agent collaboration design
- incident classification and resolution flow

## Product Screenshots

### Command Center

![Command Center](assets/screenshots/command-center.png)

### Incident Detail

![Incident Detail](assets/screenshots/incident-detail.png)

### Raw Log To Incident Flow

![Raw Log Flow](assets/screenshots/raw-log-incident-flow.png)

### Learning & Controls

![Learning and Controls](assets/screenshots/learning-controls.png)

## High-Level Product Flow

```mermaid
flowchart LR
    A["Operator or alert source"] --> B["Inputs / Queue"]
    B --> C["Incident Detail"]
    C --> D["SENTINEL classifies"]
    D --> E["PRISM diagnoses"]
    E --> F["FORGE proposes runbook"]
    F --> G["GUARDIAN approves or blocks"]
    G --> H["Execution state updates"]
    H --> I["Training and reward tracking"]
```

## User Journey Flow

```mermaid
flowchart TD
    A["Open Command Center"] --> B["Choose queue incident"]
    A --> C["Open Inputs"]
    C --> D["Paste raw logs"]
    D --> E["Submit raw logs"]
    E --> F["Redirect to created incident"]
    B --> G["Incident Detail"]
    F --> G
    G --> H["Inspect agent handoff thread"]
    G --> I["Approve runbook in Guardian"]
    I --> J["Execution becomes approved / executed"]
    G --> K["Optional BYO OpenAI key"]
    J --> L["Open Learning & Controls"]
```

## Frontend / Backend Surface Design

```mermaid
flowchart TD
    subgraph Frontend
        A["Command Center / Queue"]
        B["Incident Detail"]
        C["Inputs"]
        D["Learning & Controls"]
    end

    subgraph API
        E["FastAPI routes"]
        F["Incident service"]
        G["Training summary service"]
        H["Governance service"]
    end

    subgraph Runtime
        I["Incident persistence"]
        J["Audit / artifacts"]
        K["Deterministic demo payloads"]
        L["Optional request-scoped OpenAI path"]
    end

    A --> E
    B --> E
    C --> E
    D --> E
    E --> F
    E --> G
    E --> H
    F --> I
    F --> J
    F --> K
    F --> L
```

## Agent Collaboration Design

```mermaid
flowchart LR
    S["SENTINEL\nClassification bot"] --> P["PRISM\nDiagnosis bot"]
    P --> F["FORGE\nRemediation bot"]
    F --> G["GUARDIAN\nGovernance bot"]
    G --> X["Execution outcome"]

    S --- S1["Severity\nConfidence\nIncident label"]
    P --- P1["Root cause\nEvidence\nCorrelation"]
    F --- F1["Runbook\nRecommended action\nEstimated cost"]
    G --- G1["Approve\nReject\nRequest modification"]
```

## Classification And Incident Resolution Flow

```mermaid
sequenceDiagram
    participant U as Operator / Source
    participant I as Inputs / Queue
    participant S as SENTINEL
    participant P as PRISM
    participant F as FORGE
    participant G as GUARDIAN
    participant T as Training Surface

    U->>I: submit raw logs or open queue incident
    I->>S: normalized incident context
    S->>P: classification, severity, confidence
    P->>F: diagnosis, evidence, root cause
    F->>G: runbook proposal
    G-->>I: approve / reject / request modification
    G-->>U: visible governance decision
    I-->>T: reward, episode, and agent metrics
```

## Runtime Mode Design

```mermaid
flowchart TD
    A["Public HF Space"] --> B["Deterministic mode by default"]
    B --> C["No project OpenAI key required"]
    C --> D["Safe public demo"]

    A --> E["Optional BYO OpenAI key"]
    E --> F["Stored only in browser session"]
    F --> G["Sent request-scoped to backend"]
    G --> H["Live reasoning only when user chooses it"]
```

## Agent Design Summary

### SENTINEL

- role: classify incident and severity
- output: incident label, severity, confidence, reasoning
- visible in UI as the first handoff

### PRISM

- role: diagnose likely root cause
- output: diagnosis, evidence, correlation reasoning
- visible in UI as the second handoff

### FORGE

- role: generate remediation or runbook proposal
- output: runbook summary, candidate action, cost
- visible in UI as the third handoff

### GUARDIAN

- role: review safety and control execution
- output: approve, reject, or request modification
- visible in UI as the final explicit governance gate

## Why These Visuals Matter

These visuals support the final submission story clearly:

- the screenshots prove the product exists and is coherent
- the diagrams explain how the user moves through it
- the agent diagrams explain how the system collaborates
- the runtime-mode diagram explains why the public deployment is safe
