# Data Flow

End-to-end incident lifecycle from intake through Guardian decision and handoff.

## Fresh Raw-Text Submission Flow

Complete sequence from operator submitting text to Guardian approval.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant UI as /inputs UI
    participant API as FastAPI Server
    participant INC as IncidentService
    participant INT as IntakeService
    participant SENT as SentinelAgent
    participant PRISM as PrismAgent
    participant REP as ReplayService
    participant FOR as ForgeAgent
    participant GUAR as GuardianAgent
    participant DB as SQLite Database
    
    Op->>UI: Submit raw incident text
    UI->>API: POST /api/v1/incidents/raw-text
    Note over API: RawIncidentTextRequest parsed
    
    API->>INC: process_raw_incident_submission(request)
    
    INC->>INT: build_raw_text_normalized_evidence()
    INT->>INT: Extract severity, service, language
    INT->>INT: Calculate input quality score
    INT->>INC: Return NormalizedEvidence
    
    INC->>SENT: classify(raw_symptoms, system_context)
    SENT->>SENT: Score all 7 families
    SENT->>INC: Return SentinelClassification
    Note over SENT: incident_id, confidence, reasoning
    
    INC->>PRISM: diagnose(classification, evidence)
    PRISM->>INC: Return PrismDiagnosis
    Note over PRISM: hypothesis, confidence, affected_services
    
    INC->>REP: attempt_runtime_replay(incident_id)
    alt Incident in {INC001, INC002, INC003}
        REP->>REP: Call Docker runtime-host via REST
        REP->>INC: Return ReplayOutcome with metrics
        Note over REP: posture=RUNTIME_BACKED
    else Other family
        REP->>INC: Return posture=SCAFFOLD_ONLY
    end
    
    INC->>FOR: rank_mitigations(evidence, diagnosis)
    FOR->>FOR: Collect runtime outcomes + memory
    FOR->>FOR: Score each mitigation by feasibility
    FOR->>INC: Return ForgeRecommendation
    Note over FOR: confidence_score, mitigations[], evidence_posture
    
    INC->>INC: Create IncidentRecord
    INC->>DB: Save incident (status=investigating)
    DB->>DB: INSERT or UPDATE incidents table
    
    INC->>API: Return IncidentLifecycleResponse
    API->>Op: HTTP 201 + incident_id = nxs_...
    Op->>Op: Navigate to /incident?nexus_incident_id=nxs_...
    
    Op->>UI: Review incident + FORGE recommendation
    Op->>UI: Click "Approve" in Guardian panel
    UI->>API: POST /api/v1/incidents/{id}/guardian-decision
    Note over UI: GuardianDecisionRequest with approve/reject
    
    API->>INC: process_guardian_decision(incident_id, approve)
    
    INC->>GUAR: validate_and_approve(incident_id)
    GUAR->>GUAR: Check governance policy
    GUAR->>GUAR: Validate operator permissions
    GUAR->>INC: Return GuardianDecision
    
    INC->>DB: Update incident.guardian_decision=approve
    INC->>DB: Update incident.case_lifecycle=approved
    INC->>DB: INSERT into audit_logs (decision + reasoning)
    
    INC->>INC: Generate handoff packet
    INC->>API: Return updated IncidentLifecycleResponse
    API->>Op: HTTP 200 + approval confirmation
    Op->>UI: Click "Export Handoff" button
    UI->>API: GET /api/v1/incidents/{id}/handoff-packet
    API->>INC: build_handoff_packet(incident_id)
    INC->>DB: Read incident + all agent packets
    API->>Op: Download: nexus_{id}_handoff.json
```

## Webhook Ingestion Flow

Datadog or PagerDuty alert → NEXUS incident.

```mermaid
sequenceDiagram
    participant DD as Datadog
    participant API as FastAPI Server
    participant ALERT as AlertNormalizer
    participant INC as IncidentService
    participant SENT as SentinelAgent
    participant DB as SQLite Database
    
    DD->>API: POST /api/v1/webhooks/datadog
    Note over DD: Alert JSON payload
    
    API->>API: verify_webhook_signature(request)
    Note over API: Check NEXUS_WEBHOOK_SIGNING_SECRET
    
    API->>ALERT: normalize_datadog_alert(payload)
    ALERT->>ALERT: Extract: service, severity, title
    ALERT->>ALERT: Parse metrics and thresholds
    ALERT->>API: Return NormalizedAlertEnvelope
    
    API->>INC: create_incident_from_webhook(normalized)
    
    INC->>SENT: classify(alert_symptoms, system_context)
    SENT->>INC: Return SentinelClassification
    
    INC->>INC: Create IncidentRecord
    INC->>INC: Set status=investigating
    INC->>INC: Set source=datadog
    
    INC->>DB: INSERT new incident
    INC->>DB: INSERT webhook_metadata
    
    INC->>API: Return IncidentLifecycleResponse
    API->>DD: HTTP 200 OK
    Note over DD: Webhook delivery confirmed
    
    Note over API: Incident now in /queue for operator review
```

## Guardian Rejection and Retry Flow

Operator rejects recommendation, system asks for modification.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant UI as /incident Console
    participant API as FastAPI Server
    participant INC as IncidentService
    participant GUAR as GuardianAgent
    participant DB as SQLite Database
    
    Op->>UI: Review incident detail
    Op->>UI: Click "Reject" in Guardian panel
    UI->>API: POST /api/v1/incidents/{id}/guardian-decision
    Note over UI: {"decision": "reject", "reasoning": "..."}
    
    API->>INC: process_guardian_decision(incident_id, reject)
    
    INC->>GUAR: validate_rejection(incident_id)
    GUAR->>GUAR: Check if rejection allowed by policy
    GUAR->>INC: Return GuardianDecision
    
    INC->>DB: Update guardian_decision=reject
    INC->>DB: Update case_lifecycle=needs_modification
    INC->>DB: INSERT into audit_logs (rejection + operator reasoning)
    
    INC->>API: Return updated IncidentLifecycleResponse
    Note over API: status="needs_modification", case_lifecycle="needs_modification"
    API->>Op: HTTP 200 + rejection confirmation
    
    Op->>UI: Incident moves to "Needs Modification" queue
    Op->>UI: Click "Request Different Mitigation"
    UI->>API: POST /api/v1/incidents/{id}/request-modification
    Note over UI: User feedback on why rejection
    
    API->>INC: process_modification_request(incident_id, feedback)
    
    INC->>INC: Re-run FORGE with feedback as constraint
    INC->>INC: Generate alternate mitigations
    
    INC->>DB: UPDATE incident with new FORGE ranking
    INC->>DB: INSERT into modification_history
    
    INC->>API: Return updated IncidentLifecycleResponse
    API->>Op: HTTP 200 + new options
    
    Op->>UI: Review new mitigation options
    Op->>UI: Click "Approve" on preferred mitigation
    UI->>API: POST /api/v1/incidents/{id}/guardian-decision
    Note over UI: {"decision": "approve", "selected_mitigation": "..."}
    
    API->>INC: process_guardian_decision(incident_id, approve)
    INC->>GUAR: Approve new mitigation
    INC->>DB: UPDATE guardian_decision=approve
    INC->>INC: Generate handoff packet
    INC->>API: Return final IncidentLifecycleResponse
    API->>Op: HTTP 200 + ready for handoff
```

## Out-of-Scope Incident Handling

Operator submits incident that doesn't match any 7 supported families.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant UI as /inputs UI
    participant API as FastAPI Server
    participant INC as IncidentService
    participant SENT as SentinelAgent
    participant DB as SQLite Database
    
    Op->>UI: Submit raw incident text
    UI->>API: POST /api/v1/incidents/raw-text
    
    API->>INC: process_raw_incident_submission(request)
    
    INC->>SENT: classify(raw_symptoms, system_context)
    SENT->>SENT: Score all 7 families
    Note over SENT: Best match: INC009 (0.45 confidence)
    Note over SENT: INC009 is catalogued but NOT wired
    
    alt Best match has payload
        SENT->>INC: Return SentinelClassification(INC009, 0.45)
        INC->>INC: Try get_incident_details(INC009)
        INC->>DB: unknown_incident_id error!
        INC->>API: HTTP 422 Unprocessable Entity
        API->>Op: "INC009 is not yet supported. Please contact support."
    else Fallback to similar supported family
        SENT->>INC: Return SentinelClassification(INC005, 0.65)
        Note over SENT: Fallback to similar supported family
        INC->>INC: Create incident as INC005
        INC->>INC: Add note: "Fallback classification due to low family match"
        INC->>DB: INSERT incident
        INC->>API: Return IncidentLifecycleResponse
        API->>Op: HTTP 201 + warning message
    end
```

---

## Database Schema (Key Tables)

```mermaid
erDiagram
    INCIDENTS ||--o{ AUDIT_LOGS : generates
    INCIDENTS ||--o{ HANDOFF_PACKETS : has
    INCIDENTS ||--o{ REPLAY_HISTORY : has
    
    INCIDENTS {
        string nexus_incident_id PK
        string external_id
        string title
        string severity
        string status
        string case_lifecycle
        string incident_id_classified
        string tenant_id
        string source
        string service
        text raw_input_text
        text normalized_evidence
        string guardian_decision
        text guardian_reasoning
        timestamp created_at
        timestamp updated_at
    }
    
    AUDIT_LOGS {
        string audit_id PK
        string nexus_incident_id FK
        string event_type
        text event_data
        string operator_id
        timestamp timestamp
    }
    
    HANDOFF_PACKETS {
        string packet_id PK
        string nexus_incident_id FK
        string agent_name
        text packet_contents
        timestamp created_at
    }
    
    REPLAY_HISTORY {
        string replay_id PK
        string nexus_incident_id FK
        string docker_host
        text execution_logs
        text outcomes
        timestamp executed_at
    }
```

---

## Key Design Patterns

1. **Intake Normalization:** All input formats → `NormalizedEvidence` (deterministic, no LLM)
2. **Linear Handoff:** Each agent's output feeds next agent's input
3. **Durable Decisions:** All agent outputs + Guardian decision persisted to SQLite
4. **Explicit Rejection:** Out-of-scope incidents fail fast with clear error
5. **Modification Loop:** Operator can request alternate rankings without re-intake
6. **Audit Trail:** Every decision, rejection, and modification logged immutably
