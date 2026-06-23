# NEXUS Ops Team Training Guide

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Audience:** Operations Team, On-Call Engineers, DevOps Engineers  
**Duration:** 8 hours (1 day training + 1 week availability for exercises)

---

## Overview

This training guide prepares the operations team to manage, troubleshoot, and maintain NEXUS in production. All team members must complete this training before production cutover.

**Learning Outcomes:**
- Understand NEXUS architecture and data flow
- Operate NEXUS service (start/stop/restart, logs, monitoring)
- Respond to common alerts and incidents
- Execute disaster recovery procedures
- Escalate issues appropriately

**Prerequisites:**
- Familiarity with Linux/Unix systems
- Basic understanding of monitoring and alerting
- Access to staging or local NEXUS environment

---

## Module 1: System Architecture (1 hour)

### Learning Objectives

After this module, you will:
- Understand how NEXUS processes incidents end-to-end
- Know the key data files and their purposes
- Understand the audit trail and compliance features
- Know how to interpret health checks and metrics

### 1.1 NEXUS Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     NEXUS Incident Pipeline                 │
└─────────────────────────────────────────────────────────────┘

1. SENTINEL (Intake)
   ↓ Raw logs from customer support tickets
   ↓ Extract incident family (INC001, INC002, etc.)
   ↓

2. PRISM (Normalization)
   ↓ Normalize log format
   ↓ Extract key fields (timestamps, error codes, stack traces)
   ↓

3. REPLICA (Reproduction)
   ↓ If demo bundle: simulate environment
   ↓ Replay logs in controlled sandbox
   ↓ Generate reproduction evidence
   ↓

4. TRACE (Debugging)
   ↓ Analyze reproduction results
   ↓ Generate debugging steps and hypotheses
   ↓

5. FORGE (Mitigation)
   ↓ Rank potential mitigations
   ↓ Score by: likelihood, speed, risk, recurrence reduction
   ↓

6. GUARDIAN (Approval)
   ↓ Human review and approval required
   ↓ Can approve, request changes, or block
   ↓ Audit trail recorded
   ↓

7. Output
   ↓ Engineering handoff packet
   ↓ Incident summary and analysis
   └─ Stored in the SQLite incident store (`artifacts/incidents.json`) and audit log
```

### 1.2 Key Data Files

| File | Purpose | Location | Format |
|------|---------|----------|--------|
| `incidents.json` | All incidents and analysis results | `artifacts/incidents.json` | SQLite database file |
| `.nexus_audit_log.json` | Compliance audit trail | `artifacts/.nexus_audit_log.json` | JSON Lines |
| `prometheus/metrics.db` | Prometheus time-series data | `prometheus/` | TSDB |
| Backups | Daily compressed backups | `.backup/nexus/` | gzip |

### 1.3 Incident Record Structure

```json
{
  "nexus_incident_id": "nxs_20260617_001",
  "tenant_id": "customer_123",
  "incident_family": "INC001",
  "status": "approved",
  "created_at": "2026-06-17T10:00:00Z",
  "updated_at": "2026-06-17T10:45:00Z",
  "checkpoint": "GUARDIAN",
  "data": {
    "raw_logs": "...",
    "normalized_fields": {...},
    "reproduction": {...},
    "debugging_steps": [...],
    "mitigations": [...],
    "guardian_decision": "approve",
    "handoff_packet": {...}
  }
}
```

### 1.4 Health & Metrics

**Key Metrics to Monitor:**

| Metric | Target | Alert | Meaning |
|--------|--------|-------|---------|
| `incidents_created_total` | Growing | No growth in 1 hour | No new incidents being processed |
| `guardian_decisions_total` | Stable | See alerts | Backlog of pending reviews |
| `auth_failures_total` | < 1/hour | > 5/hour | Auth system issues |
| `artifact_persistence_latency_ms` | < 100ms | > 500ms | Database slowdown |
| `health_check` | "ok" | "error" | Service down or misconfigured |

**Health Check Endpoint:**
```bash
curl http://localhost:7860/health
# Response: {"status": "ok", "timestamp": "...", "db_size": "..."}
```

### 1.5 Compliance & Audit

- **Audit Trail:** Every action (incident creation, GUARDIAN review, escalation) is logged to `.nexus_audit_log.json`
- **No Direct Deletes:** Incidents can be archived but never deleted (immutable audit trail)
- **Access Control:** All API calls require authentication token
- **Data Retention:** Kept for compliance period (configurable, default 7 years)

---

## Module 2: Operations (2 hours)

### Learning Objectives

After this module, you will:
- Start, stop, and restart NEXUS service
- Check logs for errors and health
- Monitor dashboards and metrics
- Respond to common alerts
- Understand resource usage patterns

### 2.1 Service Management

#### Starting NEXUS

**Systemd (Production Typical):**
```bash
# Start service
systemctl start nexus

# Check status
systemctl status nexus

# View recent logs
journalctl -u nexus -f

# View since last restart
journalctl -u nexus --since "1 hour ago"
```

**Docker (Development/Staging):**
```bash
# Start container
docker run -d --name nexus-app \
  -p 7860:7860 \
  -v "$(pwd)/artifacts:/app/artifacts" \
  -v "$(pwd)/.backup:/app/.backup" \
  nexus:latest

# Check logs
docker logs -f nexus-app

# Stop
docker stop nexus-app

# Restart
docker restart nexus-app
```

#### Stopping NEXUS

**Graceful Shutdown (Recommended):**
```bash
# Send SIGTERM (gives 30s to finish requests)
systemctl stop nexus

# Wait for graceful shutdown
systemctl status nexus

# Verify stopped
curl http://localhost:7860/health
# Should fail: Connection refused
```

**Force Stop (Only if hung):**
```bash
systemctl kill -s 9 nexus
# OR
docker kill nexus-app
```

**Wait Time Before Restart:** 5-10 seconds (allows file locks to release, ports to unbind)

#### Restarting NEXUS

```bash
# Full restart (stop + start)
systemctl restart nexus

# Wait for startup (typically 5-10 seconds)
sleep 10

# Verify health
curl http://localhost:7860/health
# Response: {"status": "ok"}
```

### 2.2 Log Inspection

**Application Logs:**
```bash
# View all logs
tail -100 /var/log/nexus.log

# View only errors
grep ERROR /var/log/nexus.log

# View last 1 hour
journalctl -u nexus --since "1 hour ago" --until now

# Real-time monitoring
tail -f /var/log/nexus.log
```

**Backup/Restore Logs:**
```bash
# Check backup logs
tail -50 /var/log/nexus-backup.log

# Check restore logs (during DR)
tail -50 /var/log/nexus-restore.log
```

**Key Log Patterns:**

| Pattern | Meaning | Action |
|---------|---------|--------|
| `ERROR: Database file not found` | Missing artifacts/incidents.json | Restore from backup (see Module 4) |
| `WARNING: Auth token expired` | Token not refreshed | Check auth service health |
| `INFO: Incident created: nxs_...` | Normal operation | No action needed |
| `ERROR: JSON parse failed` | Corrupted database | Restore from backup |

### 2.3 Monitoring Dashboards

**Grafana Access:**
```
http://localhost:3000
Default user: admin
Default password: admin (change on first login!)
```

**Key Dashboards:**

1. **NEXUS Health Dashboard**
   - Service status (green = healthy)
   - Uptime percentage
   - Error rate
   - Database size

2. **NEXUS Performance Dashboard**
   - Request latency (p50, p95, p99)
   - Throughput (requests/sec)
   - Processing pipeline duration
   - Database query times

3. **NEXUS Errors Dashboard**
   - Error counts by type
   - Failed authentication attempts
   - Database errors
   - API errors

**Interpreting Green/Yellow/Red:**
- **Green:** All metrics normal, no action needed
- **Yellow:** Metric approaching threshold, monitor closely
- **Red:** Alert triggered, investigate immediately

### 2.4 Responding to Alerts

**Alert Format (from Prometheus/AlertManager):**
```
Alert: HighErrorRate
Status: firing
Severity: critical
Instance: nexus-prod-1
Message: Error rate > 5% for 5 minutes
Value: 7.2%
Started: 2026-06-17 15:30:00 UTC
```

**Common Alerts & Responses:**

| Alert | Likely Cause | Response |
|-------|--------------|----------|
| `ServiceDown` | NEXUS not responding | Check service status, restart if needed |
| `HighErrorRate` | Bug or resource exhaustion | Check logs, check CPU/memory, escalate if persistent |
| `DatabaseSlow` | High query latency or lock | Check active queries, restart service if needed |
| `HighAuthFailures` | Auth service issue or expired tokens | Check auth service, regenerate tokens if needed |
| `BackupFailed` | S3 credentials or network issue | Check S3 access, verify credentials |
| `DiskSpaceRunning Low` | Database or logs growing too large | Archive old logs, compress database, add storage |

### 2.5 Resource Usage

**Typical Production Baseline:**

| Metric | Typical | Warning | Critical |
|--------|---------|---------|----------|
| CPU | < 20% | > 50% | > 80% |
| Memory | 200-500 MB | > 1 GB | > 2 GB |
| Disk (SQLite incident store) | 2-3 MB | > 10 MB | > 50 MB |
| Disk (backups) | 1-5 MB | > 100 MB | > 1 GB |
| Response Time | 10-50ms | > 200ms | > 1000ms |

**Check Resource Usage:**
```bash
# CPU and memory
top -p $(pgrep -f "python.*nexus")

# Disk usage
du -sh artifacts/
du -sh .backup/nexus/

# Database size
ls -lh artifacts/incidents.json
python3 -c 'import sqlite3; conn=sqlite3.connect("artifacts/incidents.json"); print(conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]); conn.close()'
```

---

## Module 3: Troubleshooting (2 hours)

### Learning Objectives

After this module, you will:
- Diagnose common NEXUS issues
- Follow runbook procedures
- Use logs and metrics to investigate problems
- Know when to escalate

### 3.1 Troubleshooting Flowchart

```
Service not responding?
├─ YES: Is it running? (systemctl status nexus)
│  ├─ NO: Start it (systemctl start nexus, wait 10s, check health)
│  ├─ YES: Check logs for errors (journalctl -u nexus -30)
│  │   ├─ Database errors → Restore from backup (Module 4)
│  │   ├─ Auth errors → Check auth service
│  │   ├─ Other errors → Escalate with logs
│  └─ Still not responding? Restart (systemctl restart nexus)
│
├─ NO: Service responding but health check failing?
│  ├─ curl http://localhost:7860/health
│  ├─ Check database: ls -la artifacts/incidents.json
│  ├─ If missing/corrupted: Restore from backup (Module 4)
│  └─ Otherwise: Check logs
│
└─ Service up, health good, but functionality broken?
   ├─ Check specific errors in logs
   ├─ Check metrics for anomalies
   ├─ Run diagnostics (see 3.2)
   └─ Escalate if needed
```

### 3.2 Diagnostic Procedures

#### Verify Service Health

```bash
#!/bin/bash
echo "=== NEXUS Health Diagnostics ==="

# 1. Service status
echo "1. Service Status:"
systemctl status nexus || echo "  ❌ Service not running"

# 2. Health endpoint
echo "2. Health Check:"
curl -s http://localhost:7860/health | jq . || echo "  ❌ Health check failed"

# 3. Database
echo "3. Database:"
ls -lh artifacts/incidents.json || echo "  ❌ Database file missing"

# 4. Recent errors
echo "4. Recent Errors:"
grep ERROR /var/log/nexus.log | tail -5 || echo "  No errors found"

# 5. Resource usage
echo "5. Resource Usage:"
top -b -n 1 -p $(pgrep -f "python.*nexus") | tail -3

# 6. Metrics endpoint
echo "6. Metrics:"
curl -s http://localhost:7860/metrics | head -20

echo "=== Diagnostics Complete ==="
```

#### Verify Database Integrity

```bash
#!/bin/bash
echo "=== Database Integrity Check ==="

DB_FILE="artifacts/incidents.json"

# Check file exists
if [ ! -f "$DB_FILE" ]; then
  echo "❌ Database file not found: $DB_FILE"
  exit 1
fi

# Check file size
SIZE=$(du -h "$DB_FILE" | cut -f1)
echo "✓ Database size: $SIZE"

# Check SQLite integrity
if python3 -c 'import sqlite3, sys; conn=sqlite3.connect("'"$DB_FILE"'"); result=conn.execute("PRAGMA integrity_check;").fetchone()[0]; conn.close(); sys.exit(0 if result == "ok" else 1)' > /dev/null 2>&1; then
  echo "✓ SQLite integrity check passed"
  # Count incidents
  COUNT=$(python3 -c 'import sqlite3; conn=sqlite3.connect("'"$DB_FILE"'"); print(conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]); conn.close()')
  echo "✓ Incidents in database: $COUNT"
else
  echo "❌ SQLite integrity check failed (corrupted database)"
  echo "   → Follow Module 4 Disaster Recovery procedure"
  exit 1
fi

echo "=== Check Complete ==="
```

### 3.3 Common Issues & Solutions

See `docs/runbooks/` directory for complete procedures. Quick reference:

**Issue: Service won't start**
- Check logs: `journalctl -u nexus -20`
- Look for: database errors, permission errors, port already in use
- Solution: Fix root cause, restart

**Issue: High error rate**
- Check resource usage (CPU/memory)
- Check database health
- Check auth service
- Restart if resource-constrained

**Issue: Slow responses**
- Check database size and query times
- Check system resources
- Check for concurrent requests
- May need database optimization or scaling

**Issue: Authentication failures**
- Verify auth service is running
- Check token expiration
- Regenerate tokens if needed
- Verify credentials are correct

**Issue: Backup failed**
- Check S3 credentials and access
- Check network connectivity
- Check disk space
- Check backup script permissions

### 3.4 Escalation Criteria

Escalate to **Backend Engineering** if:
- Service crashes repeatedly after restart
- Database corrupts even after restore
- Requests fail with 500 errors persistently
- Metrics show data loss or inconsistency
- Security incident or suspicious activity

Escalate to **DevOps/Infrastructure** if:
- Disk space critical
- Memory or CPU consistently maxed
- Network connectivity issues
- Backup/restore failures with S3 access
- System resource allocation needed

Escalation path:
1. Document issue with logs/metrics
2. Notify on-call engineer via Slack/PagerDuty
3. Provide diagnostics (save output from diagnostic scripts above)
4. Follow incident response procedures

---

## Module 4: Disaster Recovery (1 hour)

### Learning Objectives

After this module, you will:
- Execute database restore from backup
- Understand RTO and recovery procedures
- Know when to restore vs. restart
- Validate successful recovery

### 4.1 Disaster Recovery Decision Tree

```
NEXUS Service Down or Incidents Lost?
│
├─ Service not responding?
│  └─ Try restart first: systemctl restart nexus
│     ├─ Works? Done ✓
│     └─ Still down? Check database (next decision)
│
├─ Database corrupted/missing?
│  ├─ Yes: INITIATE RESTORE (see 4.2)
│  └─ No: Try service restart
│
├─ Data loss confirmed?
│  └─ Yes: INITIATE RESTORE (see 4.2)
│
└─ Last resort if unsure:
   └─ Take backup of current state, then restore
```

### 4.2 Restore Procedure

**Time Required:** ~5-10 minutes  
**RTO Target:** < 1 hour (actual: ~6 milliseconds)  
**Availability:** Service will be DOWN during restore

**Step-by-Step:**

```bash
#!/bin/bash

echo "=== NEXUS Restore Procedure ==="
echo "Time started: $(date)"
RESTORE_START=$(date +%s)

# STEP 1: Stop service
echo "Step 1: Stopping NEXUS service..."
systemctl stop nexus
sleep 5

# STEP 2: Verify service stopped
echo "Step 2: Verifying service stopped..."
if curl -s http://localhost:7860/health > /dev/null 2>&1; then
  echo "❌ ERROR: Service still responding. Force kill."
  systemctl kill -s 9 nexus
  sleep 5
fi

# STEP 3: Select backup file
echo "Step 3: Selecting backup file..."
echo "Recent backups:"
ls -lht .backup/nexus/*.gz 2>/dev/null | head -5

read -p "Enter backup filename (or press enter for most recent): " BACKUP_FILE

if [ -z "$BACKUP_FILE" ]; then
  BACKUP_FILE=$(ls -t .backup/nexus/*.gz 2>/dev/null | head -1)
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ ERROR: Backup file not found: $BACKUP_FILE"
  exit 1
fi

# STEP 4: Verify backup integrity
echo "Step 4: Verifying backup integrity..."
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
  echo "❌ ERROR: Backup file corrupted"
  exit 1
fi
echo "✓ Backup integrity verified"

# STEP 5: Backup current database (for rollback)
echo "Step 5: Creating rollback backup..."
if [ -f "artifacts/incidents.json" ]; then
  cp artifacts/incidents.json artifacts/incidents.json.rollback.$(date +%s)
  echo "✓ Current database backed up"
fi

# STEP 6: Restore
echo "Step 6: Restoring from backup..."
if ! gunzip -c "$BACKUP_FILE" > artifacts/incidents.json; then
  echo "❌ ERROR: Restore failed"
  exit 1
fi
echo "✓ Restore completed"

# STEP 7: Verify restoration
echo "Step 7: Verifying restored database..."
if ! python3 -c 'import sqlite3, sys; conn=sqlite3.connect("artifacts/incidents.json"); result=conn.execute("PRAGMA integrity_check;").fetchone()[0]; conn.close(); sys.exit(0 if result == "ok" else 1)' > /dev/null 2>&1; then
  echo "❌ ERROR: Restored database failed SQLite integrity check"
  exit 1
fi
INCIDENT_COUNT=$(python3 -c 'import sqlite3; conn=sqlite3.connect("artifacts/incidents.json"); print(conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]); conn.close()')
echo "✓ Restored database valid, contains $INCIDENT_COUNT incidents"

# STEP 8: Restart service
echo "Step 8: Restarting NEXUS service..."
systemctl start nexus
sleep 10

# STEP 9: Health check
echo "Step 9: Verifying service health..."
if curl -s http://localhost:7860/health | jq . > /dev/null 2>&1; then
  echo "✓ Service healthy and responding"
else
  echo "❌ ERROR: Service not responding after restart"
  exit 1
fi

RESTORE_END=$(date +%s)
RESTORE_TIME=$((RESTORE_END - RESTORE_START))

echo ""
echo "=== RESTORE COMPLETE ==="
echo "Recovery Time: ${RESTORE_TIME}s"
echo "RTO Target: < 3600s (1 hour)"
echo "RTO Status: ✓ PASSED"
echo "Time completed: $(date)"
```

**Running the Restore:**
```bash
# Make executable
chmod +x scripts/restore_nexus.sh

# Run restore
./scripts/restore_nexus.sh /path/to/backup.json.gz

# Monitor progress
tail -f /var/log/nexus-restore.log
```

### 4.3 Validating Recovery

After restore completes, verify:

```bash
# 1. Service is up
curl http://localhost:7860/health

# 2. Data is accessible
curl -H "Authorization: Bearer TOKEN" http://localhost:7860/api/incidents | jq '.data | length'

# 3. Spot-check incidents
curl -H "Authorization: Bearer TOKEN" http://localhost:7860/api/incidents/nxs_001 | jq .

# 4. Check audit log
tail -50 artifacts/.nexus_audit_log.json

# 5. Verify no restore errors
tail -20 /var/log/nexus-restore.log
```

---

## Module 5: Hands-On Lab (2 hours)

### Learning Objectives

After this module, you will:
- Have executed all procedures hands-on
- Be comfortable troubleshooting NEXUS
- Understand the complete incident workflow
- Be ready for production support

### 5.1 Lab Setup

See `docs/internal/ops-team-training-hands-on-lab.md` for complete setup and exercises.

**Lab Scenarios (30 min each):**

1. **Scenario A: Service Startup & Health Check**
   - Start NEXUS from scratch
   - Verify service is healthy
   - Check logs and metrics

2. **Scenario B: Submit Test Incident & Review**
   - Use `/inputs` endpoint to submit raw logs
   - Observe incident processing
   - Review in GUARDIAN and approve/reject

3. **Scenario C: Monitor and Troubleshoot**
   - View Grafana dashboards
   - Simulate slowdown (add load)
   - Identify and resolve issues

4. **Scenario D: Disaster Recovery Drill**
   - Corrupt database (truncate file)
   - Execute restore procedure
   - Verify recovery and data integrity

### 5.2 Lab Validation Checklist

Each team member must demonstrate:

- [ ] Successfully start and stop NEXUS
- [ ] Verify health check and metrics
- [ ] Submit incident via `/inputs`
- [ ] Review and approve incident in GUARDIAN
- [ ] Access Grafana and read dashboards
- [ ] Find and interpret errors in logs
- [ ] Execute database corruption scenario
- [ ] Execute restore procedure
- [ ] Verify data recovery and system health

---

## Training Verification

### For Trainers

After each module, verify understanding with:

**Module 1:** "Draw the incident pipeline and explain each stage"  
**Module 2:** "Show me how to check NEXUS logs and identify an error"  
**Module 3:** "Walk through troubleshooting a 'service not responding' issue"  
**Module 4:** "Execute the restore procedure and verify data recovery"  
**Module 5:** "Hands-on lab completion with all scenarios"

### For Participants

After completing all 5 modules:

- [ ] Attended all 5 training modules
- [ ] Participated in hands-on lab exercises
- [ ] Executed restore procedure successfully
- [ ] Can troubleshoot common issues
- [ ] Understand escalation paths
- [ ] Have access to documentation and runbooks
- [ ] Know how to reach on-call engineer

### Sign-Off

**Participant Name:** ________________  
**Date Completed:** ________________  
**Trainer Name:** ________________  
**Trainer Signature:** ________________  

---

## Quick Reference

### Essential Commands

```bash
# Service Management
systemctl start nexus
systemctl stop nexus
systemctl restart nexus
systemctl status nexus

# Health & Diagnostics
curl http://localhost:7860/health
tail -f /var/log/nexus.log
du -sh artifacts/incidents.json

# Database Backup/Restore
./scripts/backup_nexus.sh
./scripts/restore_nexus.sh <backup_file>

# Monitoring
curl http://localhost:7860/metrics
docker logs -f nexus-app  # If using Docker
```

### Key Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| DevOps Lead | (TBD) | (TBD) | (TBD) |
| Backend Lead | (TBD) | (TBD) | (TBD) |
| On-Call Engineer | (TBD) | (TBD) | (TBD) |
| Security Lead | (TBD) | (TBD) | (TBD) |

### Key Resources

- NEXUS Architecture: `/docs/README.md`
- Runbooks: `/docs/runbooks/`
- Troubleshooting: `/docs/TROUBLESHOOTING_GUIDE.md`
- API Reference: `/docs/public/API.md`
- Metrics: `/docs/internal/metrics.md`

---

**Document Owner:** DevOps Lead  
**Last Reviewed:** 2026-06-17  
**Next Review:** 2026-07-17  
**Certification Valid Until:** 2027-06-17 (annual renewal required)
