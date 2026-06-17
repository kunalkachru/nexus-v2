# Monthly Disaster Recovery Drill

**Runbook ID:** DR-DRILL-001  
**Last Updated:** 2026-06-17  
**Audience:** DevOps Team, On-Call Engineers  
**Severity:** MEDIUM (scheduled, no prod impact)  

---

## Overview

The monthly NEXUS Disaster Recovery (DR) drill validates that our backup and restore procedures work reliably in a controlled environment. This drill is scheduled for the **first Monday of each month** and must complete within the designated maintenance window.

**Goals:**
- Verify backup integrity and completeness
- Test restore procedure end-to-end
- Measure Recovery Time Objective (RTO) — target: < 1 hour
- Validate all incident data recovery
- Identify process improvements before a real incident

---

## Before the Drill

### 1. Schedule & Communication (1 week before)

- [ ] Schedule drill for first Monday 2:00 AM UTC (adjust for your timezone)
- [ ] Post drill calendar event to team
- [ ] Notify all stakeholders (dev, ops, security, product)
- [ ] Confirm at least 2 people available for drill execution
- [ ] Backup any temporary work/scripts that might be lost during simulated corruption

### 2. Prepare Test Environment

- [ ] Confirm you have a non-production environment (staging or local)
- [ ] If using production data:
  - [ ] Make a manual backup of current artifacts/incidents.json
  - [ ] Store securely in a separate location
- [ ] Document current incident count: **___ incidents**
- [ ] Document current database size: **___ MB**
- [ ] Verify S3/backup storage has recent backups available

### 3. Preparation Checklist (1 day before)

- [ ] Review this runbook
- [ ] Review latest restore_nexus.sh script
- [ ] Verify restore script has execute permissions: `chmod +x scripts/restore_nexus.sh`
- [ ] List available backups: `ls -lh .backup/nexus/` or query S3
- [ ] Select the backup to restore (usually the most recent)
- [ ] Verify backup file is readable and not corrupted: `gzip -t <backup_file>`
- [ ] Clear /var/log/nexus-restore.log or establish new log location
- [ ] Test health check endpoint: `curl http://localhost:7860/health`
- [ ] Prepare communication channels (Slack, email) for drill status updates

---

## Drill Execution (Day-of, ~1 hour)

### Phase 1: Start Drill (5 minutes)

**01:00 - Start Time**

- [ ] Post "DR Drill Starting" message to #incidents or team Slack channel
- [ ] Start timer (use stopwatch app or record start time)
- [ ] Verify all participants are ready
- [ ] Take screenshot of current system state (uptime, health check passing)

**Record Start Time:** `_______` (HH:MM UTC)

### Phase 2: Simulate Corruption (10 minutes)

**01:05 - Simulate Database Corruption**

Choose ONE of these scenarios:

**Option A: Simulate File Corruption**
```bash
# Backup current production file
cp artifacts/incidents.json artifacts/incidents.json.prebreach

# Simulate corruption (overwrite first 100 bytes)
dd if=/dev/zero of=artifacts/incidents.json bs=1 count=100 conv=notrunc

# Verify NEXUS now shows errors when accessing incidents
curl http://localhost:7860/health
curl http://localhost:7860/api/incidents -H "Authorization: Bearer ..."
# Both should show errors or service unavailable
```

**Option B: Simulate Missing Database**
```bash
# Backup current file
cp artifacts/incidents.json artifacts/incidents.json.prebreach

# Remove database to simulate data loss
rm artifacts/incidents.json

# Verify NEXUS fails to load data
curl http://localhost:7860/api/incidents -H "Authorization: Bearer ..."
# Should return 500 or service unavailable
```

**Option C: Simulate Truncation**
```bash
# Backup current file
cp artifacts/incidents.json artifacts/incidents.json.prebreach

# Truncate file (simulate incomplete write)
> artifacts/incidents.json

# Verify NEXUS shows data loss
curl http://localhost:7860/api/incidents -H "Authorization: Bearer ..."
```

- [ ] Corruption applied successfully
- [ ] Verify NEXUS shows error when accessing incidents (403/404/500)
- [ ] Document which corruption scenario was used: **Option: ___**
- [ ] Screenshot showing error state

### Phase 3: Initiate Restore (5 minutes)

**01:15 - Begin Restore Process**

**Record Restore Start Time:** `_______` (HH:MM UTC)

```bash
# Step 1: Identify backup file
BACKUP_FILE=".backup/nexus/nexus_backup_20260617_120000.json.gz"
# Or retrieve from S3:
# aws s3 cp s3://nexus-backups/nexus_backup_20260617_120000.json.gz .

# Step 2: Verify backup integrity
gzip -t "$BACKUP_FILE"
echo "Backup integrity: $?"  # Should be 0

# Step 3: Run restore script
./scripts/restore_nexus.sh "$BACKUP_FILE"

# Step 4: Monitor restore progress
tail -f /var/log/nexus-restore.log
```

- [ ] Backup file located and verified
- [ ] Restore script executed without errors
- [ ] Backup integrity check: **PASSED / FAILED**
- [ ] Service restart completed
- [ ] Screenshot of successful restore log

**Record Restore End Time:** `_______` (HH:MM UTC)

### Phase 4: Verify Recovery (15 minutes)

**01:25 - Validate Restored Data**

```bash
# Step 1: Verify service is responding
curl http://localhost:7860/health
# Should return 200 OK with {"status": "ok"}

# Step 2: Query restored data
curl http://localhost:7860/api/incidents \
  -H "Authorization: Bearer your-token" | jq '.data | length'

# Step 3: Spot-check specific incidents
curl http://localhost:7860/api/incidents/nxs_INC001 \
  -H "Authorization: Bearer your-token" | jq .

# Step 4: Verify incident count matches pre-drill
# Expected: ___ incidents (from preparation checklist)
# Actual: ___ incidents

# Step 5: Check restore log for any warnings
tail -50 /var/log/nexus-restore.log | grep -i warning

# Step 6: Verify audit log shows restore event
tail -100 .nexus_audit_log.json | grep -i restore
```

- [ ] Health check: **PASSED**
- [ ] Service responding: **YES / NO**
- [ ] Incident count matches: **YES / NO** (pre: ___, post: ___)
- [ ] Spot-check incidents: **PASSED / FAILED**
- [ ] No critical warnings in restore log: **YES / NO**
- [ ] Restore event in audit log: **YES / NO**

**Record End-of-Verification Time:** `_______` (HH:MM UTC)

### Phase 5: Cleanup (5 minutes)

**01:45 - Post-Drill Cleanup**

```bash
# Step 1: Restore pre-breach backup if using production environment
cp artifacts/incidents.json.prebreach artifacts/incidents.json

# Or if using staging, just verify it's clean:
rm artifacts/incidents.json.prebreach

# Step 2: Verify production/staging data is back to normal
curl http://localhost:7860/api/incidents \
  -H "Authorization: Bearer your-token" | jq '.data | length'

# Step 3: Clear logs
: > /var/log/nexus-restore.log
```

- [ ] Original data restored (if used production): **YES / NO**
- [ ] Service verified healthy post-recovery: **YES / NO**
- [ ] Cleanup complete: **YES / NO**

### Phase 6: Post-Drill Report (10 minutes)

**01:55 - Document Results**

**Record Drill End Time:** `_______` (HH:MM UTC)

Calculate RTO:
- **Restore Start Time:** ___:___ UTC
- **Restore End Time:** ___:___ UTC
- **RTO (Recovery Time Objective):** ___ minutes
- **RTO Target:** < 60 minutes
- **RTO Status:** ✅ PASSED / ❌ FAILED

- [ ] RTO < 1 hour: **YES / NO**
- [ ] All incidents recovered: **YES / NO**
- [ ] No data corruption in restore: **YES / NO**
- [ ] Postmortem document started

---

## Post-Drill Postmortem

Use this template to document findings:

### Postmortem Header

| Field | Value |
|-------|-------|
| **Drill Date** | 2026-06-01 (first Monday) |
| **Drill Duration** | ___ minutes |
| **RTO Achieved** | ___ minutes |
| **Participants** | (names) |
| **Facilitator** | (name) |
| **Issues Found** | (count) |

### What Went Well ✅

- [ ] Backup file was available and uncorrupted
- [ ] Restore script ran without errors
- [ ] Service restarted cleanly
- [ ] All incident data recovered
- [ ] Health checks passed

Add any other wins:

```
- 
- 
- 
```

### Issues Found 🔴

| # | Issue | Severity | Owner | Resolution |
|---|-------|----------|-------|------------|
| 1 | Example: "Restore took 45 min, slow gzip decompression" | Medium | @ops | Investigate faster restore method |
| | | | | |
| | | | | |

### Action Items 📋

- [ ] Issue #1: (description) — Due: (date)
- [ ] Issue #2: (description) — Due: (date)
- [ ] Issue #3: (description) — Due: (date)

### Lessons Learned 💡

What should the team know for the next drill or real incident?

```
1. (Observation)
2. (Observation)
3. (Observation)
```

### Runbook Updates Required

- [ ] Update restore_nexus.sh with improvements
- [ ] Update this monthly-dr-drill.md runbook
- [ ] Update pre-flight checklist
- [ ] Update (other docs)

### Sign-Off

- **Drill Facilitator:** _________________ Date: _______
- **DevOps Lead:** _________________ Date: _______
- **On-Call Lead:** _________________ Date: _______

---

## Common Issues & Troubleshooting

### Issue: Restore Script Not Found

**Symptom:** `./scripts/restore_nexus.sh: command not found`

**Fix:**
```bash
chmod +x scripts/restore_nexus.sh
ls -la scripts/restore_nexus.sh  # Verify executable
./scripts/restore_nexus.sh <backup_file>
```

### Issue: Backup File Corrupted

**Symptom:** `Backup file is corrupted or not valid gzip`

**Fix:**
```bash
# Use an older backup
ls -lh .backup/nexus/ | sort -k6,7 -r  # Show newest first

# Try S3 backup
aws s3 ls s3://nexus-backups/ | sort  # Show available backups
aws s3 cp s3://nexus-backups/nexus_backup_20260617_120000.json.gz .
```

### Issue: Service Won't Start After Restore

**Symptom:** `curl http://localhost:7860/health` returns connection refused

**Fix:**
```bash
# Check service status
systemctl status nexus
# OR
docker logs nexus-app

# Verify database file exists and is readable
ls -la artifacts/incidents.json
chmod 644 artifacts/incidents.json

# Try manual restart
systemctl restart nexus
# OR
docker restart nexus-app

# Wait 10 seconds and retry health check
sleep 10
curl http://localhost:7860/health
```

### Issue: RTO Exceeded 1 Hour

**Symptom:** Restore + verification took > 60 minutes

**Action Items:**
- [ ] Identify bottleneck (gzip decompression? service startup? verification?)
- [ ] Consider faster compression (e.g., zstd instead of gzip)
- [ ] Consider restore to staging, then cutover (parallel restore + test)
- [ ] Document in next month's postmortem for optimization

---

## Monthly Schedule

| Month | Date | Facilitator | Status |
|-------|------|-------------|--------|
| June 2026 | 2026-06-01 | TBD | Pending |
| July 2026 | 2026-07-07 | TBD | Pending |
| August 2026 | 2026-08-04 | TBD | Pending |
| September 2026 | 2026-09-01 | TBD | Pending |

---

## Escalation

If the drill encounters critical issues:

1. **During Drill:** Post to #incidents or on-call channel immediately
2. **After Drill:** If RTO exceeded or data not recovered, escalate to DevOps Lead
3. **Post-Incident:** Schedule team meeting to review findings

**Escalation Contacts:**
- **DevOps Lead:** (contact info)
- **On-Call Lead:** (contact info)
- **Engineering Manager:** (contact info)

---

## Related Documentation

- [Backup Automation Script](../scripts/backup_nexus.sh)
- [Restore Procedure](../scripts/restore_nexus.sh)
- [Disaster Recovery Architecture](../disaster-recovery.md)
- [Alerting Rules](../prometheus/alerts.yml)

---

**Document Owner:** DevOps Team  
**Last Reviewed:** 2026-06-17  
**Next Review:** 2026-07-17
