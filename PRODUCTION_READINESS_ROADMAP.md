# NEXUS Production Readiness Roadmap

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Status:** Planning Phase  
**Timeline:** 9-15 weeks (depending on database decision in Task 1.4)

---

## Table of Contents
1. [Dependency Graph](#dependency-graph)
2. [Critical Path](#critical-path)
3. [Phase 3: Hardening (Weeks 1-4)](#phase-3-hardening)
4. [Phase 4: Production Deployment (Weeks 5-6)](#phase-4-production-deployment)
5. [Task Reference](#task-reference)
6. [Decision Gates](#decision-gates)

---

## Dependency Graph

```
Phase 3: Hardening
├── TRACK 1: Database Architecture (Decision Point)
│   ├── Task 1.1: Evaluate options (0.5 days)
│   ├── Task 1.2: IF SQLite chosen → Implement (5-7 days)
│   └── Decision Gate: Keep JSON or Migrate to SQLite?
│
├── TRACK 2: Monitoring (Depends on: None)
│   ├── Task 2.1: Add Prometheus metrics (1 day)
│   ├── Task 2.2: Prometheus config (0.5 days)
│   └── Task 2.3: Grafana dashboards (1.5 days)
│       └── Deliverable: 3 dashboards (Health, Performance, Errors)
│
├── TRACK 3: Alerting (Depends on: TRACK 2)
│   └── Task 3.1: Define SLOs + alert rules (1 day)
│       └── Deliverable: 6 alert rules in prometheus/alerts.yml
│
├── TRACK 4: Runbooks (Depends on: TRACK 3)
│   ├── Task 4.1: Write 6 incident response runbooks (2 days)
│   ├── Task 4.2: Write troubleshooting guide (1 day)
│   └── Deliverable: docs/runbooks/ directory
│
├── TRACK 5: Disaster Recovery (Depends on: None)
│   ├── Task 5.1: Backup automation script (0.5 days)
│   ├── Task 5.2: Restore + verify procedure (0.5 days)
│   ├── Task 5.3: Monthly DR drill process (2 days)
│   └── Deliverable: scripts/backup_nexus.sh, scripts/restore_nexus.sh
│
└── TRACK 6: Secret Rotation (Depends on: None)
    └── Task 6.1: Zero-downtime rotation code (1 day)
        └── Deliverable: Modified server/webhooks.py

Phase 4: Production Deployment
├── TRACK 7: Pre-Production Validation (Depends on: TRACK 1-6)
│   ├── Task 7.1: Security review (2 days)
│   ├── Task 7.2: Load testing (1 day)
│   ├── Task 7.3: Disaster recovery drill (1 day)
│   └── Task 7.4: Ops team training (1 day + 1 week availability)
│
└── TRACK 8: Production Cutover (Depends on: TRACK 7)
    ├── Task 8.1: Deploy to production (0.5 days)
    ├── Task 8.2: Monitor for 24 hours (2 days)
    └── Task 8.3: Handoff to operations (1 day)
```

---

## Critical Path

**Shortest path to production (days):**

```
Week 1-2: 
  - Task 1.1: Database decision (0.5 days) 
  - Task 1.2 (optional): SQLite migration (5-7 days)
  - Task 2: Monitoring (3 days) [in parallel with 1.2]

Week 3:
  - Task 3: Alerting (1 day)
  - Task 4: Runbooks (3 days) [in parallel with 3]
  - Task 5: Disaster Recovery (2 days) [in parallel with 4]

Week 4:
  - Task 6: Secret Rotation (1 day)

Week 5:
  - Task 7: Pre-Production Validation (5 days)

Week 5-6:
  - Task 8: Production Cutover (3.5 days)

TOTAL: 9-15 weeks
(9 weeks if JSON, 15 weeks if SQLite migration needed)
```

---

# PHASE 3: HARDENING (Weeks 1-4)

## TRACK 1: Database Architecture Decision & Implementation

### Task 1.1: Evaluate Database Options
**Status:** Not Started  
**Duration:** 0.5 days  
**Owner:** Tech Lead + Ops Lead  
**Effort:** 4 hours discussion + decision

**Objective:**
Decide between JSON, SQLite, or PostgreSQL based on pilot feedback.

**Decision Criteria:**

| Decision Point | Recommendation |
|---|---|
| Pilot feedback: "1 operator only" | **DECISION: Keep JSON (0 days effort)** |
| Pilot feedback: "3-5 concurrent operators needed" | **DECISION: Migrate to SQLite (5-7 days)** |
| Pilot feedback: "10+ concurrent operators, need multi-region" | **DECISION: Use PostgreSQL (10-14 days)** |

**Input Data Needed:**
- Pilot customer feedback on concurrent operator needs
- Expected user count at product launch
- SLA requirements (uptime, latency)

**Acceptance Criteria:**
- [ ] Database choice documented in PRODUCTION_READINESS_ROADMAP.md
- [ ] Justification written (why this choice over others)
- [ ] Technical team agrees with choice
- [ ] Effort estimate updated based on choice

**Output:**
- Database choice: [ ] JSON / [ ] SQLite / [ ] PostgreSQL
- Updated timeline

---

### Task 1.2: Database Migration (SQLite only - if Task 1.1 chooses SQLite)

**Status:** Not Started  
**Duration:** 5-7 days (only if SQLite chosen)  
**Owner:** Backend Engineer  
**Effort:** Full-time

#### Task 1.2.1: Create Database Schema

**Files to Create:**
- `server/schema.sql` (new)

**Deliverable:**
```sql
-- Table 1: incidents
CREATE TABLE incidents (
    nexus_incident_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB NOT NULL,
    UNIQUE(tenant_id, nexus_incident_id)
);

CREATE INDEX idx_incidents_tenant_id ON incidents(tenant_id);
CREATE INDEX idx_incidents_created_at ON incidents(created_at DESC);
CREATE INDEX idx_incidents_updated_at ON incidents(updated_at DESC);

-- Table 2: audit_logs
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    data JSONB NOT NULL
);

CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
```

**Acceptance Criteria:**
- [ ] Schema file created and reviewed
- [ ] All indexes created for query performance
- [ ] Foreign key constraints validated
- [ ] Schema tested with sample data

**Effort:** 1 day

---

#### Task 1.2.2: Rewrite Database Layer

**Files to Modify:**
- `server/db.py` → Replace with SQLite implementation
- `server/repositories.py` → Update to use SQLite queries

**Key Classes to Implement:**

```python
class SQLiteIncidentStore:
    # Methods:
    - get_incident_for_tenant(nexus_incident_id, tenant_id)
    - list_incidents_for_tenant(tenant_id, limit, offset)
    - create_incident(incident_record)
    - update_incident(nexus_incident_id, **updates)
    - delete_incident(nexus_incident_id)  # If needed
```

**Acceptance Criteria:**
- [ ] All existing tests pass with SQLite backend
- [ ] No N+1 queries (verified with EXPLAIN QUERY PLAN)
- [ ] Concurrent updates don't lose data
- [ ] Query latency < 10ms for single record
- [ ] Query latency < 100ms for list (100 records)

**Effort:** 3 days

---

#### Task 1.2.3: Migration Script

**File to Create:**
- `scripts/migrate_to_sqlite.py` (new)

**Functionality:**
1. Load all incidents from `artifacts/incidents.json`
2. Insert into SQLite database
3. Verify row counts match
4. Spot-check 10 random incidents
5. Print migration summary

**Acceptance Criteria:**
- [ ] Script runs without errors
- [ ] All incidents migrated
- [ ] Row counts match (incidents in JSON = records in SQLite)
- [ ] Spot-check finds no data corruption
- [ ] Rollback plan documented (keep JSON backup 30 days)

**Effort:** 1 day

---

#### Task 1.2.4: Performance Testing

**File to Create:**
- `tests/test_sqlite_performance.py` (new)

**Tests to Write:**

```python
def test_single_incident_retrieval():  # Target: < 10ms
def test_list_1000_incidents():        # Target: < 100ms  
def test_concurrent_writes_no_loss():  # Target: 100 concurrent writes, 0 loss
def test_query_plan_uses_indexes():    # Target: SEARCH not SCAN
```

**Acceptance Criteria:**
- [ ] Single-incident retrieval: < 10ms
- [ ] List 100 incidents: < 100ms
- [ ] 100 concurrent writes: 0 data loss
- [ ] EXPLAIN QUERY PLAN shows indexed searches
- [ ] All performance tests pass

**Effort:** 1 day

---

## TRACK 2: Monitoring & Observability

### Task 2.1: Add Prometheus Metrics Endpoint

**Status:** Not Started  
**Duration:** 1 day  
**Owner:** Backend Engineer

**Files to Create:**
- `server/metrics.py` (new) — Metric definitions
- `server/routes/metrics.py` (new) — /metrics endpoint

**Metrics to Implement:**

```python
# Counters
incidents_created_total (labels: family, source)
guardian_decisions_total (labels: decision)
auth_failures_total (labels: failure_type)

# Histograms
artifact_persistence_latency_ms (buckets: [10, 50, 100, 500, 1000, 5000])
incident_processing_duration_seconds (buckets: [1, 5, 10, 30, 60, 300])
replay_duration_seconds (buckets: [1, 5, 10, 30, 60, 300])

# Gauges
active_replays
pending_guardian_reviews
database_size_bytes
```

**Acceptance Criteria:**
- [ ] /metrics endpoint returns Prometheus text format
- [ ] All metrics above are reported
- [ ] Metrics scrape without error
- [ ] Labels are consistent (no typos)
- [ ] Metric values make sense (non-negative, increasing trends)

**Effort:** 1 day

---

### Task 2.2: Prometheus Configuration

**Status:** Not Started  
**Duration:** 0.5 days  
**Owner:** DevOps / Platform Engineer

**Files to Create:**
- `deployment/prometheus.yml` (new)
- `deployment/docker-compose.prometheus.yml` (new)

**Configuration:**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'nexus'
    static_configs:
      - targets: ['localhost:7860']
    metrics_path: '/metrics'
```

**Acceptance Criteria:**
- [ ] Prometheus config file created
- [ ] Config validates without errors
- [ ] Prometheus can scrape /metrics endpoint
- [ ] Metrics appear in Prometheus UI
- [ ] Data retention set to 30 days

**Effort:** 0.5 days

---

### Task 2.3: Grafana Dashboards

**Status:** Not Started  
**Duration:** 1.5 days  
**Owner:** DevOps / Data Visualization Engineer

**Files to Create:**
- `deployment/grafana/dashboard-system-health.json` (new)
- `deployment/grafana/dashboard-performance.json` (new)
- `deployment/grafana/dashboard-errors.json` (new)

**Dashboard 1: System Health**
- Panel 1: Uptime (health check success rate)
- Panel 2: Incident submission rate (incidents/hour)
- Panel 3: GUARDIAN approval rate (%)
- Panel 4: Auth failure rate (failures/hour)

**Dashboard 2: Performance**
- Panel 1: Artifact persistence latency (p50, p95, p99)
- Panel 2: Incident processing duration (p50, p95, p99)
- Panel 3: REPLICA replay duration (p50, p95, p99)
- Panel 4: Active replays (gauge)

**Dashboard 3: Error Analysis**
- Panel 1: Auth failures by type (pie chart)
- Panel 2: Incidents awaiting GUARDIAN review (time series)
- Panel 3: Failed artifact persists (counter)
- Panel 4: Database size over time (trend)

**Acceptance Criteria:**
- [ ] All 3 dashboards load without errors
- [ ] All metrics visible
- [ ] Data is collecting (not flat lines)
- [ ] Dashboards are readable and informative
- [ ] Charts have appropriate time ranges

**Effort:** 1.5 days

**Total TRACK 2 Effort:** 3 days

---

## TRACK 3: Alerting Rules

### Task 3.1: Define SLOs and Alert Rules

**Status:** Not Started  
**Duration:** 1 day  
**Owner:** DevOps / SRE Engineer

**Files to Create:**
- `deployment/prometheus/alerts.yml` (new)

**Alert Rules to Define:**

```yaml
# CRITICAL: Service Down
- alert: NexusDown
  expr: up{job="nexus"} == 0
  for: 5m
  severity: critical

# HIGH: Auth Attack Detection
- alert: SuspiciousAuthFailures
  expr: rate(nexus_auth_failures_total[5m]) > 0.2
  for: 5m
  severity: high

# HIGH: Database Performance Degradation
- alert: ArtifactPersistenceSlow
  expr: histogram_quantile(0.99, nexus_artifact_persistence_latency_ms) > 1000
  for: 10m
  severity: high

# MEDIUM: GUARDIAN Approval Rate Change
- alert: GuardianApprovalRateLow
  expr: (rate(nexus_guardian_decisions_total{decision="approve"}[1h]) / rate(nexus_guardian_decisions_total[1h])) < 0.5
  for: 30m
  severity: medium

# MEDIUM: Pending Reviews Accumulating
- alert: PendingGuardianReviewsHigh
  expr: nexus_pending_guardian_reviews > 50
  for: 30m
  severity: medium

# LOW: Database Size Growing Fast
- alert: DatabaseGrowthFast
  expr: rate(nexus_database_size_bytes[24h]) > 1000000000
  for: 2h
  severity: low
```

**Acceptance Criteria:**
- [ ] Alert rules defined for all critical/high/medium scenarios
- [ ] Thresholds based on baseline data from pilots
- [ ] Runbooks exist for each alert (See TRACK 4)
- [ ] Team knows how to acknowledge/silence alerts
- [ ] Alert rules tested (verify they fire when expected)

**Effort:** 1 day

**Total TRACK 3 Effort:** 1 day

---

## TRACK 4: Operational Runbooks

### Task 4.1: Write Incident Response Runbooks

**Status:** Not Started  
**Duration:** 2 days  
**Owner:** DevOps / On-Call Engineer + Backend Engineer

**Files to Create:**
- `docs/runbooks/nexus-down.md` (new)
- `docs/runbooks/auth-failures.md` (new)
- `docs/runbooks/slow-persistence.md` (new)
- `docs/runbooks/guardian-approval-rate.md` (new)
- `docs/runbooks/pending-reviews-backlog.md` (new)
- `docs/runbooks/database-growth.md` (new)

**Each Runbook Must Include:**

```markdown
# [Alert Name]

## Symptoms
- [List symptoms]

## Immediate Actions (< 5 min)
1. [Quick diagnostic step 1]
2. [Quick diagnostic step 2]
3. [Recovery step]

## If Immediate Actions Don't Work (5-15 min)
1. [Deeper investigation]
2. [Escalation path]

## If Still Broken (15+ min)
1. [Last resort action]
2. [Escalation contact]

## Post-Incident
- [Preventive measures]
- [Documentation update]
```

**Acceptance Criteria:**
- [ ] Each runbook has investigation steps
- [ ] Each runbook has recovery steps
- [ ] Escalation paths are clear
- [ ] Runbooks tested by ops team (dry run)
- [ ] Estimated resolution time provided for each

**Effort:** 2 days

---

### Task 4.2: Write Troubleshooting Guide

**Status:** Not Started  
**Duration:** 1 day  
**Owner:** DevOps / Documentation Engineer

**File to Create:**
- `docs/TROUBLESHOOTING_GUIDE.md` (new)

**Coverage:**
- "Incident won't load" scenario
- "Webhook keeps rejecting" scenario
- "Auth failures spiking" scenario
- "Database growing fast" scenario
- "GUARDIAN keeps rejecting safe actions" scenario
- "Performance degraded" scenario
- "Can't access the API" scenario

**Each Scenario Must Include:**
1. Symptom description
2. Diagnosis steps
3. Fix steps
4. Link to related runbook

**Acceptance Criteria:**
- [ ] Guide covers all common scenarios
- [ ] Each scenario has diagnosis + fix steps
- [ ] Links to detailed runbooks
- [ ] Tested by ops team

**Effort:** 1 day

**Total TRACK 4 Effort:** 3 days

---

## TRACK 5: Disaster Recovery & Backup Strategy

### Task 5.1: Backup Automation Script

**Status:** Not Started  
**Duration:** 0.5 days  
**Owner:** DevOps Engineer

**File to Create:**
- `scripts/backup_nexus.sh` (new)

**Script Functionality:**
1. Create backup of `artifacts/incidents.json`
2. Compress with gzip
3. Upload to S3
4. Delete local backups > 7 days old
5. Verify backup succeeded

**Acceptance Criteria:**
- [ ] Script runs without errors
- [ ] Files uploaded to S3
- [ ] Local retention limited to 7 days
- [ ] Backup verification works
- [ ] Cron job configured (every 6 hours)

**Cron Entry:**
```
0 */6 * * * /nexus/scripts/backup_nexus.sh >> /var/log/nexus-backup.log 2>&1
```

**Effort:** 0.5 days

---

### Task 5.2: Restore & Verify Procedure

**Status:** Not Started  
**Duration:** 0.5 days  
**Owner:** DevOps Engineer

**File to Create:**
- `scripts/restore_nexus.sh` (new)
- `docs/runbooks/disaster-recovery-procedure.md` (new)

**Script Functionality:**
1. Download backup from S3
2. Decompress
3. Verify JSON is valid
4. Count incidents
5. Stop service
6. Restore file
7. Start service
8. Verify health check passes

**Acceptance Criteria:**
- [ ] Restore script runs without errors
- [ ] Files downloaded from S3
- [ ] JSON validation works
- [ ] Service restarts cleanly
- [ ] Service health check passes

**Effort:** 0.5 days

---

### Task 5.3: Disaster Recovery Drill Process

**Status:** Not Started  
**Duration:** 2 days (1 day for process, 1 day for first drill)  
**Owner:** DevOps + On-Call Engineer

**Deliverables:**
- `docs/runbooks/monthly-dr-drill.md` (new) — Procedure
- DR drill execution checklist
- Postmortem template

**Drill Procedure:**
1. Monthly on first Monday of month
2. Simulate database corruption
3. Run restore script
4. Verify RTO < 1 hour
5. Verify all incidents recovered
6. Document findings
7. Update runbook if needed

**Acceptance Criteria:**
- [ ] Drill procedure documented
- [ ] Drill runs successfully
- [ ] RTO < 1 hour achieved
- [ ] All data recovered
- [ ] Postmortem completed

**Effort:** 2 days

**Total TRACK 5 Effort:** 3 days

---

## TRACK 6: Secret Rotation Automation

### Task 6.1: Zero-Downtime Secret Rotation

**Status:** Not Started  
**Duration:** 1 day  
**Owner:** Backend Engineer

**Files to Modify:**
- `server/webhooks.py` — Add support for both current + previous secret

**Implementation:**

```python
class WebhookVerifier:
    def __init__(self, current_secret: str, previous_secret: str | None = None):
        self.current_secret = current_secret
        self.previous_secret = previous_secret
    
    def verify(self, signature: str, body: bytes) -> bool:
        """Accept both current and previous secret during rotation."""
        expected_current = self._compute_signature(body, self.current_secret)
        expected_previous = (
            self._compute_signature(body, self.previous_secret)
            if self.previous_secret else None
        )
        
        return (hmac.compare_digest(signature, expected_current) or
                (expected_previous and hmac.compare_digest(signature, expected_previous)))
```

**Rotation Procedure Document:**
- `docs/runbooks/secret-rotation-procedure.md` (new)

**Procedure:**
1. Day 1: Deploy code accepting both secrets
2. Day 2-7: Customer rotates their secret
3. Day 8: Remove previous secret support
4. Day 30: Archive old secret

**Acceptance Criteria:**
- [ ] Code accepts both secrets
- [ ] Rotation procedure documented
- [ ] Tested with live webhook calls
- [ ] Audit log records rotation

**Effort:** 1 day

**Total TRACK 6 Effort:** 1 day

---

# PHASE 4: PRODUCTION DEPLOYMENT (Weeks 5-6)

## TRACK 7: Pre-Production Validation

### Task 7.1: Security Review Checklist

**Status:** Not Started  
**Duration:** 2 days  
**Owner:** Security Engineer + Backend Engineer

**Deliverable:**
- `docs/security-review-checklist.md` (new)

**Areas to Review:**

- [ ] **Authentication**
  - All endpoints require auth headers
  - Error messages don't leak info
  - Auth failures logged with context
  - Brute force test: 100 requests verified rate-limited

- [ ] **Tenant Isolation**
  - No fallback paths in incident access
  - Tenant ID enforced in all queries
  - Cross-tenant access attempt returns 404/403
  - Audit log verified for no tenant mismatches

- [ ] **Input Validation**
  - All request models have constraints
  - Oversized raw_text rejected
  - Invalid severity rejected
  - Unicode/binary handling verified

- [ ] **Data Persistence**
  - Artifact writes are atomic
  - Kill-process test: data integrity verified
  - Full disk scenario: graceful error
  - Backup/restore tested

- [ ] **Secrets Management**
  - NEXUS_WEBHOOK_SIGNING_SECRET enforced
  - Secret never logged
  - Rotation tested
  - Expired secret rejected

- [ ] **Rate Limiting**
  - AsyncIO locks prevent bypass
  - 100 concurrent requests tested
  - 429 returned correctly
  - Different users independent

- [ ] **Logging & Audit**
  - All security events logged
  - Audit log contains actor_id + tenant_id
  - Auth failure spike triggers alert
  - Customer can query audit log

**Acceptance Criteria:**
- [ ] All checklist items passing
- [ ] Security review document signed off

**Effort:** 2 days

---

### Task 7.2: Load Testing

**Status:** Not Started  
**Duration:** 1 day  
**Owner:** Backend Engineer

**File to Create:**
- `tests/load_test.py` (new)

**Test Scenarios:**
- 100 concurrent users submitting incidents
- 100 concurrent users viewing incidents
- Mixed: 50 submit + 50 view simultaneously

**Success Criteria:**
- 100 concurrent users sustained
- p99 latency < 1 second
- Error rate < 0.1%
- CPU/memory stable

**Acceptance Criteria:**
- [ ] Load test script created and runs
- [ ] Target metrics achieved
- [ ] Bottleneck identified (if any)

**Effort:** 1 day

---

### Task 7.3: Disaster Recovery Drill

**Status:** Not Started  
**Duration:** 1 day  
**Owner:** DevOps + On-Call Engineer

**Drill:**
1. Simulate database corruption
2. Run restore script
3. Verify RTO < 1 hour
4. Verify all data recovered
5. Resume normal operation

**Acceptance Criteria:**
- [ ] RTO < 1 hour achieved
- [ ] All data recovered
- [ ] Procedure documented
- [ ] Team trained

**Effort:** 1 day

---

### Task 7.4: Ops Team Training

**Status:** Not Started  
**Duration:** 1 day (trainer) + 1 week (ops availability)  
**Owner:** DevOps Lead + Backend Lead

**Training Agenda:**

1. **System Architecture** (1 hour)
   - How NEXUS works
   - Data flow: incident → relay → GUARDIAN → audit
   - Key files: incidents.json, .nexus_audit_log.json, metrics

2. **Operations** (2 hours)
   - Start/stop/restart service
   - Check logs
   - Monitor dashboards
   - Respond to alerts

3. **Troubleshooting** (2 hours)
   - Incident response runbooks
   - Troubleshooting guide
   - Escalation paths

4. **Disaster Recovery** (1 hour)
   - Restore from backup
   - When to restore vs. restart
   - Full DR drill

5. **Hands-On Lab** (2 hours)
   - Set up local NEXUS
   - Submit test incident
   - Review audit log
   - Run troubleshooting scenarios

**Acceptance Criteria:**
- [ ] All ops team members trained
- [ ] Each member runs troubleshooting guide
- [ ] Each member executes restore procedure
- [ ] Knowledge transfer documented

**Effort:** 1 day (trainer) + 1 week (team availability)

**Total TRACK 7 Effort:** 5 days (sequential)

---

## TRACK 8: Production Cutover

### Task 8.1: Deploy to Production

**Status:** Not Started  
**Duration:** 0.5 days  
**Owner:** DevOps Engineer

**Pre-Deployment Checklist:**
- [ ] All pre-production validation passed
- [ ] Load testing completed
- [ ] DR drill completed
- [ ] Ops team trained
- [ ] Monitoring active
- [ ] Backups tested
- [ ] Runbooks reviewed

**Deployment Steps:**

```bash
# 1. Build production image
docker build -t nexus:prod .

# 2. Tag and push
docker tag nexus:prod gcr.io/nexus-prod/nexus:latest
docker push gcr.io/nexus-prod/nexus:latest

# 3. Deploy
docker pull gcr.io/nexus-prod/nexus:latest
docker run --name nexus-prod -p 7860:7860 ...

# 4. Verify
curl http://localhost:7860/health

# 5. Smoke tests
./scripts/local_enterprise_smoke.sh

# 6. Cutover
# Update load balancer / DNS
```

**Acceptance Criteria:**
- [ ] Service starts cleanly
- [ ] Health check passes
- [ ] Smoke tests all pass
- [ ] Metrics flowing to Prometheus

**Effort:** 0.5 days

---

### Task 8.2: Monitor for 24 Hours

**Status:** Not Started  
**Duration:** 2 days  
**Owner:** On-Call Engineer + Backend Lead

**Monitoring Checklist:**
- [ ] Health check passing continuously
- [ ] Metrics collecting without gaps
- [ ] Auth failure rate normal (< 1/hour)
- [ ] Incident processing latency stable
- [ ] GUARDIAN approval rate matches baseline
- [ ] Artifact persistence latency < 100ms
- [ ] No unexpected errors in logs
- [ ] Backup running successfully

**On-Call Support:**
- 24-hour rotation
- Resolve any alerts immediately
- Document any issues for postmortem

**Acceptance Criteria:**
- [ ] 24 hours without incidents
- [ ] All metrics stable
- [ ] Customer satisfied

**Effort:** 2 days (on-call)

---

### Task 8.3: Handoff to Operations

**Status:** Not Started  
**Duration:** 1 day  
**Owner:** DevOps Lead + Backend Lead

**Knowledge Transfer:**
1. Review all runbooks with ops team
2. Review all dashboards and alerts
3. Confirm escalation chain
4. Document contact info for engineering
5. Schedule regular sync meetings (weekly)

**Documentation Handoff:**
- [ ] Master operator guide
- [ ] Incident response runbooks (6 runbooks)
- [ ] Troubleshooting guide
- [ ] Grafana dashboard guide
- [ ] Disaster recovery procedure
- [ ] Secret rotation procedure
- [ ] Performance tuning guide
- [ ] Escalation policy

**Acceptance Criteria:**
- [ ] Ops team confirms understanding
- [ ] All documentation handed over
- [ ] Escalation chain confirmed
- [ ] First on-call shift completed

**Effort:** 1 day

**Total TRACK 8 Effort:** 3.5 days (with 24-hour on-call overlap)

---

# TASK REFERENCE

## Master Task List (by ID)

| ID | Task | Duration | Owner | Status | Dependencies |
|---|---|---|---|---|---|
| 1.1 | Database Evaluation | 0.5d | Tech Lead | Not Started | None |
| 1.2.1 | Create Schema | 1d | Backend | Not Started | 1.1 |
| 1.2.2 | Rewrite DB Layer | 3d | Backend | Not Started | 1.2.1 |
| 1.2.3 | Migration Script | 1d | Backend | Not Started | 1.2.2 |
| 1.2.4 | Performance Test | 1d | Backend | Not Started | 1.2.3 |
| 2.1 | Prometheus Metrics | 1d | Backend | Not Started | None |
| 2.2 | Prometheus Config | 0.5d | DevOps | Not Started | 2.1 |
| 2.3 | Grafana Dashboards | 1.5d | DevOps | Not Started | 2.2 |
| 3.1 | Alert Rules | 1d | SRE | Not Started | 2.3 |
| 4.1 | Incident Runbooks | 2d | DevOps/Backend | Not Started | 3.1 |
| 4.2 | Troubleshooting Guide | 1d | DevOps | Not Started | 4.1 |
| 5.1 | Backup Script | 0.5d | DevOps | Not Started | None |
| 5.2 | Restore Script | 0.5d | DevOps | Not Started | 5.1 |
| 5.3 | DR Drill Process | 2d | DevOps/On-Call | Not Started | 5.2 |
| 6.1 | Secret Rotation | 1d | Backend | Not Started | None |
| 7.1 | Security Review | 2d | Security/Backend | Not Started | 1.2/6.1 |
| 7.2 | Load Testing | 1d | Backend | Not Started | 2.3 |
| 7.3 | DR Drill | 1d | DevOps/On-Call | Not Started | 5.3 |
| 7.4 | Ops Training | 1d+1w | DevOps Lead | Not Started | 4/5 |
| 8.1 | Production Deploy | 0.5d | DevOps | Not Started | 7.* |
| 8.2 | 24hr Monitor | 2d | On-Call | Not Started | 8.1 |
| 8.3 | Ops Handoff | 1d | DevOps/Backend | Not Started | 8.2 |

---

# DECISION GATES

## Gate 1: Database Choice (End of Task 1.1)

**Decision Required:**
- [ ] Keep JSON (0 days)
- [ ] Migrate to SQLite (5-7 days)
- [ ] Migrate to PostgreSQL (10-14 days)

**Inputs:**
- Pilot feedback on concurrent operator needs
- Expected user count at launch
- SLA requirements

**Output:**
- Updated timeline (9 weeks vs. 15 weeks)
- Tasks 1.2.1-1.2.4 added or removed

**Owner:** Tech Lead + Ops Lead

---

## Gate 2: Pre-Production Validation Pass (End of Task 7.4)

**Decision Required:**
- [ ] GO: All validations passed, proceed to production
- [ ] CONDITIONAL: Some issues found, but fixable
- [ ] NO-GO: Critical issues, delay production

**Inputs:**
- Security review results
- Load test results
- DR drill results
- Ops team readiness

**Output:**
- GO/NO-GO decision
- Any blocking items to fix
- Updated go-live date

**Owner:** Tech Lead + DevOps Lead

---

## Gate 3: Production Cutover Approval (End of Task 8.2)

**Decision Required:**
- [ ] CUTOVER: Move to full production
- [ ] ROLLBACK: Revert to pilot version
- [ ] HOLD: Keep monitoring, address issue

**Inputs:**
- 24-hour monitoring results
- Customer satisfaction
- Metric stability
- No critical incidents

**Output:**
- Production is now the primary system
- Ops team fully responsible
- Engineering on-call support

**Owner:** DevOps Lead + On-Call Lead

---

# TRACKING & STATUS

Use this section to track progress:

## Week 1
- [ ] Task 1.1: Database evaluation
- [ ] Task 2.1: Prometheus metrics
- [ ] Task 2.2: Prometheus config

## Week 2
- [ ] Task 1.2: SQLite migration (if chosen)
- [ ] Task 2.3: Grafana dashboards
- [ ] Task 3.1: Alert rules (depends on 2.3)

## Week 3
- [ ] Task 4.1: Incident runbooks (depends on 3.1)
- [ ] Task 4.2: Troubleshooting guide
- [ ] Task 5: Disaster recovery
- [ ] Task 6: Secret rotation

## Week 4
- [ ] Task 6.1: Secret rotation (complete)
- [ ] Buffer for overruns

## Week 5
- [ ] Task 7: Pre-production validation
- [ ] Security review, load testing, training

## Week 5-6
- [ ] Task 8: Production cutover
- [ ] Deploy, 24hr monitoring, ops handoff

---

# NOTES & ASSUMPTIONS

1. **Team Size:** Assumes 2-3 engineers (1 backend, 1-2 DevOps)
2. **Database Decision:** Critical path depends on this (9 vs. 15 weeks)
3. **Parallel Work:** Tasks without dependencies can run in parallel
4. **Testing:** All tasks include acceptance criteria and testing
5. **Documentation:** Every task includes documentation deliverable
6. **Training:** Ops team needs 1 week for full availability/training

---

**Document Status:** Ready for independent execution  
**Next Step:** Review Task 1.1 (Database Evaluation) to unlock timeline
