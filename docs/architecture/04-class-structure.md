# Class Structure

Key data models and their relationships in the NEXUS system.

## Core Data Models

```mermaid
classDiagram
    class IncidentRecord {
        str nexus_incident_id
        str external_id
        str title
        str severity
        str status
        str case_lifecycle
        str tenant_id
        str source
        str service
        str raw_input_text
        dict normalized_evidence
        str incident_id_classified
        str guardian_decision
        str guardian_reasoning
        str guardian_reviewed_at
        str guardian_policy_id
        str guardian_policy_name
        str created_at
        str updated_at
        +validate_severity_by_source()
    }
    
    class IncidentLifecycleResponse {
        str nexus_incident_id
        str external_id
        str title
        str severity
        str status
        str case_lifecycle
        dict normalized_evidence
        str incident_id_classified
        str guardian_decision
        dict sentinel_classification
        dict prism_diagnosis
        dict forge_recommendation
        dict guardian_decision_packet
        list~dict~ handoff_packets
        str created_at
        str updated_at
    }
    
    class QueueIncidentSummary {
        str nexus_incident_id
        str title
        str severity
        str status
        str incident_id_classified
        str case_lifecycle
        str source
        str created_at
        str updated_at
    }
    
    class QueueResponse {
        list~QueueIncidentSummary~ incidents
        int total_count
        str last_updated
    }
    
    class SystemContext {
        str service
        str language
        str infra
        list~str~ dependencies
    }
    
    class IncidentDefinition {
        str id
        str name
        str severity
        str difficulty
        list~str~ symptoms
        SystemContext system_context
        str root_cause
        str fix
    }
    
    class SentinelClassification {
        str incident_id
        str incident_name
        str severity
        float confidence
        str reasoning
    }
    
    class PrismDiagnosis {
        str hypothesis
        float confidence
        list~str~ affected_services
        str likely_root_cause
        dict context
    }
    
    class ReplayOutcome {
        str incident_id
        str posture
        str runtime_host
        int execution_duration_seconds
        list~dict~ outcomes
        bool succeeded
        str error_message
    }
    
    class TracePacket {
        str incident_id
        list~dict~ inspection_points
        list~str~ code_locations
        list~str~ remediation_paths
        dict context
    }
    
    class ForgeRecommendation {
        str incident_id
        str evidence_posture
        float confidence_score
        list~dict~ mitigations
        str reasoning
        dict evidence_summary
    }
    
    class GuardianDecision {
        str incident_id
        str decision
        str policy_id
        str policy_basis
        str reasoning
        str operator_id
        list~str~ approved_mitigations
        str audit_trail_id
        str approved_at
    }
    
    class AuthenticatedContext {
        str user_id
        str tenant_id
        list~str~ roles
        dict permissions
        str request_id
    }
    
    class NormalizedAlertEnvelope {
        str source
        str external_id
        str title
        str severity
        str service
        str detected_at
        dict observed_values
    }
    
    class RuntimeHostReplayRequest {
        str incident_id
        str docker_compose_path
        str runtime_token
        int timeout_seconds
        bool capture_metrics
    }
    
    class RuntimeHostReplayResponse {
        str replay_id
        str status
        dict runtime_metrics
        list~str~ execution_logs
        int execution_duration_ms
        bool succeeded
        str error_message
    }
    
    %% Relationships
    IncidentRecord --> SystemContext : uses
    IncidentRecord --> IncidentDefinition : references
    
    IncidentLifecycleResponse --> IncidentRecord : derived from
    IncidentLifecycleResponse --> SentinelClassification : contains
    IncidentLifecycleResponse --> PrismDiagnosis : contains
    IncidentLifecycleResponse --> ReplayOutcome : contains
    IncidentLifecycleResponse --> TracePacket : contains
    IncidentLifecycleResponse --> ForgeRecommendation : contains
    IncidentLifecycleResponse --> GuardianDecision : contains
    
    QueueResponse --> QueueIncidentSummary : aggregates
    
    IncidentDefinition --> SystemContext : has
    
    SentinelClassification --> IncidentDefinition : references
    
    RuntimeHostReplayRequest --> IncidentDefinition : references
    RuntimeHostReplayRequest --> RuntimeHostReplayResponse : produces
```

## Agent Output Models

Each agent produces a structured output that feeds into the incident record:

### SENTINEL Output: `SentinelClassification`

```python
@dataclass
class SentinelClassification:
    incident_id: str              # One of INC001-INC007
    incident_name: str
    severity: str                 # P0-P4
    confidence: float             # 0.0-1.0
    reasoning: str
```

**Used by:** PRISM, REPLICA, TRACE, FORGE  
**Stored in:** `IncidentRecord.incident_id_classified`

---

### PRISM Output: `PrismDiagnosis`

```python
@dataclass
class PrismDiagnosis:
    hypothesis: str               # Root cause hypothesis
    confidence: float             # 0.0-1.0
    affected_services: list[str]
    likely_root_cause: str
    context: dict                 # Evidence used in diagnosis
```

**Used by:** REPLICA, TRACE, FORGE  
**Stored in:** `IncidentLifecycleResponse.prism_diagnosis`

---

### REPLICA Output: `ReplayOutcome`

```python
@dataclass
class ReplayOutcome:
    incident_id: str
    posture: str                  # RUNTIME_BACKED or SCAFFOLD_ONLY
    runtime_host: str             # Docker host URL (if ran)
    execution_duration_seconds: int
    outcomes: list[dict]          # Runtime metrics before/after
    succeeded: bool
    error_message: str | None
```

**Evidence Posture:**
- `RUNTIME_BACKED` — Incident reproduced successfully
- `SCAFFOLD_ONLY` — Not in runtime-backed set (INC001-INC003)

**Stored in:** `IncidentLifecycleResponse.replay_outcome`

---

### TRACE Output: `TracePacket`

```python
@dataclass
class TracePacket:
    incident_id: str
    inspection_points: list[dict]  # {file, line, context}
    code_locations: list[str]      # File:line pairs
    remediation_paths: list[str]
    context: dict                  # Evidence used for inspection
```

**Stored in:** `IncidentLifecycleResponse.trace_packet`

---

### FORGE Output: `ForgeRecommendation`

```python
@dataclass
class ForgeRecommendation:
    incident_id: str
    evidence_posture: str          # RUNTIME_BACKED, INFERENCE_FIRST, etc.
    confidence_score: float        # 0.0-1.0
    mitigations: list[dict]        # Ranked by feasibility
    reasoning: str
    evidence_summary: dict         # Which evidence informed ranking
```

**Mitigation Structure:**
```python
{
    "action": "drain hot pods",
    "risk_level": "low",
    "impact": "immediate",
    "confidence": 0.95,
    "reasoning": "Runtime outcomes show CPU saturation..."
}
```

**Stored in:** `IncidentLifecycleResponse.forge_recommendation`

---

### GUARDIAN Output: `GuardianDecision`

```python
@dataclass
class GuardianDecision:
    incident_id: str
    decision: str                  # approve, reject, or request_modification
    policy_id: str
    policy_basis: str
    reasoning: str
    operator_id: str
    approved_mitigations: list[str]
    audit_trail_id: str
    approved_at: str
```

**Stored in:** `IncidentRecord.guardian_decision` + audit log

---

## Request/Response Models

### `/api/v1/incidents/raw-text`

**Request:** `RawIncidentTextRequest`
```python
{
    "title": str,
    "raw_logs": str,
    "service": str | None,
    "severity": str | None
}
```

**Response:** `IncidentLifecycleResponse`

---

### `/api/v1/incidents/{id}/guardian-decision`

**Request:** `GuardianDecisionRequest`
```python
{
    "decision": "approve" | "reject" | "request_modification",
    "reasoning": str,
    "selected_mitigation": str | None
}
```

**Response:** `IncidentLifecycleResponse`

---

### `/api/v1/incidents`

**Response:** `QueueResponse`
```python
{
    "incidents": [QueueIncidentSummary, ...],
    "total_count": int,
    "last_updated": str
}
```

---

## Type Definitions

### Enums

**Status:**
```
investigating | resolved | blocked_by_guardian | needs_modification
```

**Case Lifecycle:**
```
created | triaged | investigating | handoff_prepared | awaiting_review | approved | executed | closed
```

**Guardian Decision:**
```
pending | approve | reject | request_modification
```

**Evidence Posture:**
```
RUNTIME_BACKED | INFERENCE_FIRST | SCAFFOLD_ONLY | UNSUPPORTED
```

**Source:**
```
datadog | prometheus | webhook | raw_text | manual_form | slack_command | stream_anomaly | batch_import
```

---

## Storage Mapping

How these models map to database tables:

| Class | Primary Table | Audit Table |
|---|---|---|
| `IncidentRecord` | `incidents` | `audit_logs` |
| `SentinelClassification` | incidents.incident_id_classified | audit_logs |
| `PrismDiagnosis` | incidents.normalized_evidence (JSON) | audit_logs |
| `ReplayOutcome` | replay_history | audit_logs |
| `GuardianDecision` | incidents.guardian_decision | audit_logs |

All decision history is **immutable** once written to `audit_logs`.

---

## Design Patterns

1. **Pydantic Models:** All classes inherit from `BaseModel` for validation
2. **Immutable Audit Trail:** Decisions logged before updating primary records
3. **Tenant Isolation:** All models include `tenant_id` for multi-tenant support
4. **Nullable Timestamps:** Lifecycle events timestamped only when they occur
5. **Flat Dicts:** Nested data stored as JSON in `normalized_evidence` (no deep nesting)
