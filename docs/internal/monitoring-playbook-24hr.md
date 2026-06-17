# NEXUS 24-Hour Production Monitoring Playbook

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Audience:** On-Call Engineers, Production Monitoring Team  
**Duration:** 24 hours post-deployment  
**Objective:** Prove NEXUS is stable and production-ready

---

## Overview

This playbook is your **minute-by-minute guide** for the 24-hour monitoring period immediately after production deployment (Task 8.2).

**Your Role:** Watch the service continuously. Respond to any alerts. Document everything.

**Success Criteria:** 24 hours with no unresolved critical issues, all 8 metrics stable, customer satisfied.

---

## Pre-Monitoring Checklist (Before Hour 0)

**Complete before starting 24-hour watch:**

- [ ] Read this entire playbook
- [ ] Access to Grafana dashboards: `http://localhost:3000`
- [ ] Access to Prometheus metrics: `http://localhost:9090`
- [ ] Access to service logs: `docker logs -f nexus-prod` or `tail -f /var/log/nexus.log`
- [ ] Access to alert notification system (Slack, PagerDuty, email)
- [ ] Printed copy of this playbook and alert-response-procedures.md
- [ ] Coffee/water for 24 hours ☕
- [ ] Backup on-call engineer contact info
- [ ] Backend engineer escalation contact info
- [ ] Customer contact info (for updates if issues arise)

**Shift Start Time:** _________________  
**On-Call Engineer Name:** _________________  
**Backup Contact:** _________________  

---

## The 8 Metrics You're Watching

### Metric 1: Health Check Status
**What:** `GET /health` returns `{"status": "ok"}`  
**Normal:** Responds within 100ms, always "ok"  
**Warning Signs:**
- Response time > 500ms (slow)
- Returns error status
- No response (service down)
- Connection refused (port issue)

**Check Every:** 5 minutes  
**How to Check:**
```bash
curl -s http://localhost:7860/health | jq .
```

**Expected Output:**
```json
{"status": "ok", "timestamp": "2026-06-17T10:00:00Z", "db_size": "2.8 MB"}
```

---

### Metric 2: Metrics Collection (No Gaps)
**What:** Prometheus is collecting metrics continuously from NEXUS  
**Normal:** New data points every 10-15 seconds  
**Warning Signs:**
- Gap > 30 seconds in metric data
- Prometheus scrape target shows "DOWN"
- Metrics endpoint (`/metrics`) returns error
- Time since last scrape > 2 minutes

**Check Every:** 10 minutes  
**How to Check:**
```bash
# 1. Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets

# 2. Check most recent metrics
curl -s http://localhost:7860/metrics | head -20

# 3. Check Prometheus query (should have recent data)
curl -s 'http://localhost:9090/api/v1/query?query=nexus_incidents_created_total'
```

**Expected:** Last data point within 30 seconds

---

### Metric 3: Auth Failure Rate
**What:** Authentication failures (invalid tokens, expired tokens, etc.)  
**Normal:** < 1 failure per hour  
**Warning Signs:**
- > 5 failures in 10 minutes
- Sudden spike in auth failures
- All requests failing with auth errors
- Auth service unavailable

**Check Every:** 30 minutes  
**How to Check:**
```bash
# From logs
tail -100 /var/log/nexus.log | grep -i auth | grep -i fail | wc -l

# From Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=auth_failures_total'
```

**Baseline (from pre-prod):** _________________ failures/hour

---

### Metric 4: Incident Processing Latency
**What:** Time to process incident from intake → output  
**Normal:** Stable, matching pre-production baseline  
**Warning Signs:**
- Latency increased > 25% from baseline
- P95 latency > 200ms (if baseline was < 100ms)
- Individual incidents taking > 5 seconds
- Processing slowing down over time

**Check Every:** 15 minutes  
**How to Check:**
```bash
# Grafana: Go to Performance Dashboard, check "Processing Duration"
# Look for p50, p95, p99 latencies

# Prometheus directly
curl -s 'http://localhost:9090/api/v1/query?query=incident_processing_duration_seconds'
```

**Baseline (from Task 7.2 load test):** _________________ ms

---

### Metric 5: GUARDIAN Approval Rate
**What:** Percentage of incidents approved (vs. rejected/pending) by GUARDIAN  
**Normal:** Matches pre-production baseline  
**Warning Signs:**
- Approval rate dropped > 10%
- Rejection rate increased suddenly
- Pending reviews piling up (not being decided)
- GUARDIAN decision times increased

**Check Every:** 30 minutes  
**How to Check:**
```bash
# From Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=guardian_decisions_total'

# Count by decision type
curl -s http://localhost:7860/metrics | grep guardian_decisions | head -5
```

**Baseline (from pre-prod):** _________________ % approval rate

---

### Metric 6: Artifact Persistence Latency
**What:** Time to save incident to database  
**Normal:** < 100ms consistently  
**Warning Signs:**
- Latency > 200ms
- Growing latency over 24 hours (database slowing)
- P95/P99 > 500ms
- Database file growing unexpectedly

**Check Every:** 15 minutes  
**How to Check:**
```bash
# Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=artifact_persistence_latency_ms'

# Check database file size
du -h artifacts/incidents.json

# Check if database growing as expected
ls -lh artifacts/incidents.json | awk '{print $5, $6, $7, $8, $9}'
```

**Baseline (from pre-prod):** _________________ ms  
**Expected Size After 24h:** _________________ MB

---

### Metric 7: Unexpected Errors in Logs
**What:** ERROR or CRITICAL log entries (not expected)  
**Normal:** 0-2 errors in 24 hours (normal startup messages OK)  
**Warning Signs:**
- Any recurring ERROR message
- Any CRITICAL message
- Errors related to: database, auth, persistence, replay
- Error rate increasing over time

**Check Every:** 30 minutes  
**How to Check:**
```bash
# Docker logs
docker logs nexus-prod 2>&1 | grep -i error | tail -20

# OR system logs
tail -100 /var/log/nexus.log | grep -i error

# Count errors
docker logs nexus-prod 2>&1 | grep -i error | wc -l
```

**Expected:** 0-2 errors in entire 24-hour period

---

### Metric 8: Backup Running Successfully
**What:** Automated backup job runs and succeeds  
**Normal:** Backup completes every 6 hours  
**Warning Signs:**
- Backup job failed to run
- Backup file is empty or corrupted
- No backups in `.backup/nexus/` directory
- Backup size smaller than expected

**Check Every:** 60 minutes  
**How to Check:**
```bash
# Check backup directory
ls -lh .backup/nexus/ | tail -5

# Check most recent backup
LATEST=$(ls -t .backup/nexus/*.gz 2>/dev/null | head -1)
gzip -t "$LATEST" && echo "Latest backup is valid" || echo "Backup corrupted"

# Check backup log
tail -20 /var/log/nexus-backup.log
```

**Expected:** At least one backup every 6 hours, all valid gzip files

---

## Hour-by-Hour Monitoring Schedule

### **Hour 0 (Deployment Time)**

**Start Time:** _________________

**Tasks:**
- [ ] Record start time and baseline metrics
- [ ] Verify all 8 metrics are green
- [ ] Check health endpoint manually
- [ ] Take screenshot of Grafana dashboards
- [ ] Verify logs have no errors
- [ ] Verify backups are scheduled/running

**Baseline Metrics Recording:**

| Metric | Baseline Value | Recorded At |
|--------|----------------|-------------|
| Health Status | | |
| Metrics Collection | | |
| Auth Failure Rate | | |
| Processing Latency | | |
| GUARDIAN Approval % | | |
| Persistence Latency | | |
| Error Count | | |
| Backup Status | | |

**Any Issues?** [ ] No [ ] Yes → Document in Issue Log (see end of playbook)

**Shift Checkpoint:** All systems nominal, monitoring begins

---

### **Hours 1-6 (Active Monitoring - Frequent Checks)**

**Check Frequency:** Every 10-15 minutes

**Checklist Each Check:**
- [ ] Health check passing
- [ ] No new alert notifications
- [ ] Metrics still flowing (not stale)
- [ ] No new error log entries
- [ ] Database file growing at expected rate
- [ ] Response times stable

**What to Do if Alert Fires:**
1. Record exact time: _________________
2. Check which metric triggered: _________________
3. Open Alert Response Runbook (alert-response-procedures.md)
4. Follow the procedure for that alert
5. Document resolution in Issue Log

**Status Update to Customer (if anything unusual):**
```
"We're monitoring NEXUS in production as part of standard deployment 
validation. Current status: [NORMAL/INVESTIGATING/RESOLVED]. 
We'll update you hourly or if any action is needed. Thank you for your patience."
```

**Checkpoint at Hour 6:**
- [ ] 6 hours elapsed
- [ ] All 8 metrics stable
- [ ] No unresolved critical issues
- [ ] Document any issues encountered

---

### **Hours 7-18 (Sustained Monitoring - Regular Checks)**

**Check Frequency:** Every 30 minutes

**Checklist Each Check:**
- [ ] Health status unchanged
- [ ] Metrics collection continuous (no gaps)
- [ ] Processing latency stable (not degrading)
- [ ] Error count low (< 1 new error)
- [ ] Backup completed since last check (if applicable)

**What to Do if Performance Degrades:**
1. Check if degradation is gradual or sudden
2. Look for correlating events (backup job? metrics collection spike?)
3. If gradual, it may be normal (database growth, more data)
4. If sudden, investigate root cause immediately
5. Document in Issue Log

**Shift Handoff (if changing on-call engineers):**
- [ ] Outgoing engineer briefs incoming engineer
- [ ] Review Issue Log so far
- [ ] Review metric trends over past 6-12 hours
- [ ] Confirm all contact info
- [ ] Incoming engineer acknowledges readiness

**Checkpoint at Hour 12 (Halfway Point):**
- [ ] 12 hours elapsed
- [ ] All 8 metrics stable
- [ ] No unresolved issues
- [ ] Backup has run at least once (6-hour interval)
- [ ] Customer satisfaction confirmed

---

### **Hours 19-24 (Final Monitoring - Frequent Again)**

**Check Frequency:** Every 15 minutes

**Rationale:** As we approach end of 24 hours, increase vigilance. Any issues now need to be documented for postmortem.

**Checklist Each Check:**
- [ ] Health stable
- [ ] All metrics nominal
- [ ] No last-minute errors
- [ ] Database final size recorded
- [ ] Backup status confirmed

**Final Hour Procedures (Hour 23-24):**

At Hour 23:
- [ ] Prepare final metrics report
- [ ] Start drafting postmortem (if any issues)
- [ ] Verify customer satisfaction

At Hour 24:
- [ ] Record final metrics
- [ ] Take final Grafana screenshot
- [ ] Summarize Issue Log
- [ ] Declare monitoring complete
- [ ] Hand off to Task 8.3 (Ops Handoff)

**Checkpoint at Hour 24 (Final):**
- [ ] 24 hours completed
- [ ] All 8 metrics stable throughout
- [ ] All issues documented and resolved
- [ ] Customer satisfied
- [ ] Ready for Ops Handoff (Task 8.3)

**End Time:** _________________  
**Total Duration:** 24 hours (should equal 24h ± 5min)  
**Status:** PASSED / FAILED  

---

## Issue Logging Template

Use this for EVERY issue encountered, no matter how small:

```
================================================================================
ISSUE #: [1, 2, 3, ...]
TIME DISCOVERED: [HH:MM UTC]
METRIC AFFECTED: [Health / Metrics / Auth / Latency / GUARDIAN / Persistence / Errors / Backup]
SEVERITY: [LOW / MEDIUM / HIGH / CRITICAL]
================================================================================

WHAT HAPPENED:
[Describe symptom. What did you observe?]

TIMELINE:
- [HH:MM] [What happened]
- [HH:MM] [What you did]
- [HH:MM] [Result]

ROOT CAUSE:
[Why did it happen?]

RESOLUTION:
[How was it fixed? By whom? What time?]

TIME TO RESOLVE (TTR):
[Time from discovery to resolution]

IMPACT:
[Did this affect customers? How many? For how long?]

PREVENTION:
[How to prevent this in future?]

OWNER: [Name]
STATUS: RESOLVED / ESCALATED
DATE RESOLVED: [Date]

================================================================================
```

---

## Baseline Comparison Throughout 24 Hours

**Use this to track if metrics are drifting:**

| Hour | Health | Metrics | Auth | Latency | GUARDIAN | Persistence | Errors | Backup |
|------|--------|---------|------|---------|----------|-------------|--------|--------|
| 0 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 9 | | | | | | | | |
| 12 | | | | | | | | |
| 15 | | | | | | | | |
| 18 | | | | | | | | |
| 21 | | | | | | | | |
| 24 | | | | | | | | |

**Legend:** ✓ = Nominal | ⚠ = Warning | ✗ = Alert

---

## Contact Information

### On-Call Team

| Role | Name | Email | Phone | Availability |
|------|------|-------|-------|--------------|
| Primary On-Call | | | | |
| Secondary On-Call | | | | |
| Backup | | | | |

### Escalation Contacts

| Role | Name | Email | Phone | When to Contact |
|------|------|-------|-------|-----------------|
| Backend Lead | | | | Database/latency issues |
| DevOps Lead | | | | Infrastructure/deployment issues |
| Engineering Manager | | | | Critical issues/customer impact |

### Customer Contacts

| Contact | Name | Email | Phone | Role |
|---------|------|-------|-------|------|
| Primary | | | | |
| Backup | | | | |

---

## Emergency Procedures

### If Service Goes Down (Health Check Fails)

1. **Immediate:** Check if service is running
   ```bash
   docker ps | grep nexus-prod
   systemctl status nexus
   ```

2. **If Not Running:** Try restart
   ```bash
   docker restart nexus-prod
   # Wait 10 seconds
   curl http://localhost:7860/health
   ```

3. **If Still Down:** Check logs for errors
   ```bash
   docker logs nexus-prod | tail -50
   # Look for: database errors, port conflicts, permission errors
   ```

4. **If Can't Fix Locally:** Escalate to Backend Lead
   - Provide: error message, attempted fixes, current status
   - Provide: database file status, recent log entries

5. **Last Resort:** Rollback (see Rollback Procedures)

### If Database Corrupted (JSON Parse Error)

1. **Immediate:** Stop writes to database
   ```bash
   docker stop nexus-prod
   ```

2. **Check Backup:** Is latest backup valid?
   ```bash
   LATEST=$(ls -t .backup/nexus/*.gz | head -1)
   gzip -t "$LATEST" && echo "Valid" || echo "Corrupted"
   ```

3. **Restore from Backup:**
   ```bash
   ./scripts/restore_nexus.sh "$LATEST"
   ```

4. **Verify Restored Data:**
   ```bash
   curl http://localhost:7860/health
   docker logs nexus-prod | tail -20
   ```

5. **Document:** What caused corruption? How to prevent?

### If Metrics Stop Flowing

1. **Check Prometheus Target:**
   ```bash
   curl http://localhost:9090/api/v1/targets
   # Look for NEXUS target status: UP or DOWN
   ```

2. **If DOWN:** Check if metrics endpoint responding
   ```bash
   curl http://localhost:7860/metrics | head -5
   ```

3. **If Not Responding:** Service issue (see "Service Goes Down")

4. **If Responding but DOWN in Prometheus:** Check Prometheus config
   ```bash
   cat prometheus/prometheus.yml
   # Verify scrape config points to correct address:port
   ```

### If Alerts Keep Firing

1. **Read Alert Response Runbook** for that specific alert
2. **Apply Fix** from runbook
3. **If Fix Fails:** Document and escalate to Backend Lead
4. **If Fix Works:** Document what was wrong and how it was fixed

---

## End-of-24-Hour Deliverables

**You must provide:**

- [ ] **Issue Log:** All issues found, documented with timestamps
- [ ] **Postmortem (if issues):** Root causes, resolutions, prevention
- [ ] **Metrics Summary:** 
  - Start baseline vs. end state for all 8 metrics
  - Any degradation noted?
  - Any concerning trends?
- [ ] **Logs Capture:** 
  - All ERROR/WARNING log entries (if any)
  - Backup job log showing successful runs
- [ ] **Customer Communication:**
  - Status updates sent (if any issues)
  - Final satisfaction confirmation
- [ ] **Sign-Off Form:**
  - Monitoring completed successfully: YES / NO
  - Ready for Ops Handoff: YES / NO
  - Escalations needed: YES / NO (if yes, list them)

---

## Success Criteria (Monitoring is "Green" When)

- ✅ 24 hours completed
- ✅ All 8 metrics stable throughout
- ✅ 0-2 unplanned issues (minor, resolved)
- ✅ 0 critical issues
- ✅ 0 unresolved issues at end
- ✅ All backups successful
- ✅ Customer satisfied
- ✅ Documentation complete
- ✅ Escalations (if any) handled and documented

---

**Document Owner:** Production Monitoring Lead  
**Last Updated:** 2026-06-17  
**Next Review:** Post-production (within 48 hours of deployment)
