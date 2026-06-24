# Sequence Diagrams

Key user journeys and system interactions.

## Sequence 1: New Pilot Customer First Incident

Operator from pilot customer receives their first incident, submits it to NEXUS, and gets a Guardian-approved recommendation.

```mermaid
sequenceDiagram
    participant Operator
    participant Browser as Web Browser
    participant API as FastAPI Server
    participant NEXUS as IncidentService
    participant Agents as 6-Agent Pipeline
    participant DB as SQLite
    
    Operator->>Browser: Navigate to /inputs
    Browser->>API: GET /inputs
    API->>Browser: Render form
    
    Operator->>Browser: Paste raw logs
    Operator->>Browser: Enter service, severity
    Operator->>Browser: Click Submit
    
    Browser->>API: POST /api/v1/incidents/raw-text
    Note over API: RawIncidentTextRequest parsed
    
    API->>NEXUS: process_raw_incident_submission()
    
    NEXUS->>Agents: SENTINEL.classify()
    Note over Agents: Match symptoms vs 11 families, filter to 8 supported
    Agents->>NEXUS: INC001, confidence=0.87
    
    NEXUS->>Agents: PRISM.diagnose()
    Note over Agents: Generate hypothesis
    Agents->>NEXUS: "Retry storm on auth timeout"
    
    NEXUS->>Agents: REPLICA.attempt_replay()
    Note over Agents: Docker INC001 pack
    Agents->>NEXUS: Runtime metrics, posture=RUNTIME_BACKED
    
    NEXUS->>Agents: TRACE.inspect()
    Note over Agents: Code locations
    Agents->>NEXUS: Inspection points + remediation
    
    NEXUS->>Agents: FORGE.rank_mitigations()
    Note over Agents: Score by feasibility + impact
    Agents->>NEXUS: 3 ranked mitigations, confidence=0.92
    
    NEXUS->>DB: INSERT IncidentRecord(status=investigating)
    DB->>DB: Persist to artifacts/incidents.json
    
    NEXUS->>API: Return IncidentLifecycleResponse
    API->>Browser: HTTP 201 + nexus_incident_id
    
    Note over Operator: Incident created; now reviewing
    
    Operator->>Browser: Click incident from queue
    Browser->>API: GET /incident?nexus_incident_id=nxs_...
    API->>NEXUS: load_incident(incident_id)
    NEXUS->>DB: Read from SQLite
    API->>Browser: Full IncidentLifecycleResponse
    Browser->>Operator: Render incident console
    
    Note over Operator: Reviews all agent packets:<br/>Classification, Diagnosis, Replay,<br/>Inspection Points, Recommendations
    
    Operator->>Browser: Click "Approve" in Guardian panel
    Browser->>API: POST /api/v1/incidents/{id}/guardian-decision
    Note over Browser: {"decision": "approve", "reasoning": "..."}
    
    API->>NEXUS: process_guardian_decision(approve)
    NEXUS->>Agents: GUARDIAN.validate()
    Note over Agents: Check policy, record decision
    Agents->>NEXUS: GuardianDecision(approve)
    
    NEXUS->>DB: UPDATE incident.guardian_decision=approve
    NEXUS->>DB: INSERT audit_log(decision + reasoning)
    NEXUS->>API: Return updated IncidentLifecycleResponse
    
    API->>Browser: HTTP 200 + approval confirmation
    Browser->>Operator: Show "Approved" badge
    
    Operator->>Browser: Click "Export Handoff"
    Browser->>API: GET /api/v1/incidents/{id}/handoff-packet
    API->>NEXUS: build_handoff_packet(incident_id)
    NEXUS->>DB: Read incident + all packets
    API->>Browser: Download nexus_{id}_handoff.json
    
    Note over Operator: Handoff ready for engineering<br/>Complete workflow in 5 minutes
```

---

## Sequence 2: Webhook-Triggered Incident (Datadog)

Datadog fires an alert → NEXUS ingests → Operator reviews in queue.

```mermaid
sequenceDiagram
    participant Datadog
    participant API as FastAPI Webhook
    participant NEXUS as IncidentService
    participant SENTINEL as SentinelAgent
    participant DB as SQLite
    participant Operator
    participant Browser
    
    Datadog->>API: POST /api/v1/webhooks/datadog
    Note over Datadog: Alert JSON: CPU>90%, service=api-gateway
    
    API->>API: verify_webhook_signature(request)
    Note over API: Check NEXUS_WEBHOOK_SIGNING_SECRET
    
    API->>API: AlertNormalizer.normalize(payload)
    Note over API: Extract service, severity, metrics
    
    API->>NEXUS: create_incident_from_webhook(normalized)
    
    NEXUS->>SENTINEL: classify(alert_symptoms, context)
    Note over SENTINEL: Best match: INC001 (API Timeout)
    SENTINEL->>NEXUS: SentinelClassification(INC001, 0.89)
    
    NEXUS->>NEXUS: Create IncidentRecord
    Note over NEXUS: status=investigating<br/>source=datadog<br/>incident_id=INC001
    
    NEXUS->>DB: INSERT new incident
    NEXUS->>DB: INSERT webhook_metadata
    
    NEXUS->>API: Return IncidentLifecycleResponse
    API->>Datadog: HTTP 200 OK
    Note over Datadog: Webhook delivery confirmed
    
    Note over Operator: Webhook ingested; incident now in queue
    
    Operator->>Browser: Refresh /queue
    Browser->>API: GET /api/v1/incidents
    API->>NEXUS: list_incidents()
    NEXUS->>DB: SELECT * FROM incidents ORDER BY created_at DESC
    API->>Browser: QueueResponse with new webhook incident
    
    Browser->>Operator: Incident appears at top of queue
    Note over Browser: Title from Datadog, severity P1
    
    Operator->>Browser: Click to open incident detail
    Browser->>API: GET /incident?nexus_incident_id=nxs_...
    API->>Browser: Full incident lifecycle response
    Browser->>Operator: Render console (but GUARDIAN pending)
    
    Note over Operator: System has classified but not<br/>approved/executed yet
```

---

## Sequence 3: Guardian Rejection and Retry

Operator rejects recommendation, system asks for modification.

```mermaid
sequenceDiagram
    participant Operator
    participant Browser as /incident Console
    participant API as FastAPI
    participant NEXUS as IncidentService
    participant GUARDIAN as GuardianAgent
    participant FORGE as ForgeAgent
    participant DB as SQLite
    
    Operator->>Browser: Review FORGE recommendation
    Note over Browser: 3 mitigations ranked by feasibility
    
    Operator->>Browser: Click "Reject" button
    Browser->>API: POST /api/v1/incidents/{id}/guardian-decision
    Note over Browser: {"decision": "reject", "reasoning": "..."}
    
    API->>NEXUS: process_guardian_decision(reject)
    
    NEXUS->>GUARDIAN: validate_rejection(incident_id)
    Note over GUARDIAN: Check if allowed by policy
    GUARDIAN->>NEXUS: GuardianDecision(reject)
    
    NEXUS->>DB: UPDATE guardian_decision=reject
    NEXUS->>DB: UPDATE case_lifecycle=needs_modification
    NEXUS->>DB: INSERT audit_log(rejection + operator feedback)
    
    NEXUS->>API: Return updated response
    API->>Browser: HTTP 200 + rejection confirmed
    Browser->>Operator: Show "Needs Modification" status
    
    Note over Operator: Incident now in "Needs Modification" queue
    
    Operator->>Browser: Click "Request Different Mitigation"
    Browser->>API: POST /api/v1/incidents/{id}/request-modification
    Note over Browser: Send feedback: "Patch too risky, prefer scaling"
    
    API->>NEXUS: process_modification_request(incident_id, feedback)
    
    NEXUS->>FORGE: re_rank_mitigations(feedback)
    Note over FORGE: Constraint: avoid patch-based fixes
    FORGE->>NEXUS: New ranking with scaling first
    
    NEXUS->>DB: UPDATE incident with new FORGE results
    NEXUS->>DB: INSERT modification_history
    
    NEXUS->>API: Return updated response with new recommendations
    API->>Browser: HTTP 200 + new mitigation options
    Browser->>Operator: Render revised FORGE ranking
    
    Operator->>Browser: Review new options (scaling now #1)
    Operator->>Browser: Click "Approve" on preferred option
    Browser->>API: POST /api/v1/incidents/{id}/guardian-decision
    Note over Browser: {"decision": "approve", "selected_mitigation": "scale gateway"}
    
    API->>NEXUS: process_guardian_decision(approve, mitigation=scale)
    
    NEXUS->>GUARDIAN: validate_and_approve(incident_id, mitigation)
    GUARDIAN->>NEXUS: GuardianDecision(approve)
    
    NEXUS->>DB: UPDATE guardian_decision=approve
    NEXUS->>DB: UPDATE approved_mitigations=[scale...]
    NEXUS->>DB: INSERT audit_log(final approval)
    
    NEXUS->>API: Return final IncidentLifecycleResponse
    API->>Browser: HTTP 200 + approval
    Browser->>Operator: Show "Approved" + handoff ready
    
    Note over Operator: Complete: Rejected → Modified → Approved
```

---

## Sequence 4: Out-of-Scope Incident

Operator submits incident that doesn't match any supported family.

```mermaid
sequenceDiagram
    participant Operator
    participant Browser as /inputs UI
    participant API as FastAPI
    participant NEXUS as IncidentService
    participant SENTINEL as SentinelAgent
    participant DB as SQLite
    
    Operator->>Browser: Submit raw logs for obscure issue
    Browser->>API: POST /api/v1/incidents/raw-text
    Note over API: Symptoms don't match INC001-INC007
    
    API->>NEXUS: process_raw_incident_submission()
    
    NEXUS->>SENTINEL: classify(symptoms, context)
    SENTINEL->>SENTINEL: Score all 11 families in catalogue
    Note over SENTINEL: Best match: INC004 (Load Balancer)<br/>Confidence: 0.35
    SENTINEL->>NEXUS: SentinelClassification(INC004, 0.35)
    
    NEXUS->>NEXUS: Try get_incident_details(INC004)
    Note over NEXUS: INC004 not in incident_payloads!<br/>ValueError: unknown_incident_id
    
    alt INC004 is catalogued but not wired
        NEXUS->>API: HTTP 422 Unprocessable Entity
        API->>Browser: Error response
        Browser->>Operator: Message: "INC004 not yet supported.<br/>Please contact support."
    else Try fallback to similar family
        NEXUS->>SENTINEL: try_fallback(best_unsupported=INC004)
        SENTINEL->>SENTINEL: Find highest-confidence supported family<br/>Second best: INC005 (Queue Backlog)<br/>Confidence: 0.28
        SENTINEL->>NEXUS: SentinelClassification(INC005, 0.28, fallback=true)
        
        NEXUS->>NEXUS: Create IncidentRecord
        Note over NEXUS: incident_id=INC005<br/>classification_confidence=0.28<br/>fallback_note: "Out-of-scope; classified as INC005"
        
        NEXUS->>DB: INSERT incident
        NEXUS->>API: Return IncidentLifecycleResponse
        API->>Browser: HTTP 201 + warning
        Browser->>Operator: Message: "Low confidence match.<br/>This may not be INC005.<br/>Consider reaching out to engineering."
        
        Note over Operator: Incident created but flagged as uncertain
    end
```

---

## Sequence 5: Incident with Runtime-Backed Evidence

Complete flow showing REPLICA achieving runtime reproduction.

```mermaid
sequenceDiagram
    participant Operator
    participant Browser
    participant API
    participant NEXUS
    participant SENTINEL as SentinelAgent
    participant PRISM as PrismAgent
    participant REPLICA as ReplayService
    participant Runtime as Docker Runtime Host
    participant FORGE as ForgeAgent
    participant GUARDIAN as GuardianAgent
    
    Operator->>Browser: Submit incident for INC001
    Browser->>API: POST /api/v1/incidents/raw-text
    
    API->>NEXUS: process_raw_incident_submission()
    
    NEXUS->>SENTINEL: classify()
    SENTINEL->>NEXUS: INC001, confidence=0.92
    
    NEXUS->>PRISM: diagnose()
    PRISM->>NEXUS: "Retry storm exhausted workers"
    
    NEXUS->>REPLICA: attempt_runtime_replay(INC001)
    Note over REPLICA: INC001 is in runtime-backed set
    
    REPLICA->>REPLICA: Get Docker environment
    Note over REPLICA: ENABLE_RUNTIME_HOST_RELAY=1
    
    REPLICA->>Runtime: POST /api/v1/replay/start
    Note over Runtime: Docker Compose up<br/>Docker volumes mounted<br/>INC001 pack loaded
    Runtime->>Runtime: Simulate transaction flow
    Runtime->>Runtime: Apply gradual latency increase
    Runtime->>Runtime: Measure metrics: CPU, latency, throughput
    
    Runtime->>REPLICA: Outcomes: cpu spike 54→95%, latency 240→5000ms
    REPLICA->>NEXUS: ReplayOutcome(posture=RUNTIME_BACKED, metrics=[...])
    
    NEXUS->>FORGE: rank_mitigations(evidence=runtime_backed)
    Note over FORGE: Evidence posture: RUNTIME_BACKED<br/>Confidence boost: +30%
    FORGE->>FORGE: Score mitigations using runtime metrics
    FORGE->>NEXUS: Ranking: [drain, cap retries, scale]<br/>confidence=0.95 (boosted from runtime)
    
    NEXUS->>DB: INSERT incident + all packets
    
    NEXUS->>API: Return response
    API->>Browser: IncidentLifecycleResponse with runtime evidence
    Browser->>Operator: Console shows 🟢 RUNTIME-BACKED badge
    
    Operator->>Browser: Reviews console
    Note over Browser: SENTINEL: INC001, 92%<br/>PRISM: Retry storm hypothesis<br/>REPLICA: ✅ Reproduced with metrics<br/>FORGE: Drain pods (95% confidence)
    
    Operator->>Browser: Click "Approve"
    Browser->>API: POST /api/v1/incidents/{id}/guardian-decision
    
    API->>NEXUS: process_guardian_decision(approve)
    NEXUS->>GUARDIAN: validate_and_approve()
    GUARDIAN->>NEXUS: GuardianDecision(approve, confidence_high=true)
    
    NEXUS->>DB: UPDATE guardian_decision=approve
    NEXUS->>API: Return final response
    API->>Browser: HTTP 200
    
    Browser->>Operator: Show "Ready for Handoff"
    Note over Operator: Complete runtime-backed investigation
```

---

## Comparison: Evidence Postures

```mermaid
graph LR
    subgraph RUNTIME["🟢 RUNTIME-BACKED"]
        R1["REPLICA succeeded"]
        R2["Docker metrics captured"]
        R3["FORGE confidence: +30%"]
        R1 --> R2 --> R3
    end
    
    subgraph INFERENCE["🟡 INFERENCE-FIRST"]
        I1["REPLICA unavailable"]
        I2["PRISM diagnosis only"]
        I3["FORGE confidence: baseline"]
        I1 --> I2 --> I3
    end
    
    subgraph UNSUPPORTED["❌ UNSUPPORTED"]
        U1["Incident doesn't match"]
        U2["Get rejected with error"]
        U3["Or fallback to similar family"]
        U1 --> U2 --> U3
    end
    
    style R3 fill:#50C878
    style I3 fill:#FFB347
    style U3 fill:#E74C3C
```

---

## Summary: When Each Posture Occurs

| Posture | When | Examples | Confidence |
|---------|------|----------|-----------|
| 🟢 Runtime-backed | INC001, INC002, INC003 classified + Docker relay enabled | Timeout cascade, pool exhaustion | 90-95% |
| 🟡 Inference-first | INC004-INC007 classified, or docker relay disabled | Cache explosion, queue backlog, auth slowdown | 65-85% |
| ❌ Unsupported | INC008-INC011 best match | CDN, ML model, geographic routing | Rejected or fallback |
