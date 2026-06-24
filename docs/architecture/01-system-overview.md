# System Overview

High-level architecture showing external inputs, NEXUS boundary, the 6-agent pipeline, storage, and deployment context.

## Architecture Diagram

```mermaid
graph TB
    subgraph "External Data Sources"
        UI["📋 /inputs UI\n(operator submission)"]
        WH["🔗 Webhook API\n(Datadog, PagerDuty)"]
        DD["📊 Datadog Adapter\n(alert normalization)"]
        PD["🚨 PagerDuty Adapter\n(incident ingestion)"]
    end
    
    subgraph "NEXUS Application Boundary"
        subgraph "Intake Layer"
            INT["Intake Service\n(server/services/intake.py)\nNormalization + Quality Scoring"]
        end
        
        subgraph "Agent Pipeline (6 agents)"
            S["SENTINEL\n(server/agents/sentinel.py)\nClassification: 7 families"]
            P["PRISM\n(server/agents/prism.py)\nRoot Cause Hypothesis"]
            R["REPLICA\n(server/services/replay.py)\nRuntime Reproduction\n(Docker: INC001-INC003)"]
            T["TRACE\n(server/services/investigation.py)\nCode Inspection"]
            F["FORGE\n(server/agents/forge.py)\nMitigation Ranking"]
            G["GUARDIAN\n(server/agents/guardian.py)\nApproval + Governance"]
        end
        
        subgraph "Support Services"
            CLASS["Classification\n(server/services/classification.py)"]
            INV["Investigation\n(server/services/investigation.py)"]
            RS["Runtime State\n(server/services/runtime_state.py)"]
            MEMO["Memory + Context\n(server/services/*)"]
        end
        
        subgraph "Storage Layer"
            DB["SQLite Database\n(artifacts/incidents.json)\nIncidentRecord, audit logs"]
            PACKS["Replica Packs\n(replica_packs/)\nINC001, INC002, INC003"]
            ARTIFACTS["Artifact Store\n(artifacts/)\nReplay history, decisions"]
        end
    end
    
    subgraph "Outputs"
        QUEUE["📈 Queue + Summary\nQueueIncidentSummary"]
        DETAIL["🔍 Incident Detail\nIncidentLifecycleResponse"]
        HANDOFF["📦 Handoff Packet\n(engineer handoff export)"]
        AUDIT["📝 Audit Log\n(compliance + replay)"]
    end
    
    subgraph "Deployment: Oracle Cloud"
        VM["VM: E2.1.Micro\n(1GB RAM, Frankfurt)"]
        DOCKER["Docker Container\n(uvicorn server.app:app)"]
        NGINX["nginx Reverse Proxy\nHTTPS via Let's Encrypt"]
        DNS["duckdns.org DNS\n(nexus-triage)"]
    end
    
    %% Data flow connections
    UI --> INT
    WH --> INT
    DD --> INT
    PD --> INT
    
    INT --> S
    S --> CLASS
    CLASS --> P
    P --> R
    R --> RS
    RS --> T
    T --> INV
    INV --> F
    F --> MEMO
    MEMO --> G
    
    G --> QUEUE
    G --> DETAIL
    G --> HANDOFF
    G --> AUDIT
    
    %% Storage connections
    S -.->|read| PACKS
    R -.->|use| PACKS
    G -.->|persist| DB
    G -.->|archive| ARTIFACTS
    
    %% Deployment connections
    DETAIL --> NGINX
    QUEUE --> NGINX
    NGINX --> DNS
    DOCKER -->|runs| NGINX
    VM -->|hosts| DOCKER
    DB -->|persistent vol| VM
    PACKS -->|mounted| DOCKER
    
    %% Styling
    classDef agent fill:#4A90E2,stroke:#2E5C8A,color:#fff
    classDef storage fill:#50C878,stroke:#2D7A4A,color:#fff
    classDef external fill:#FFB347,stroke:#B8860B,color:#000
    classDef deploy fill:#9B59B6,stroke:#6C3A70,color:#fff
    
    class S,P,R,T,F,G agent
    class DB,PACKS,ARTIFACTS storage
    class UI,WH,DD,PD external
    class VM,DOCKER,NGINX,DNS deploy
```

## Component Roles

### Intake Layer
- **Purpose:** Normalize diverse input formats (webhooks, raw text, manual forms) into unified `NormalizedEvidence`
- **Input:** Raw incident data from any source (Datadog, PagerDuty, /inputs UI, Slack)
- **Output:** `NormalizedEvidence` dict + quality metrics
- **Location:** `server/services/intake.py`

### Agent Pipeline

**SENTINEL** (Classification)
- Matches symptoms and context against 7-family catalogue
- Returns: `SentinelClassification(incident_id, severity, confidence, reasoning)`
- Pattern-based (deterministic) or LLM-based (if client provided)

**PRISM** (Diagnosis)
- Generates root cause hypothesis from classification context
- Stub implementation (returns structured reasoning)
- Returns: hypothesis + confidence

**REPLICA** (Reproduction)
- Runtime reproducer for INC001, INC002, INC003 only
- Delegates to Docker runtime-host via REST
- Returns: runtime outcomes or "not reproducible" for other families
- Uses: `server/services/replay.py`

**TRACE** (Debugging)
- Code inspection and debugging guidance
- Bounded to curated packs only
- Returns: code locations, inspection points, remediation paths
- Uses: `server/services/investigation.py`

**FORGE** (Mitigation)
- Ranks mitigations using: runtime outcomes (if available) + inference + memory
- Scores each option with confidence and risk
- Returns: ranked mitigation list + evidence posture
- Uses: `server/agents/forge.py`

**GUARDIAN** (Approval)
- Human approval gate with governance policy enforcement
- Records decision, reasoning, and execution context
- Transitions case to "awaiting_action" only if approved
- Uses: `server/agents/guardian.py`

### Storage

**SQLite Database** (`artifacts/incidents.json`)
- Persists: `IncidentRecord`, audit logs, decision history
- Tenant-isolated schema
- Durable across container restarts

**Replica Packs** (`replica_packs/`)
- Docker Compose definitions for INC001, INC002, INC003
- Mounted into runtime-host container
- Enable REPLICA to reproduce in isolated environments

**Artifact Store** (`artifacts/`)
- Replay execution history
- Guardian decisions and reasoning
- Memory/context snapshots for pilot use

### Deployment on Oracle Cloud

**Infrastructure:**
- **VM:** E2.1.Micro (1GB RAM, single vCPU, Frankfurt region)
- **SSH:** `ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239`

**Layers:**
1. **nginx** — Reverse proxy, SSL termination (Let's Encrypt), HTTPS → HTTP routing
2. **Docker Container** — uvicorn FastAPI server on port 7860
3. **Named Volume** — `nexus-data` → `/app/artifacts` (incident data persistence)
4. **DNS** — duckdns.org dynamic DNS (`nexus-triage.duckdns.org`)

**Automatic deployment:** GitHub Actions triggers on `git push origin master`
- Run tests (495 pytest + 16 browser tests)
- Deploy Docker image to Oracle Cloud
- Run smoke tests against production

---

## Key Design Points

1. **Single Responsibility:** Each agent has one clear input/output contract
2. **Evidence Postures:** 🟢 runtime-backed, 🟡 inference-first, 🔴 unsupported
3. **Bounded Scope:** Only 7 families with full payloads; 4 catalogued but not wired
4. **Deterministic Intake:** No LLM required for normalization (improves consistency)
5. **Human Gate:** Guardian approval required before any action
6. **Durable Storage:** Incident data persists across restarts; audit logs preserved
7. **Isolated Reproduction:** REPLICA runs in separate Docker container, not host system
