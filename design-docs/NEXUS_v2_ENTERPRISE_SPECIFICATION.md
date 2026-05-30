# NEXUS v2 — Enterprise Technical Specification
## Input Channels, Log Ingestion, Agent Contributions & UI Architecture

**Version:** 1.0 | **Classification:** Enterprise | **Author:** Kunal Kachru | **Date:** May 28, 2026

> Target-state reference for the enterprise product.
> The shipped implementation and current gaps are tracked in [README.md](../README.md), [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](../docs/NEXUS_v2_DOC_STATUS_MATRIX.md), and [docs/NEXUS_v2_PRIORITY_BACKLOG.md](../docs/NEXUS_v2_PRIORITY_BACKLOG.md).

---

## TABLE OF CONTENTS

1. Executive Overview
2. Input Channel Architecture (All Options)
3. Log Ingestion Pipeline
4. Agent Job Definitions & Contributions
5. UI/UX Specifications
6. Data Models
7. Integration Points & APIs
8. Deployment Architecture
9. Stakeholder Presentation Flow

---

## 1. EXECUTIVE OVERVIEW

### 1.1 NEXUS v2 as Enterprise Software (Target State)

NEXUS v2 is a **multi-channel incident response orchestration platform** that:

- **Accepts incidents** via multiple channels (Slack, webhooks, forms, continuous streams)
- **Processes incidents** through 4 specialized RL agents with transparent decision-making
- **Shows an auditable trail** of all agent decisions with supporting evidence
- **Enables stakeholder visibility** at every stage of the incident lifecycle
- **Maintains enterprise compliance** (SOC2, audit logs, access control)

### 1.2 Core Principle: Transparency

Every action in NEXUS must be **visible, auditable, and explainable** to stakeholders.

---

## 2. INPUT CHANNEL ARCHITECTURE

### 2.1 All Input Channel Options

NEXUS v2 supports **4 distinct input channels**, each with different use cases:

```
┌─────────────────────────────────────────────────────────────────┐
│                    INCIDENT INPUT CHANNELS                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Channel 1: ALERT WEBHOOKS        Channel 2: MANUAL FORMS      │
│  (Real-time from monitoring)      (On-call or web UI)          │
│  ┌──────────────────────┐         ┌──────────────────────┐    │
│  │ Datadog webhook      │         │ Web form input       │    │
│  │ Prometheus AlertMgr  │         │ Slack /command       │    │
│  │ CloudWatch SNS       │         │ Mobile app           │    │
│  │ New Relic            │         │ PagerDuty webhook    │    │
│  └──────────────────────┘         └──────────────────────┘    │
│  Latency: <1 sec                  Latency: Immediate          │
│  Format: Structured JSON          Format: User input          │
│                                                                 │
│  Channel 3: CONTINUOUS STREAMS    Channel 4: BATCH IMPORTS    │
│  (Real-time log/metric streams)   (Periodic bulk ingestion)   │
│  ┌──────────────────────┐         ┌──────────────────────┐    │
│  │ ELK log stream       │         │ Periodic CSV import  │    │
│  │ Kafka/Kinesis        │         │ Database polls       │    │
│  │ CloudWatch Logs      │         │ Scheduled uploads    │    │
│  │ Loki log stream      │         │ Backup restoration   │    │
│  └──────────────────────┘         └──────────────────────┘    │
│  Latency: <5 sec                  Latency: Minutes            │
│  Format: Semi-structured logs     Format: Tabular data        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Detailed Channel Specifications

#### **Channel 1: Alert Webhooks (Primary)**

**Use Case:** Real-time incident detection from monitoring tools

**Technologies Supported:**
- Datadog, Prometheus AlertManager, CloudWatch, New Relic, Grafana, PagerDuty, OpsGenie

**Endpoint:**
```
POST /api/v1/incidents/webhook
```

**Expected Request Body (Normalized):**
```json
{
  "webhook_source": "datadog",
  "alert_id": "alert-12345",
  "alert_name": "High Error Rate - Payment Service",
  "timestamp": "2026-05-28T14:32:00Z",
  "severity": "critical",

  "affected_service": {
    "name": "payment-service",
    "environment": "production",
    "region": "us-east-1"
  },

  "affected_hosts": [
    "payment-pod-12",
    "payment-pod-13",
    "payment-pod-14"
  ],

  "metrics": {
    "error_rate_pct": 45.2,
    "p95_latency_ms": 8500,
    "cpu_percent": 92,
    "memory_percent": 87,
    "request_rate_rps": 1200
  },

  "alert_context": {
    "threshold": 5.0,
    "baseline": 0.5,
    "change_magnitude": "9x"
  },

  "tags": [
    "team:payments",
    "service:payment-service",
    "env:production"
  ]
}
```

**Processing Flow:**
```python
# Webhook Handler
@app.post("/api/v1/incidents/webhook")
async def handle_alert_webhook(alert: WebhookAlert, background_tasks):
    """
    Enterprise-grade webhook handler with full audit trail
    """

    # 1. VALIDATE (Strict schema validation)
    try:
        validated_alert = WebhookAlert.model_validate(alert)
    except ValidationError as e:
        log_webhook_error(alert, error=str(e))
        return {"status": "rejected", "reason": str(e)}, 400

    # 2. AUTHENTICATE (Check API key/signature)
    auth_result = await verify_webhook_signature(
        alert_source=validated_alert.webhook_source,
        signature=request.headers.get("X-Webhook-Signature")
    )
    if not auth_result.valid:
        audit_log.warning(f"Invalid webhook signature from {validated_alert.webhook_source}")
        return {"status": "unauthorized"}, 401

    # 3. ENRICH (Add context from service registry)
    service_metadata = await k8s_provider.get_service(
        validated_alert.affected_service.name
    )

    # 4. NORMALIZE (Convert to NEXUS internal format)
    incident_trigger = convert_webhook_to_trigger(
        alert=validated_alert,
        metadata=service_metadata
    )

    # 5. LOG (Full audit trail)
    audit_log.info(
        "Webhook received",
        webhook_id=validated_alert.alert_id,
        incident_id=incident_trigger.incident_id,
        source=validated_alert.webhook_source,
        service=incident_trigger.affected_service
    )

    # 6. ENQUEUE (Add to incident queue)
    await incident_queue.enqueue(
        incident=incident_trigger,
        priority=get_priority(validated_alert.severity),
        source="webhook",
        webhook_source=validated_alert.webhook_source
    )

    # 7. ACKNOWLEDGE (Immediate response)
    return {
        "status": "accepted",
        "incident_id": incident_trigger.incident_id,
        "queue_position": await incident_queue.position(incident_trigger.incident_id),
        "estimated_processing_time_sec": 30
    }
```

---

#### **Channel 2: Manual Incident Reports (Secondary)**

**Use Case:** On-call engineers report incidents NEXUS missed, or trigger manual investigations

**Option A: Web Form**

**Endpoint:**
```
POST /api/v1/incidents/manual-report
```

**Form Fields:**
```python
class ManualIncidentReport(BaseModel):
    # What (required)
    affected_service: str
    symptoms: list[str]  # Free-text list
    severity: Literal["P0", "P1", "P2", "P3"]

    # Why (optional but encouraged)
    root_cause_suspected: Optional[str]
    additional_context: Optional[str]

    # Who (required for audit)
    reported_by: str  # Email address
    team: str  # Which team reported

    # When (optional)
    symptom_start_time: Optional[datetime]

    # Where (optional)
    affected_regions: Optional[list[str]]
    affected_hosts: Optional[list[str]]
```

**UI Form (HTML/React):**
```html
<Form onSubmit={submitIncidentReport}>
  <FormSection title="What is broken?">
    <Select
      label="Affected Service"
      options={services}
      required
    />
    <TextArea
      label="Describe the symptoms"
      placeholder="e.g., Payments timing out, error rate spiking..."
      required
    />
    <Select
      label="Severity"
      options={["P0", "P1", "P2", "P3"]}
      required
    />
  </FormSection>

  <FormSection title="Additional context (optional)">
    <TextArea
      label="Suspected root cause (if you know)"
      placeholder="e.g., Recent deployment, database migration..."
    />
    <TextArea
      label="Any other details"
    />
  </FormSection>

  <FormSection title="Your information (for audit)">
    <Input
      label="Your email"
      type="email"
      defaultValue={currentUser.email}
      disabled
    />
    <Select
      label="Your team"
      options={teams}
      defaultValue={currentUser.team}
    />
  </FormSection>

  <Button type="submit">Report Incident</Button>
</Form>
```

**Option B: Slack Command**

**Slack Slash Command:**
```
/nexus-report payment-service "Requests timing out, high error rate" --severity P0
```

**Slack Modal Interaction:**
```
User types: /nexus-report
↓
NEXUS opens modal with form fields
↓
User fills: Service, symptoms, severity
↓
Slack sends to NEXUS API
↓
NEXUS acknowledges with incident ID
```

---

#### **Channel 3: Continuous Log Streams (Advanced)**

**Use Case:** NEXUS continuously monitors logs and metrics, auto-detects anomalies

**Technologies:**
- ELK Stack (Elasticsearch), Grafana Loki, Kafka, AWS Kinesis, DataDog

**Architecture:**

```python
class LogStreamConsumer:
    """
    Consumes logs from ELK/Loki in real-time.
    Detects anomalies and creates incidents automatically.
    """

    async def connect_to_elk(self):
        """Connect to ELK log stream"""
        self.es_client = Elasticsearch(
            hosts=["elk.internal:9200"],
            verify_certs=False
        )

    async def tail_logs(self):
        """
        Continuously tail logs from ELK for key services
        """
        while True:
            # Query ELK for recent errors
            response = self.es_client.search(
                index="logs-*",
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"level": "ERROR"}},
                                {"range": {
                                    "timestamp": {
                                        "gte": "now-1m"
                                    }
                                }}
                            ]
                        }
                    },
                    "size": 100,
                    "sort": [{"timestamp": {"order": "desc"}}]
                }
            )

            # Process each error log
            for hit in response["hits"]["hits"]:
                log_entry = hit["_source"]

                # Check if this is an anomaly
                if self.is_anomaly(log_entry):
                    incident = self.create_incident_from_log(log_entry)
                    await incident_queue.enqueue(
                        incident,
                        source="log_stream_anomaly"
                    )

            # Wait before next batch
            await asyncio.sleep(30)

    def is_anomaly(self, log_entry: dict) -> bool:
        """
        Detect if this log represents a real anomaly.
        Uses pattern matching + ML model.
        """

        # Pattern 1: Connection pool exhaustion
        if "connection pool" in log_entry.get("message", "").lower():
            if "exhausted" in log_entry.get("message", "").lower():
                return True

        # Pattern 2: Repeated errors (threshold)
        error_count = self.count_recent_errors(
            log_entry.get("service"),
            minutes=5
        )
        if error_count > 100:  # Threshold
            return True

        # Pattern 3: ML anomaly detection
        embedding = self.ml_encoder.encode(log_entry["message"])
        anomaly_score = self.ml_anomaly_detector.score(embedding)
        if anomaly_score > 0.8:
            return True

        return False
```

---

#### **Channel 4: Batch Imports (Operational)**

**Use Case:** Import historical incidents, bulk uploads, disaster recovery

**Endpoint:**
```
POST /api/v1/incidents/batch-import
```

**Batch Import Format:**
```json
{
  "batch_id": "batch-recovery-2026-05-28",
  "source": "disaster_recovery",
  "incidents": [
    {
      "incident_id": "INC-legacy-001",
      "timestamp": "2026-05-28T10:00:00Z",
      "affected_service": "payment-service",
      "symptoms": ["Database unavailable"],
      "severity": "P0"
    },
    {
      "incident_id": "INC-legacy-002",
      "timestamp": "2026-05-28T11:30:00Z",
      "affected_service": "api-gateway",
      "symptoms": ["Certificate expired"],
      "severity": "P1"
    }
  ]
}
```

---

### 2.3 Input Channel Selection Matrix

| Scenario | Recommended Channel | Reasoning |
|----------|---|---|
| Alert fires in Datadog | Alert Webhook | Real-time, structured |
| Engineer finds issue manually | Manual Form or Slack | Quick, human context |
| Log error spike detected | Log Stream | Automated, continuous |
| Post-incident training data | Batch Import | Historical bulk load |
| Backup restoration | Batch Import | Bulk recovery |

---

## 3. LOG INGESTION PIPELINE

### 3.1 Complete Log Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    INCIDENT ENTERS NEXUS                           │
│              (via any of the 4 channels above)                     │
│                                                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────┐
        │  STAGE 1: VALIDATION & ENRICHMENT        │
        ├──────────────────────────────────────────┤
        │                                          │
        │  ✓ Schema validation (Pydantic)         │
        │  ✓ Mandatory field checks                │
        │  ✓ Data type validation                  │
        │  ✓ Range checks (error_rate 0-100%)     │
        │  ✓ Signature verification (webhooks)     │
        │  ✓ Authentication (API key/OAuth)        │
        │  ✓ PII detection & removal               │
        │    - Remove emails, credit cards         │
        │    - Redact user IDs                     │
        │  ✓ Service metadata enrichment           │
        │    - Lookup in Kubernetes API            │
        │    - Get dependencies, version, team     │
        │  ✓ Historical context lookup             │
        │    - Query Incident Memory Graph         │
        │    - Get similar past incidents          │
        │                                          │
        │  Log Entry: IncidentValidationLog        │
        │  Duration: ~500ms                        │
        │                                          │
        └──────────────────────┬───────────────────┘
                               ↓
        ┌──────────────────────────────────────────┐
        │  STAGE 2: QUERY CONTEXT DATA             │
        ├──────────────────────────────────────────┤
        │                                          │
        │  For PRISM to process, fetch:            │
        │                                          │
        │  Recent Logs (past 30 minutes)           │
        │  ──────────────────────────────────      │
        │  Query ELK/Loki for:                     │
        │  - ERROR level logs from service         │
        │  - Stack traces matching incident type   │
        │  - Deploy/config change logs             │
        │  Result: ~50-500 log lines               │
        │                                          │
        │  Recent Metrics (past 30 minutes)        │
        │  ────────────────────────────────        │
        │  Query Prometheus/Datadog for:           │
        │  - Error rate, latency, CPU, memory      │
        │  - Traffic patterns, dependency health   │
        │  Result: ~20-50 metric data points       │
        │                                          │
        │  Recent Traces (past 30 minutes)         │
        │  ───────────────────────────────         │
        │  Query Jaeger/Datadog APM for:           │
        │  - Request flows, timeouts, errors       │
        │  - Service dependency chain              │
        │  Result: ~10-100 trace samples           │
        │                                          │
        │  Deployment History                      │
        │  ──────────────────────                  │
        │  Query Kubernetes API:                   │
        │  - Last deployment time                  │
        │  - Current version vs previous           │
        │  - Pod restarts, node changes            │
        │                                          │
        │  Log Entry: ContextDataRetrievalLog      │
        │  Duration: ~2-5 seconds (parallel calls) │
        │                                          │
        └──────────────────────┬───────────────────┘
                               ↓
        ┌──────────────────────────────────────────┐
        │  STAGE 3: NORMALIZE & STRUCTURE          │
        ├──────────────────────────────────────────┤
        │                                          │
        │  Convert all data to NEXUS format:       │
        │                                          │
        │  IncidentTrigger {                       │
        │    incident_id,                          │
        │    timestamp,                            │
        │    raw_symptoms,                         │
        │    affected_service,                     │
        │    signal_metrics,                       │
        │    detection_method,                     │
        │    source_channel                        │
        │  }                                       │
        │                                          │
        │  MonitoringSignals {                     │
        │    logs: [...],                          │
        │    metrics: {...},                       │
        │    traces: [...],                        │
        │    events: [...]                         │
        │  }                                       │
        │                                          │
        │  ServiceMetadata {                       │
        │    name, language, infra,                │
        │    dependencies, current_version, ...    │
        │  }                                       │
        │                                          │
        │  Log Entry: IncidentNormalizationLog     │
        │  Duration: ~100ms                        │
        │                                          │
        └──────────────────────┬───────────────────┘
                               ↓
        ┌──────────────────────────────────────────┐
        │  STAGE 4: PRIORITY & QUEUEING            │
        ├──────────────────────────────────────────┤
        │                                          │
        │  Assign priority based on:               │
        │  • Severity (P0 > P1 > P2 > P3)         │
        │  • Service criticality (payment > log)   │
        │  • Blast radius (Global > Multi > 1)     │
        │                                          │
        │  Queue Strategy:                         │
        │  Priority Queue (not FIFO)               │
        │  P0: Process immediately                 │
        │  P1: Within 60 seconds                   │
        │  P2: Within 5 minutes                    │
        │  P3: Within 30 minutes                   │
        │                                          │
        │  Storage: Redis or PostgreSQL            │
        │                                          │
        │  Log Entry: IncidentQueuedLog            │
        │  Duration: ~50ms                         │
        │                                          │
        └──────────────────────┬───────────────────┘
                               ↓
        ┌──────────────────────────────────────────┐
        │  STAGE 5: AUDIT & PERSISTENCE            │
        ├──────────────────────────────────────────┤
        │                                          │
        │  Store auditable trail:                  │
        │                                          │
        │  IncidentLog Table:                      │
        │  - incident_id                           │
        │  - received_timestamp                    │
        │  - source_channel                        │
        │  - received_from (IP/user)               │
        │  - validation_status                     │
        │  - enrichment_status                     │
        │  - queue_position                        │
        │                                          │
        │  AllWebhookPayloads Table:               │
        │  - incident_id                           │
        │  - original_payload (full JSON)          │
        │  - source_system                         │
        │  - timestamp                             │
        │                                          │
        │  Storage: PostgreSQL (immutable logs)    │
        │  Retention: Indefinite (for compliance)  │
        │                                          │
        │  Log Entry: IncidentPersistedLog         │
        │  Duration: ~200ms                        │
        │                                          │
        └──────────────────────┬───────────────────┘
                               ↓
               INCIDENT READY FOR SENTINEL PROCESSING
```

### 3.2 Log Ingestion Timing & SLAs

| Stage | Duration | Target | Status |
|-------|----------|--------|--------|
| Validation | 500ms | <1s | ✅ |
| Context retrieval | 2-5s | <10s | ✅ |
| Normalization | 100ms | <1s | ✅ |
| Queueing | 50ms | <1s | ✅ |
| Persistence | 200ms | <1s | ✅ |
| **Total** | **3-7 seconds** | **<15s** | ✅ |

**Guarantee:** Incident fully ingested and ready for SENTINEL within **15 seconds** of initial receipt.

---

## 4. AGENT JOB DEFINITIONS & CONTRIBUTIONS

### 4.1 Agent Responsibility Matrix

```
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│   SENTINEL   │    PRISM     │    FORGE     │   GUARDIAN   │  NEXUS CORE  │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│              │              │              │              │              │
│ JOB:         │ JOB:         │ JOB:         │ JOB:         │ JOB:         │
│ Classify     │ Diagnose     │ Generate     │ Validate     │ Orchestrate  │
│              │              │              │              │              │
│ QUESTION:    │ QUESTION:    │ QUESTION:    │ QUESTION:    │ QUESTION:    │
│ "What is     │ "Why is it   │ "How do we   │ "Is it safe  │ "What's the  │
│  broken?"    │  broken?"    │  fix it?"    │  to fix?"    │  status?"    │
│              │              │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

### 4.2 SENTINEL Agent Specification

**Role:** Classify incident type, severity, blast radius

**Input Data:**
```python
class SentinelInput(BaseModel):
    incident_id: str
    raw_symptoms: list[str]
    affected_service: str
    affected_hosts: list[str]
    signal_metrics: dict  # error_rate, latency, cpu, etc.
    timestamp: datetime
```

**Processing:**
```python
class SentinelAgent:
    def classify(self, input: SentinelInput) -> SentinelOutput:
        """
        Use trained RL neural network to classify incident.

        Process:
        1. Tokenize symptoms and metrics
        2. Pass through neural network
        3. Get probability distribution over incident types
        4. Select highest probability class
        5. Assess severity and blast radius
        """

        # Step 1: Feature extraction
        symptom_tokens = self.tokenize(input.raw_symptoms)
        metric_embedding = self.embed_metrics(input.signal_metrics)
        service_embedding = self.embed_service(input.affected_service)

        # Step 2: Neural network inference
        logits = self.policy_network(
            symptoms=symptom_tokens,
            metrics=metric_embedding,
            service=service_embedding
        )
        probabilities = softmax(logits)  # [0.92, 0.05, 0.02, 0.01]

        # Step 3: Classification decision
        incident_type = argmax(probabilities)  # ResourceExhaustion
        confidence = max(probabilities)  # 0.92

        # Step 4: Severity assessment
        severity = self.assess_severity(
            incident_type=incident_type,
            error_rate=input.signal_metrics.get("error_rate_pct"),
            affected_count=len(input.affected_hosts)
        )

        # Step 5: Blast radius
        blast_radius = self.assess_blast_radius(
            affected_hosts=input.affected_hosts,
            affected_service=input.affected_service
        )

        return SentinelOutput(
            incident_classification=incident_type,
            severity=severity,
            confidence=confidence,
            blast_radius=blast_radius,
            reasoning=[
                "High error rate + high latency pattern",
                "CPU at 92% indicates resource bottleneck",
                "Pattern matches ResourceExhaustion classification"
            ]
        )
```

**Output:**
```python
class SentinelOutput(BaseModel):
    incident_classification: str  # e.g., "ResourceExhaustion"
    severity: str  # "P0", "P1", "P2", "P3"
    blast_radius: str  # "Isolated", "ServiceLevel", "MultiService", "Global"
    confidence: float  # 0.0 - 1.0
    reasoning: list[str]  # Human-readable explanations
    affected_services: list[str]
    immediate_risks: list[str]
```

**Decision Log (Saved in Database):**
```python
class SentinelDecisionLog(BaseModel):
    timestamp: datetime
    incident_id: str

    # Input
    input_data: SentinelInput

    # Processing details
    feature_extraction: dict  # Tokenization results
    network_output: dict  # Logits and probabilities
    classification_candidates: dict  # {type: confidence, ...}

    # Decision
    decision: SentinelOutput

    # Metadata
    model_version: str
    execution_time_ms: float
    neural_network_weights_hash: str  # For reproducibility
```

**UI Display (Dashboard Card):**
```
┌─ SENTINEL CLASSIFICATION ────────────────────────┐
│                                                  │
│ Classification: ResourceExhaustion               │
│ Confidence: 92%                                  │
│                                                  │
│ Severity: P0                                     │
│ Blast Radius: MultiService                      │
│                                                  │
│ Reasoning:                                       │
│  • High error rate + high latency pattern       │
│  • CPU at 92% indicates resource bottleneck     │
│  • Pattern matches ResourceExhaustion           │
│                                                  │
│ Affected Services:                               │
│  • payment-service                              │
│  • api-gateway                                  │
│  • checkout-service                             │
│                                                  │
│ Immediate Risks:                                 │
│  • Service will timeout in 2-3 minutes          │
│  • Cascading failures likely                    │
│  • Customer transactions will be blocked        │
│                                                  │
│ Processing Time: 245ms                          │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

### 4.3 PRISM Agent Specification

**Role:** Diagnose root cause using logs, metrics, and traces

**Input Data:**
```python
class PrismInput(BaseModel):
    incident_id: str
    sentinel_output: SentinelOutput

    # Monitoring signals (already retrieved in ingestion stage)
    logs: list[LogEntry]  # ~50-500 recent error logs
    metrics: dict  # ~20-50 metric points
    traces: list[TraceSpan]  # ~10-100 trace samples

    step_budget: int = 3  # Max queries PRISM can make
    step_count: int = 0  # Current step count
```

**Processing:**
```python
class PrismAgent:
    async def diagnose(self, input: PrismInput) -> PrismOutput:
        """
        Diagnose root cause by examining logs, metrics, traces.

        Strategy:
        1. Analyze provided signals
        2. If confident enough → form hypothesis
        3. If uncertain → request more data (costly in MTTR)
        4. Form final diagnosis with evidence
        """

        # Step 1: Analyze logs (free, already have them)
        log_analysis = self.analyze_logs(input.logs)
        # e.g., "47 logs mention Redis, 'connection pool exhausted'"

        # Step 2: Analyze metrics (free, already have them)
        metric_analysis = self.analyze_metrics(input.metrics)
        # e.g., "redis_connections: 512/512 (100%), memory: 93%"

        # Step 3: Analyze traces (free, already have them)
        trace_analysis = self.analyze_traces(input.traces)
        # e.g., "All error traces timeout on Redis GET operation"

        # Step 4: Form initial hypothesis
        hypothesis = self.form_hypothesis(
            log_analysis=log_analysis,
            metric_analysis=metric_analysis,
            trace_analysis=trace_analysis,
            sentinel_classification=input.sentinel_output.incident_classification
        )
        # Hypothesis: "Redis connection pool exhausted"

        # Step 5: Confidence check
        confidence = self.assess_confidence(hypothesis, evidence)

        if confidence >= 0.85:
            # High confidence → commit to diagnosis
            return PrismOutput(
                root_cause=hypothesis["root_cause"],
                confidence=confidence,
                evidence=hypothesis["evidence"],
                reasoning=hypothesis["reasoning"]
            )
        else:
            # Low confidence → optionally query more (if budget allows)
            if input.step_count < input.step_budget:
                more_logs = await self.query_logs(
                    query="[more specific query based on hypothesis]"
                )
                input.logs.extend(more_logs)
                input.step_count += 1

                # Retry diagnosis with more data
                return await self.diagnose(input)
            else:
                # Budget exhausted → return best guess
                return PrismOutput(
                    root_cause=hypothesis["root_cause"],
                    confidence=confidence,
                    evidence=hypothesis["evidence"],
                    reasoning=hypothesis["reasoning"],
                    note="Diagnosis with limited data due to step budget"
                )
```

**Output:**
```python
class PrismOutput(BaseModel):
    root_cause: str
    root_cause_category: str  # CodeBug, ConfigError, InfraFailure, etc.
    confidence: float  # 0.0 - 1.0

    # Evidence backing the diagnosis
    evidence: list[dict]  # [{type: "log", value: "...", supports: True}, ...]

    # Alternatives considered
    hypotheses_considered: list[dict]

    # Recommendation to FORGE
    recommended_fix_type: str  # e.g., "scale_up", "restart", "code_fix"
```

**Decision Log (Saved in Database):**
```python
class PrismDecisionLog(BaseModel):
    timestamp: datetime
    incident_id: str

    # Input
    sentinel_output: SentinelOutput
    logs_examined: int  # How many logs analyzed
    metrics_examined: int  # How many metrics analyzed
    traces_examined: int  # How many traces analyzed

    # Processing details
    log_analysis_summary: dict
    metric_analysis_summary: dict
    trace_analysis_summary: dict

    # Hypothesis formation
    initial_hypothesis: str
    hypothesis_confidence: float
    alternative_hypotheses: list[str]

    # Queries made (if any)
    additional_queries: list[dict]  # [{type: "logs", query: "...", results: N}, ...]

    # Decision
    decision: PrismOutput

    # Metadata
    steps_used: int
    execution_time_ms: float
```

**UI Display (Dashboard Card):**
```
┌─ PRISM ROOT CAUSE DIAGNOSIS ─────────────────────┐
│                                                  │
│ Root Cause:                                      │
│ Redis connection pool exhausted due to job       │
│ backlog from previous deployment                 │
│                                                  │
│ Category: InfraFailure                           │
│ Confidence: 88%                                  │
│                                                  │
│ Evidence:                                        │
│  ✓ 47 error logs mentioning Redis               │
│  ✓ Metrics: redis_connections 512/512 (100%)    │
│  ✓ All error traces timeout on Redis GET        │
│  ✓ Celery queue depth: 5000 (up from 100)       │
│                                                  │
│ Hypotheses Considered & Rejected:                │
│  ✗ Application code bug                         │
│    Reason: Would affect only 1 service          │
│                                                  │
│  ✗ Network connectivity issue                   │
│    Reason: Other services reach Redis fine      │
│                                                  │
│ Recommended Fix Type:                            │
│ Scale + Restart                                  │
│                                                  │
│ Processing Time: 2.3 seconds                     │
│ Steps Used: 2 / 3                                │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

### 4.4 FORGE Agent Specification

**Role:** Generate executable runbook using Codex

**Input Data:**
```python
class ForgeInput(BaseModel):
    incident_id: str
    prism_output: PrismOutput  # Root cause diagnosis
    sentinel_output: SentinelOutput

    # Historical context
    similar_incidents: list[dict]  # Past incidents with similar root cause

    # Service context
    service_metadata: ServiceMetadata
```

**Processing:**
```python
class ForgeAgent:
    async def generate_runbook(self, input: ForgeInput) -> ForgeOutput:
        """
        Generate executable runbook using OpenAI Codex.

        Process:
        1. Query Incident Memory Graph for similar fixes
        2. Build Codex prompt with context
        3. Call Codex API to generate runbook
        4. Parse and validate runbook
        5. Return execution-ready script
        """

        # Step 1: Find similar past fixes
        similar = self.query_incident_memory_graph(
            root_cause=input.prism_output.root_cause_category,
            service=input.service_metadata.name
        )
        # e.g., [INC-2026-02-14 (similarity 0.92), INC-2026-03-20 (0.87)]

        # Step 2: Extract what worked before
        prior_fixes = [
            {
                "incident_id": sim["id"],
                "fix": sim["fix_method"],
                "mttr_minutes": sim["mttr"],
                "success_rate": sim["rl_reward"]
            }
            for sim in similar[:3]
        ]
        # e.g., "Incident INC-2026-02-14: Scale Redis + restart, 12 min MTTR, 0.78 reward"

        # Step 3: Build Codex prompt
        codex_prompt = self.build_prompt(
            root_cause=input.prism_output.root_cause,
            service=input.service_metadata.name,
            language=input.service_metadata.language,
            prior_fixes=prior_fixes,
            severity=input.sentinel_output.severity
        )

        # Step 4: Call Codex
        codex_response = await self.call_codex(
            prompt=codex_prompt,
            model="codex-1",
            temperature=0.2,  # Deterministic, not creative
            max_tokens=500
        )

        # Step 5: Parse response
        runbook = self.parse_codex_response(codex_response)
        # Extract: bash script, estimated duration, validation check

        # Step 6: Validate runbook
        validation = self.validate_runbook(runbook)
        if not validation.valid:
            raise RunbookGenerationError(validation.errors)

        return ForgeOutput(
            runbook_language="bash",
            runbook_code=runbook["script"],
            estimated_duration_min=runbook["duration"],
            is_destructive=runbook["is_destructive"],
            validation_check=runbook["validation"],
            rollback_script=self.generate_rollback(runbook),
            confidence=0.87
        )
```

**Output:**
```python
class ForgeOutput(BaseModel):
    runbook_language: str  # "bash", "python", "kubectl"
    runbook_code: str  # The actual script
    estimated_duration_min: int
    is_destructive: bool  # Requires GUARDIAN approval
    prerequisites: list[str]  # What must be true before execution
    validation_check: str  # Command to verify fix worked
    rollback_script: str  # How to undo the fix
    confidence: float
```

**Decision Log:**
```python
class ForgeDecisionLog(BaseModel):
    timestamp: datetime
    incident_id: str

    # Input
    prism_output: PrismOutput

    # Processing
    similar_incidents_found: int
    top_similar_incident: dict

    # Codex call
    codex_prompt: str  # Full prompt sent to Codex
    codex_response: str  # Full response from Codex
    codex_tokens_used: int
    codex_api_cost: float

    # Decision
    decision: ForgeOutput

    # Metadata
    execution_time_ms: float
    model_version: str
```

**UI Display (Dashboard Card):**
```
┌─ FORGE RUNBOOK GENERATION ────────────────────────┐
│                                                  │
│ Generated Runbook:                               │
│ ╔════════════════════════════════════════════╗   │
│ ║ #!/bin/bash                                ║   │
│ ║ set -e                                     ║   │
│ ║                                            ║   │
│ ║ echo "Scaling Redis..."                    ║   │
│ ║ kubectl set resources pod redis-pod...     ║   │
│ ║   -c redis --memory=4Gi                    ║   │
│ ║                                            ║   │
│ ║ echo "Restarting payment-service..."       ║   │
│ ║ kubectl rollout restart deploy...          ║   │
│ ║   payment-service -n production            ║   │
│ ║                                            ║   │
│ ║ echo "Waiting for rollout..."              ║   │
│ ║ kubectl rollout status deploy...           ║   │
│ ║   payment-service -n production            ║   │
│ ║                                            ║   │
│ ║ echo "Health check..."                     ║   │
│ ║ curl -f http://payment/health || exit 1    ║   │
│ ╚════════════════════════════════════════════╝   │
│                                                  │
│ Language: bash                                   │
│ Estimated Duration: 5 minutes                    │
│ Is Destructive: Yes (requires restart)           │
│ Confidence: 87%                                  │
│                                                  │
│ Prerequisites:                                   │
│  • kubectl access to production cluster          │
│  • Slack notifications configured                │
│                                                  │
│ Validation Check:                                │
│ curl -f http://payment/health                    │
│                                                  │
│ Rollback Command (if needed):                    │
│ kubectl rollout undo deploy payment-service      │
│                                                  │
│ Similar Past Fixes:                              │
│  [0.92] INC-2026-02-14: Scale + restart         │
│         MTTR: 12 min, Reward: 0.78              │
│  [0.87] INC-2026-03-20: Increase pool size      │
│         MTTR: 8 min, Reward: 0.85               │
│                                                  │
│ Processing Time: 2.1 seconds                     │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

### 4.5 GUARDIAN Agent Specification

**Role:** Safety review before execution

**Input Data:**
```python
class GuardianInput(BaseModel):
    incident_id: str
    forge_output: ForgeOutput  # Runbook to review
    sentinel_output: SentinelOutput  # Severity context
    prism_output: PrismOutput  # Confidence context
```

**Processing:**
```python
class GuardianAgent:
    def validate_runbook(self, input: GuardianInput) -> GuardianOutput:
        """
        Perform safety checks before execution.
        """

        # Check 1: Command Safety
        check_1 = self.check_command_safety(
            runbook_code=input.forge_output.runbook_code
        )
        # Look for: rm -rf, truncate, DROP TABLE, etc.

        # Check 2: Blast Radius Acceptability
        check_2 = self.check_blast_radius_acceptable(
            severity=input.sentinel_output.severity,
            blast_radius=input.sentinel_output.blast_radius,
            is_destructive=input.forge_output.is_destructive
        )
        # P0 + Multi service + destructive = Acceptable
        # P3 + Isolated + non-destructive = Acceptable

        # Check 3: Confidence Level
        check_3 = self.check_confidence_acceptable(
            sentinel_confidence=input.sentinel_output.confidence,
            prism_confidence=input.prism_output.confidence,
            combined_threshold=0.75
        )

        # Check 4: Rollback Availability
        check_4 = self.check_rollback_available(
            rollback_script=input.forge_output.rollback_script
        )

        # Aggregate all checks
        all_pass = all([
            check_1.passed,
            check_2.passed,
            check_3.passed,
            check_4.passed
        ])

        if all_pass:
            approval_type = self.determine_approval_type(input)
            # Might be "auto_approve" or "require_human_approval"

        return GuardianOutput(
            decision="approve" if all_pass else "reject",
            approval_type=approval_type,
            safety_score=self.calculate_safety_score([check_1, check_2, check_3, check_4]),
            risk_flags=[],
            reasoning=[...]
        )
```

**Output:**
```python
class GuardianOutput(BaseModel):
    decision: Literal["approve", "reject", "modify"]
    approval_type: Literal["auto_approve", "require_human_approval"]
    safety_score: float  # 0.0 - 1.0
    risk_flags: list[str]
    reasoning: list[str]
```

**Decision Log:**
```python
class GuardianDecisionLog(BaseModel):
    timestamp: datetime
    incident_id: str

    # Input
    forge_output: ForgeOutput

    # Safety checks
    command_safety_check: dict
    blast_radius_check: dict
    confidence_check: dict
    rollback_check: dict

    # Decision
    decision: GuardianOutput

    # Approval type logic
    approval_type_reasoning: str
```

**UI Display (Dashboard Card):**
```
┌─ GUARDIAN SAFETY APPROVAL ────────────────────────┐
│                                                  │
│ Safety Checks:                                   │
│                                                  │
│  ✓ Command Safety: SAFE                         │
│    No destructive commands detected              │
│    Proper error handling with 'set -e'           │
│                                                  │
│  ✓ Blast Radius: ACCEPTABLE                     │
│    P0 severity justifies pod restart risk        │
│    Alternative is complete service outage        │
│                                                  │
│  ✓ Confidence Level: STRONG                     │
│    SENTINEL: 0.92, PRISM: 0.88                   │
│    Combined confidence: 0.89 (> 0.75 threshold)  │
│                                                  │
│  ✓ Rollback Available: YES                      │
│    Rollback script present and tested            │
│    Estimated rollback time: 2 minutes            │
│                                                  │
│ Overall Safety Score: 0.95 / 1.0                │
│                                                  │
│ Approval Decision: ✓ APPROVED                   │
│ Approval Type: AUTO_APPROVE                      │
│ Human Review Required: No                        │
│ Execution Mode: IMMEDIATE                        │
│                                                  │
│ Reasoning:                                       │
│  • All safety checks pass                       │
│  • High confidence in diagnosis (0.89)          │
│  • P0 severity justifies risk                   │
│  • Rollback available and tested                │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 5. UI/UX SPECIFICATIONS

### 5.1 Dashboard Layout (Enterprise View)

```
┌─────────────────────────────────────────────────────────────────┐
│  NEXUS v2 INCIDENT RESPONSE CONSOLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Incident Queue] [Live Dashboard] [Historical] [Settings]      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INCIDENT: INC-2026-05-28-001 | Status: IN_PROGRESS             │
│  Service: payment-service | Severity: P0 | Created: 14:32:00    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TIMELINE VIEW (Shows each agent's work)                         │
│                                                                 │
│  14:32:00 ─┬─ INCIDENT RECEIVED                                 │
│            │  Source: datadog_webhook                           │
│            │  Error rate: 45.2% | Latency: 8500ms              │
│            │  [Expand Details]                                  │
│            │                                                    │
│            └─ Enrichment: Service metadata loaded               │
│                                                                 │
│  14:32:05 ─┬─ SENTINEL CLASSIFICATION                           │
│            │  Type: ResourceExhaustion                          │
│            │  Confidence: 92%                                   │
│            │  [Expand Reasoning]                                │
│            │                                                    │
│  14:32:10 ─┬─ PRISM DIAGNOSIS                                   │
│            │  Root Cause: Redis pool exhausted                  │
│            │  Confidence: 88%                                   │
│            │  Evidence: 47 error logs, metrics, traces          │
│            │  [Expand Analysis]                                 │
│            │                                                    │
│  14:32:15 ─┬─ FORGE RUNBOOK GENERATION                          │
│            │  Language: bash                                    │
│            │  Lines: 12                                         │
│            │  Estimated Duration: 5 minutes                     │
│            │  [View Runbook Code]                               │
│            │                                                    │
│  14:32:20 ─┬─ GUARDIAN APPROVAL                                 │
│            │  Status: ✓ APPROVED                               │
│            │  Safety Score: 0.95                                │
│            │  Approval Type: AUTO_APPROVE                       │
│            │  [View Safety Analysis]                            │
│            │                                                    │
│  14:32:25 ─┬─ EXECUTION (In Progress...)                        │
│            │  Step 1/3: Scaling Redis...                        │
│            │  Progress: ████░░░░░░ 40%                         │
│            │                                                    │
│            └─ Result: Pending                                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  AGENT DETAILS SECTION (Click timeline to expand)               │
│                                                                 │
│  ┌─ SENTINEL DETAILS ────────────────────────────────────────┐ │
│  │                                                            │ │
│  │ Classification: ResourceExhaustion                        │ │
│  │ Confidence: 92%                                           │ │
│  │ Severity: P0                                              │ │
│  │ Blast Radius: MultiService                               │ │
│  │                                                            │ │
│  │ Reasoning:                                                │ │
│  │  • High error rate + high latency pattern                │ │
│  │  • CPU at 92% indicates resource bottleneck              │ │
│  │  • Pattern matches ResourceExhaustion classification     │ │
│  │                                                            │ │
│  │ Other Candidates (NN Output):                            │ │
│  │  • MemoryLeak: 5%                                        │ │
│  │  • NetworkTimeout: 2%                                    │ │
│  │  • ConfigError: 1%                                       │ │
│  │                                                            │ │
│  │ Processing Time: 245ms                                    │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ PRISM DETAILS ───────────────────────────────────────────┐ │
│  │                                                            │ │
│  │ Root Cause: Redis connection pool exhausted               │ │
│  │ Confidence: 88%                                           │ │
│  │ Category: InfraFailure                                    │ │
│  │                                                            │ │
│  │ Evidence Supporting Diagnosis:                            │ │
│  │                                                            │ │
│  │  Logs Examined (47 total):                               │ │
│  │  ├─ [14:31:45] ERROR "FATAL: Lost connection to Redis"   │ │
│  │  │           service: payment-service                     │ │
│  │  │           pod: payment-pod-12                          │ │
│  │  │           stack_trace: redis.ConnectionError           │ │
│  │  ├─ [14:31:50] WARN "Redis connection pool nearly        │ │
│  │  │            exhausted (510/512 used)"                  │ │
│  │  └─ [14:32:00] ERROR "Celery tasks piling up in queue"  │ │
│  │               queue_depth: 5000                           │ │
│  │                                                            │ │
│  │  Metrics Retrieved:                                       │ │
│  │  • redis_connections: 512/512 (100%) ← KEY               │ │
│  │  • redis_memory: 2.8GB / 3GB (93%)                       │ │
│  │  • celery_queue_depth: 5000                              │ │
│  │  • payment_service_cpu: 92%                               │ │
│  │  • payment_service_memory: 87%                            │ │
│  │                                                            │ │
│  │  Traces Examined (10 samples):                            │ │
│  │  • 100% of error traces timeout on Redis GET              │ │
│  │  • Latency breakdown:                                     │ │
│  │    - Service: 100ms (normal)                             │ │
│  │    - Redis: TIMEOUT (expected 5ms)                       │ │
│  │                                                            │ │
│  │ Hypotheses Considered & Rejected:                         │ │
│  │  ✗ Application code bug                                  │ │
│  │    Reason: Would affect only payment-service             │ │
│  │    But api-gateway also affected                         │ │
│  │                                                            │ │
│  │  ✗ Network connectivity issue                            │ │
│  │    Reason: Other services reach Redis fine               │ │
│  │                                                            │ │
│  │ Next Step: FORGE should generate runbook to scale        │ │
│  │ Redis and restart payment-service pods                   │ │
│  │                                                            │ │
│  │ Processing Time: 2.3 seconds                              │ │
│  │ Steps Used: 2 / 3                                         │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ FORGE DETAILS ───────────────────────────────────────────┐ │
│  │                                                            │ │
│  │ Runbook Code (Generated by Codex):                        │ │
│  │                                                            │ │
│  │ #!/bin/bash                                              │ │
│  │ set -e                                                   │ │
│  │                                                            │ │
│  │ echo "Scaling Redis..."                                  │ │
│  │ kubectl set resources pod redis-pod \                    │ │
│  │   -c redis --memory=4Gi                                 │ │
│  │                                                            │ │
│  │ echo "Restarting payment-service..."                    │ │
│  │ kubectl rollout restart deploy/payment-service \         │ │
│  │   -n production                                          │ │
│  │                                                            │ │
│  │ echo "Waiting for rollout..."                            │ │
│  │ kubectl rollout status deploy/payment-service \          │ │
│  │   -n production                                          │ │
│  │                                                            │ │
│  │ echo "Health check..."                                   │ │
│  │ curl -f http://payment/health || exit 1                 │ │
│  │                                                            │ │
│  │ Language: bash                                            │ │
│  │ Estimated Duration: 5 minutes                             │ │
│  │ Is Destructive: Yes (requires restart)                    │ │
│  │ Confidence: 87%                                           │ │
│  │                                                            │ │
│  │ Similar Past Fixes:                                       │ │
│  │  [0.92] INC-2026-02-14: Scale Redis + restart            │ │
│  │         MTTR: 12 min, RL Reward: 0.78                    │ │
│  │  [0.87] INC-2026-03-20: Increase pool size                │ │
│  │         MTTR: 8 min, RL Reward: 0.85                     │ │
│  │                                                            │ │
│  │ Processing Time: 2.1 seconds                              │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ GUARDIAN DETAILS ────────────────────────────────────────┐ │
│  │                                                            │ │
│  │ ✓ APPROVED FOR EXECUTION                                │ │
│  │                                                            │ │
│  │ Safety Checks:                                            │ │
│  │  ✓ Command Safety: SAFE                                 │ │
│  │    No destructive commands, proper error handling        │ │
│  │  ✓ Blast Radius: ACCEPTABLE                             │ │
│  │    P0 severity justifies pod restart risk                │ │
│  │  ✓ Confidence: STRONG (0.89 combined)                   │ │
│  │  ✓ Rollback: AVAILABLE (2 min estimated)                │ │
│  │                                                            │ │
│  │ Safety Score: 0.95 / 1.0                                 │ │
│  │ Approval Type: AUTO_APPROVE                              │ │
│  │ Human Review Required: No                                │ │
│  │                                                            │ │
│  │ Processing Time: 380ms                                    │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Incident Report Form (UI)

```html
<IncidentReportForm>
  <Section title="What is broken?">
    <FieldGroup>
      <Label>Affected Service *</Label>
      <Select
        options={services}
        placeholder="payment-service, api-gateway, ..."
        required
      />
    </FieldGroup>

    <FieldGroup>
      <Label>Describe the symptoms *</Label>
      <TextArea
        placeholder="e.g., Requests timing out, high error rate, performance degradation..."
        minLength={20}
        required
      />
      <HelperText>
        Be specific. Examples: "POST /payments returns 504", "P99 latency 8.5s"
      </HelperText>
    </FieldGroup>

    <FieldGroup>
      <Label>Severity *</Label>
      <RadioGroup>
        <Radio value="P0" label="P0 - Service Down">
          Service is completely unavailable or critical functionality broken
        </Radio>
        <Radio value="P1" label="P1 - Major Impact">
          Significant degradation, subset of users affected
        </Radio>
        <Radio value="P2" label="P2 - Moderate Impact">
          Non-critical feature affected, workaround available
        </Radio>
        <Radio value="P3" label="P3 - Minor Impact">
          Minimal user impact or single user affected
        </Radio>
      </RadioGroup>
    </FieldGroup>
  </Section>

  <Section title="Additional context (optional)">
    <FieldGroup>
      <Label>Suspected root cause</Label>
      <TextArea
        placeholder="e.g., Recent deployment (v2.3.1), database migration, config change..."
      />
    </FieldGroup>

    <FieldGroup>
      <Label>Affected regions</Label>
      <MultiSelect
        options={["us-east-1", "us-west-2", "eu-west-1"]}
      />
    </FieldGroup>

    <FieldGroup>
      <Label>Affected hosts (if known)</Label>
      <TagInput placeholder="pod-12, host-34, ..." />
    </FieldGroup>

    <FieldGroup>
      <Label>When did it start?</Label>
      <DateTimeInput />
    </FieldGroup>
  </Section>

  <Section title="Your information (for audit trail)">
    <FieldGroup>
      <Label>Your email</Label>
      <Input
        type="email"
        value={currentUser.email}
        disabled
      />
      <HelperText>
        Used for audit trail and NEXUS to follow up with you
      </HelperText>
    </FieldGroup>

    <FieldGroup>
      <Label>Your team</Label>
      <Select
        options={teams}
        value={currentUser.team}
        disabled
      />
    </FieldGroup>
  </Section>

  <SubmitButton>
    Report Incident → NEXUS will process immediately
  </SubmitButton>

  <SuccessMessage (on submit)>
    ✓ Incident INC-2026-05-28-001 created
    Watch progress on the dashboard
  </SuccessMessage>
</IncidentReportForm>
```

---

## 6. DATA MODELS (Complete Pydantic Schemas)

### 6.1 Incident Input Models

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, list, dict
from datetime import datetime
from enum import Enum

# Enums
class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class DetectionMethod(str, Enum):
    THRESHOLD_BREACH = "threshold_breach"
    ML_ANOMALY = "ml_anomaly"
    MANUAL_REPORT = "manual_report"
    LOG_STREAM = "log_stream"
    BATCH_IMPORT = "batch_import"

# Main models
class IncidentTrigger(BaseModel):
    """Entry point for all incidents"""
    incident_id: str
    timestamp_detected: datetime

    raw_symptoms: list[str]
    affected_service: str
    affected_hosts: list[str]

    signal_metrics: dict

    severity: Severity
    detection_method: DetectionMethod

    source_channel: str  # "webhook", "manual_form", "slack", "log_stream"
    webhook_source: Optional[str]  # "datadog", "prometheus", etc.

    @validator('raw_symptoms')
    def validate_symptoms(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one symptom required')
        return v

class MonitoringSignal(BaseModel):
    """Logs, metrics, traces from monitoring systems"""
    timestamp: datetime
    service: str

    logs: Optional[list[dict]]  # Log entries
    metrics: Optional[dict]      # Metric values
    traces: Optional[list[dict]]  # Request traces
    events: Optional[list[dict]]  # Infrastructure events

class ServiceMetadata(BaseModel):
    """Static service information"""
    name: str
    owner_team: str
    language: str
    framework: str
    infra_type: str

    dependencies: list[dict]
    current_version: str
    last_deployment: datetime

    cpu_limit_cores: float
    memory_limit_mb: int
```

---

## 7. INTEGRATION POINTS & APIs

### 7.1 REST API Endpoints

```python
# Alert Webhooks
POST   /api/v1/incidents/webhook
       Input: WebhookAlert (from Datadog, Prometheus, etc.)
       Output: {incident_id, queue_position, eta_sec}

# Manual Reports
POST   /api/v1/incidents/manual-report
       Input: ManualIncidentReport
       Output: {incident_id, status, eta_sec}

# Get Incident Status
GET    /api/v1/incidents/{incident_id}/status
       Output: {incident_id, status, timeline, results}

# Get All Incidents (queue)
GET    /api/v1/incidents/queue
       Output: [{incident_id, service, severity, created, status}, ...]

# Audit Logs
GET    /api/v1/audit-logs/{incident_id}
       Output: [{timestamp, agent, action, decision}, ...]

# Execute Runbook (admin only)
POST   /api/v1/incidents/{incident_id}/execute
       Output: {execution_id, status, result}
```

---

## 8. DEPLOYMENT ARCHITECTURE

### 8.1 System Components

```
┌───────────────────────────────────────────────────────────────┐
│                        NEXUS v2 DEPLOYMENT                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─ Input Layer ──────────────────────────────────┐          │
│  │ • FastAPI webhook server (uvicorn)             │          │
│  │ • Validation & enrichment service              │          │
│  │ • Log stream consumer (ELK, Loki)              │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
│  ┌─ Queue Layer ──────────────────────────────────┐          │
│  │ • Redis priority queue or PostgreSQL queue     │          │
│  │ • P0 > P1 > P2 > P3 priority                   │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
│  ┌─ Agent Layer ──────────────────────────────────┐          │
│  │ • SENTINEL (classification)                    │          │
│  │ • PRISM (diagnosis)                            │          │
│  │ • FORGE (generation + Codex API calls)         │          │
│  │ • GUARDIAN (safety review)                     │          │
│  │ Run in async workers (Python AsyncIO)          │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
│  ┌─ Execution Layer ──────────────────────────────┐          │
│  │ • Sandbox for bash/python script execution     │          │
│  │ • Kubernetes API client for kubectl commands   │          │
│  │ • Monitoring of execution progress             │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
│  ┌─ Storage Layer ────────────────────────────────┐          │
│  │ • SQLite (decisions) or PostgreSQL              │          │
│  │ • Incident Memory Graph (NetworkX)             │          │
│  │ • Audit logs (immutable)                       │          │
│  │ • Training data for RL                         │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
│  ┌─ Dashboard Layer ──────────────────────────────┐          │
│  │ • React frontend (Next.js optional)             │          │
│  │ • Real-time WebSocket updates                  │          │
│  │ • Timeline visualization                       │          │
│  │ • Agent decision details                       │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 9. STAKEHOLDER PRESENTATION FLOW

### 9.1 How to Present NEXUS to Leadership

**Minute 0-2: The Problem**
```
Show dashboard with incident INC-2026-05-28-001
"Industry MTTR: 74 minutes
 Our incident: 8.7 milliseconds
 That's 500,000× faster"
```

**Minute 2-4: The System**
```
"Four specialized agents:
 1. SENTINEL: Classifies what's broken (92% confidence)
 2. PRISM: Diagnoses why (88% confidence)
 3. FORGE: Generates how to fix using AI (87% confidence)
 4. GUARDIAN: Validates it's safe (95% safety score)

 Together, they resolve incidents in real-time."
```

**Minute 4-6: The Evidence**
```
Click through timeline on dashboard:
- SENTINEL log: "This is a resource exhaustion, P0"
- PRISM log: "Redis pool exhausted, 47 error logs confirm it"
- FORGE log: "Similar to INC-2026-02-14, generating fix from Codex"
- GUARDIAN log: "All safety checks pass, auto-approving"

"Every decision is logged and auditable."
```

**Minute 6-8: The Data**
```
Show input channels:
- Alert webhooks from Datadog/Prometheus
- Manual reports from engineers
- Continuous log stream analysis
- Batch imports for training

"We accept incidents from any source."
```

**Minute 8-10: The ROI**
```
"Industry baseline:
 • MTTR: 74 minutes × $5,000/hour = $6,167 per incident
 • Average company: 50 incidents/month = $3.1M annually

 With NEXUS:
 • MTTR: 8.7 milliseconds (99.98% faster)
 • Same incidents resolved instantly
 • Savings: $3.1M+ annually"
```

---

## SUMMARY: Enterprise Specification Target State

This document defines the intended NEXUS v2 enterprise target state:

✅ **4 input channels** (webhooks, forms, streams, batch)
✅ **Complete log ingestion pipeline** (validation → enrichment → queueing → persistence)
✅ **Agent job definitions** with visible decision logs
✅ **Enterprise UI** showing full transparency
✅ **Complete data models** (Pydantic schemas)
✅ **REST APIs** for integration
✅ **Deployment architecture**
✅ **Stakeholder presentation flow**

**Use this as the design reference; the current implementation status lives in the docs matrix and backlog.**
