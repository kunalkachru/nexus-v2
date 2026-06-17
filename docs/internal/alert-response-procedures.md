# NEXUS Alert Response Procedures

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Audience:** On-Call Engineers, Production Support  
**Purpose:** Step-by-step procedures for responding to each alert type

---

## Overview

**When an alert fires during 24-hour monitoring:**
1. You get notified (Slack, PagerDuty, email)
2. Find the alert type in this document
3. Follow the step-by-step procedure
4. Document what happened in Issue Log
5. Return to normal monitoring

---

## Alert #1: Health Check Failing

### **Alert Name:** `ServiceDown`  
**Severity:** CRITICAL  
**Trigger:** Health endpoint returns error or doesn't respond  
**SLA:** Must respond within 5 minutes

### **Diagnosis (2 minutes)**

**Step 1:** Verify service is actually down
```bash
curl -v http://localhost:7860/health
# Should return: Connection refused OR timeout OR 500 error
```

**Step 2:** Check if Docker container is running
```bash
docker ps | grep nexus
# If not in list → service stopped
# If in list → service running but not responding
```

**Step 3:** Check service status
```bash
systemctl status nexus
# OR
docker logs -n 20 nexus-prod
# Look for: errors, panic, database errors
```

### **Resolution (5-10 minutes)**

**If container not running:**
```bash
docker start nexus-prod
sleep 10
curl http://localhost:7860/health
# If health returns → RESOLVED
# If still fails → continue to "Database Issues" section
```

**If container running but not responding:**
```bash
docker logs nexus-prod | tail -50
# Look for error type:

# Case A: Database error
# → Follow "Alert #7: Database Errors"

# Case B: Port already in use
# docker ps | grep 7860
# Kill the conflicting process, restart NEXUS

# Case C: Startup error
# → Check error message, may need rollback
```

### **If Can't Resolve in 10 Minutes**

1. Stop trying to fix
2. Escalate to **Backend Lead** immediately
3. Provide:
   - Full docker logs output
   - Error messages
   - Steps already attempted
4. Meanwhile: Prepare rollback (see Deployment Rollback Procedures)

### **Post-Resolution**

- [ ] Health check confirmed passing
- [ ] Monitor for 5 minutes (ensure it doesn't fail again)
- [ ] Document in Issue Log:
  - Time detected
  - Root cause
  - Resolution applied
  - How long to fix (TTR)
  - Prevention measure

---

## Alert #2: Metrics Collection Gap

### **Alert Name:** `MetricsNotCollecting`  
**Severity:** MEDIUM  
**Trigger:** Prometheus hasn't scraped metrics in 30+ seconds  
**SLA:** Must respond within 10 minutes

### **Diagnosis (3 minutes)**

**Step 1:** Check Prometheus target status
```bash
curl -s http://localhost:9090/api/v1/targets | jq .data.activeTargets
# Look for NEXUS target, check "health" field: UP or DOWN
```

**Step 2:** Check if metrics endpoint responding
```bash
curl -s http://localhost:7860/metrics | head -10
# Should show prometheus format metrics (nexus_...)
# If blank or error → endpoint problem
# If has data → scraping problem
```

**Step 3:** Check Prometheus scrape config
```bash
cat prometheus/prometheus.yml | grep -A 5 "nexus"
# Verify: correct job_name, correct targets address:port
```

### **Resolution (5-10 minutes)**

**If NEXUS metrics endpoint not responding:**
- This is part of the service problem
- Follow "Alert #1: Health Check Failing"

**If NEXUS responding but Prometheus shows DOWN:**
```bash
# Fix 1: Verify network connectivity
ping localhost
curl -s http://localhost:7860/metrics | wc -l
# If > 10 lines → metrics available

# Fix 2: Restart Prometheus
docker restart prometheus
sleep 5
curl -s http://localhost:9090/api/v1/targets
# Check status changed to UP

# Fix 3: Check scrape interval
# Prometheus default is 15 seconds
# If last scrape > 30 seconds ago, something is wrong
# Restart both services
docker restart nexus-prod prometheus
sleep 10
```

**If Still Not Collecting:**
- Escalate to **DevOps Lead**
- Check Prometheus logs: `docker logs prometheus`
- May need to reconfigure scrape targets

### **Post-Resolution**

- [ ] Metrics endpoint confirmed responding
- [ ] Prometheus target showing UP
- [ ] Recent data points visible in Prometheus
- [ ] Document in Issue Log

---

## Alert #3: High Auth Failure Rate

### **Alert Name:** `HighAuthFailureRate`  
**Severity:** MEDIUM  
**Trigger:** > 5 auth failures in 10 minutes  
**SLA:** Must respond within 15 minutes

### **Diagnosis (5 minutes)**

**Step 1:** Check current auth failure rate
```bash
tail -200 /var/log/nexus.log | grep -i "auth" | grep -i "fail" | wc -l
# How many failures in last ~5 minutes of logs?
```

**Step 2:** Look at actual failure messages
```bash
tail -200 /var/log/nexus.log | grep -i "auth" | grep -i "fail" | head -10
# What's the actual error? (expired token? invalid? revoked?)
```

**Step 3:** Check if it's widespread or isolated
```bash
# Check request rate
curl -s http://localhost:7860/metrics | grep requests_total

# If high request volume + normal failure rate → OK
# If normal volume + high failures → issue with auth
```

### **Resolution (10-20 minutes)**

**If isolated incident (only a few requests):**
- This is normal (some clients always send bad tokens)
- Monitor: if rate stays < 1/hour, no action needed
- Only alert if sustained > 5 per 10 min

**If legitimate spike:**
```bash
# Possibilities:
# 1. Auth service/token provider is down
#    → Check if auth dependency is healthy
#    → If external: escalate to that team
#
# 2. Tokens were revoked in bulk
#    → Inform customers to re-authenticate
#    → Expected behavior
#
# 3. Token validation changed
#    → Check recent code changes (git log)
#    → May need rollback
```

**If can't determine cause:**
- Escalate to **Backend Lead**
- Provide: error messages, failure count, when it started
- May need to check auth service logs

### **Post-Resolution**

- [ ] Auth failure rate dropped below 1/hour
- [ ] Monitor for 30 minutes to confirm stable
- [ ] Determine if customer action needed (re-auth)
- [ ] Document in Issue Log

---

## Alert #4: High Processing Latency

### **Alert Name:** `HighProcessingLatency`  
**Severity:** MEDIUM  
**Trigger:** Incident processing latency > 25% above baseline  
**SLA:** Must respond within 15 minutes

### **Diagnosis (5 minutes)**

**Step 1:** Check current latency
```bash
curl -s http://localhost:7860/metrics | grep incident_processing_duration
# Compare to baseline from Task 7.2: _______________ ms

# If increased > 25%: alert justified
# If increased < 25%: likely normal variance, monitor
```

**Step 2:** Check if it's growing over time
```bash
# Check Grafana: Performance Dashboard → "Processing Duration" panel
# Is latency stable at new level or continuing to grow?
```

**Step 3:** Identify what's slow
```bash
# Logs may show which stage is slow (PRISM, REPLICA, TRACE, FORGE, GUARDIAN)
tail -100 /var/log/nexus.log | grep -i "duration\|latency"

# Check if it's consistent or intermittent
```

### **Resolution (10-20 minutes)**

**If steady increase (degrading):**
- Likely: Database getting slower as it grows
- Check database size:
  ```bash
  du -h artifacts/incidents.json
  # Is it growing as expected? (1-2MB per hour during load)
  ```
- Likely cause: Normal (database operations inherently slower with more data)
- Mitigation: Monitor and document trend

**If sudden spike:**
- Check if coincides with other event (backup? high load?)
- Check system resources:
  ```bash
  top -b -n 1
  # CPU, memory, disk usage
  ```
- If resources constrained: that's the issue
- If resources OK: may be query performance issue

**If consistently high:**
- Could indicate inefficient queries
- Escalate to **Backend Lead** for query optimization review

### **Post-Resolution**

- [ ] Latency stable (even if higher than pre-prod)
- [ ] Customer impact assessed (is it noticeable?)
- [ ] Trend documented (is it continuing to degrade?)
- [ ] Document in Issue Log

---

## Alert #5: GUARDIAN Approval Rate Dropped

### **Alert Name:** `GuardianApprovalRateLow`  
**Severity:** LOW  
**Trigger:** Approval rate < baseline OR decisions pending > threshold  
**SLA:** Must respond within 30 minutes

### **Diagnosis (5 minutes)**

**Step 1:** Check GUARDIAN decision rate
```bash
curl -s http://localhost:7860/metrics | grep guardian_decisions_total
# Compare approve vs. reject vs. pending

# Normal: mostly approvals (80-90%), some rejects (5-10%)
```

**Step 2:** Check if decisions are being made
```bash
# Are there incidents pending review?
curl -H "Authorization: Bearer test" http://localhost:7860/api/incidents?status=pending_review
# If many → decisions not being made (concerning)
# If few → normal, may just be lower volume
```

**Step 3:** Check GUARDIAN service status
```bash
# Is GUARDIAN responding?
# Check logs for GUARDIAN errors
tail -50 /var/log/nexus.log | grep -i guardian
```

### **Resolution (10-30 minutes)**

**If incidents pending (decisions not being made):**
- Check if GUARDIAN UI is accessible
- Check if users have access rights
- May be a blocking issue preventing decisions
- Escalate to **Backend Lead** if prolonged (> 1 hour)

**If approval rate just lower:**
- This may be normal variance
- Could be incident types are harder to approve today
- Only alert if consistently below baseline for > 2 hours

**If rate dropping over time:**
- Trend is concerning
- May indicate growing issue
- Escalate for investigation

### **Post-Resolution**

- [ ] Decisions resuming (if they were stuck)
- [ ] Approval rate returning toward baseline
- [ ] No pending incidents stuck in review
- [ ] Document in Issue Log

---

## Alert #6: High Persistence Latency

### **Alert Name:** `HighPersistenceLatency`  
**Severity:** MEDIUM  
**Trigger:** Artifact save latency > 200ms  
**SLA:** Must respond within 15 minutes

### **Diagnosis (5 minutes)**

**Step 1:** Check current persistence latency
```bash
curl -s http://localhost:7860/metrics | grep artifact_persistence_latency_ms
# Baseline from pre-prod: _______________ ms
# Alert threshold: 200ms
# If current > 200ms: alert justified
```

**Step 2:** Check database performance
```bash
# Database file size (growing file = slower writes)
du -h artifacts/incidents.json

# Database I/O: check if disk is saturated
iostat -x 1 5
# Look for %util (utilization) and avgqu-sz (queue)
```

**Step 3:** Check system resources
```bash
top -b -n 1
# Memory available
# CPU usage
# Disk space remaining
```

### **Resolution (10-20 minutes)**

**If database file large (> 10MB):**
- This is expected and normal
- Larger databases have slower writes
- Latency degradation is acceptable if not > 500ms
- Monitor for trend (is it continuing to degrade?)

**If disk I/O high:**
- Database writes are competing with other I/O
- Check if backup is running (backup causes I/O)
- If backup: this is temporary, will pass
- If not backup: escalate (may indicate issue)

**If memory/CPU constrained:**
- System resources are the bottleneck
- May need to reduce load or increase resources
- Escalate to **DevOps Lead**

### **Post-Resolution**

- [ ] Persistence latency stable (even if higher)
- [ ] No exponential degradation trend
- [ ] Acceptable for SLA (< 500ms)
- [ ] Document in Issue Log

---

## Alert #7: Unexpected Errors in Logs

### **Alert Name:** `ErrorsInLogs` (or specific error alert)  
**Severity:** MEDIUM-HIGH (depends on error type)  
**Trigger:** Any ERROR log entry  
**SLA:** Must investigate within 10 minutes

### **Diagnosis (3 minutes)**

**Step 1:** Find the error
```bash
tail -50 /var/log/nexus.log | grep ERROR
# What's the exact error message?
```

**Step 2:** Categorize the error
```
Common error categories:
- Database errors (connection, I/O, corruption)
- Auth errors (token validation, service unavailable)
- Persistence errors (file write, JSON parse)
- Replay errors (sandbox issues, timeout)
- API errors (invalid request, 500 response)
```

**Step 3:** Check if it's recurring
```bash
grep "ERROR" /var/log/nexus.log | grep -i "[error_keyword]" | wc -l
# Is this error appearing once or many times?
```

### **Resolution (5-15 minutes)**

**Action depends on error type. Examples:**

**If "Database connection error":**
- Follow Alert #8 procedures (database corrupted)

**If "JSON parse error":**
- Database may be corrupted
- Stop service and restore from backup

**If "Timeout" error:**
- Service is overloaded or slow
- Check CPU/memory
- May indicate load issue

**If "Permission denied" error:**
- File or directory permissions issue
- Fix permissions: `chmod 644 artifacts/incidents.json`

**If "Unknown error":**
- Search error message online or in code
- Escalate to **Backend Lead** with error details

### **Post-Resolution**

- [ ] Error stopped appearing in logs
- [ ] No new instances of same error
- [ ] Root cause identified
- [ ] Prevention measure identified
- [ ] Document in Issue Log

---

## Alert #8: Backup Job Failed

### **Alert Name:** `BackupFailed`  
**Severity:** HIGH  
**Trigger:** Backup job didn't complete or produced invalid file  
**SLA:** Must respond within 30 minutes

### **Diagnosis (5 minutes)**

**Step 1:** Check backup log
```bash
tail -50 /var/log/nexus-backup.log
# What's the error message from backup script?
```

**Step 2:** Check if backup file exists
```bash
ls -lh .backup/nexus/ | tail -5
# Is there a recent backup file?
# What's its size?
```

**Step 3:** Check if backup is valid
```bash
LATEST=$(ls -t .backup/nexus/*.gz 2>/dev/null | head -1)
gzip -t "$LATEST"
# If no error: backup is valid
# If error: backup file corrupted
```

### **Resolution (15-30 minutes)**

**If backup file doesn't exist:**
- Backup script didn't run
- Check if cron job is configured:
  ```bash
  crontab -l | grep backup
  # If nothing: cron job not set up
  # If exists: check if it's scheduled for future (not now)
  ```
- Manually run backup:
  ```bash
  ./scripts/backup_nexus.sh
  # Check for errors
  ```

**If backup file is corrupted:**
- Likely issue during write
- Retry backup: `./scripts/backup_nexus.sh`
- If fails again: escalate to **DevOps Lead**

**If backup took too long:**
- Large database may take time
- If taking > 5 minutes: expected but monitor
- If taking > 30 minutes: may indicate I/O issue

**If S3 upload failed (if configured):**
- Check AWS credentials
- Check network connectivity: `ping s3.amazonaws.com`
- Check S3 bucket accessible: `aws s3 ls s3://nexus-backups`
- May need to reconfigure AWS CLI

### **Post-Resolution**

- [ ] Backup file exists and is valid
- [ ] At least one valid backup in `.backup/nexus/`
- [ ] Cron job configured (if using scheduled backups)
- [ ] Can restore from backup if needed (verify)
- [ ] Document in Issue Log

---

## General Escalation Criteria

**Escalate to Backend Lead if:**
- Any database errors
- Persistent latency issues
- Unexpected behavior in GUARDIAN
- Any logic error (not just infrastructure)

**Escalate to DevOps Lead if:**
- Infrastructure issues (disk, CPU, memory)
- Container/Docker issues
- Backup/restore issues
- Monitoring/metrics issues

**Escalate to Engineering Manager if:**
- Multiple critical issues
- Customer-facing outage > 30 minutes
- Cascading failures
- Data loss or corruption
- Any CRITICAL severity alert

---

## Post-Alert Checklist

**For EVERY alert that fires:**

- [ ] Alert received and acknowledged
- [ ] Diagnosis completed (< 10 min)
- [ ] Resolution attempted (< 30 min)
- [ ] Issue resolved or escalated
- [ ] Issue logged in Issue Log (with timeline)
- [ ] Root cause identified
- [ ] Prevention measure documented
- [ ] Monitoring confirmed stable
- [ ] No new incidents from same issue

---

## Quick Reference Table

| Alert | Severity | Response Time | If Unresolved |
|-------|----------|---------------|---------------|
| Health Check Failing | CRITICAL | 5 min | Escalate immediately |
| Metrics Gap | MEDIUM | 10 min | Escalate in 15 min |
| High Auth Failures | MEDIUM | 15 min | Escalate in 30 min |
| High Processing Latency | MEDIUM | 15 min | Escalate in 30 min |
| GUARDIAN Rate Low | LOW | 30 min | Escalate in 60 min |
| High Persistence Latency | MEDIUM | 15 min | Escalate in 30 min |
| Errors in Logs | MEDIUM | 10 min | Escalate in 20 min |
| Backup Failed | HIGH | 30 min | Escalate immediately |

---

**Document Owner:** Production Support Lead  
**Last Updated:** 2026-06-17  
**Next Review:** Post-deployment (48 hours)
