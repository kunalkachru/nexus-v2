# Runbook: High Pending GUARDIAN Reviews Backlog

**Alert:** `PendingGuardianReviewsHigh`  
**Severity:** MEDIUM  
**On-Call Owner:** GUARDIAN Operations Team  
**Estimated Resolution Time:** 30-60 minutes (depends on backlog size)

---

## Symptoms

- Number of incidents awaiting GUARDIAN review >50 for >30 minutes
- Prometheus metric: `nexus_pending_guardian_reviews > 50`
- Users report slow incident approvals
- Incidents stuck in "pending_review" state
- GUARDIAN review latency increasing

---

## Immediate Actions (< 5 min)

1. **Assess backlog size**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM incidents 
     WHERE status='pending_review' AND created_at > datetime('now','-24 hours');"
   
   sqlite3 /path/to/nexus.db "SELECT status, COUNT(*) FROM incidents 
     GROUP BY status;"
   ```
   - How many are pending? How old are the oldest?

2. **Check if GUARDIAN review service is working**
   ```bash
   # If GUARDIAN is a separate service/queue
   curl -s https://guardian-api.company.com/status
   
   # Check for errors in last hour
   grep "guardian.*error\|review.*failed" /var/log/nexus/app.log | wc -l
   tail -50 /var/log/nexus/app.log | grep -i guardian
   ```

3. **Check if there's a submission spike**
   ```bash
   # Incidents created in last hour vs normal
   sqlite3 /path/to/nexus.db "SELECT DATE(created_at), COUNT(*) FROM incidents 
     WHERE created_at > datetime('now','-24 hours') 
     GROUP BY DATE(created_at) ORDER BY created_at DESC;"
   
   # If today >> yesterday: spike detected
   ```

4. **Check GUARDIAN review capacity**
   ```bash
   # How many reviews per hour can GUARDIAN process?
   sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM incidents 
     WHERE status IN ('approved','rejected') 
     AND created_at > datetime('now','-1 hour');"
   
   # If processing rate is very low: GUARDIAN is bottleneck
   ```

---

## If Immediate Actions Don't Work (5-20 min)

1. **Check if GUARDIAN is stuck or slow**
   ```bash
   # Review latency
   sqlite3 /path/to/nexus.db "SELECT 
     AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_review_time_seconds,
     MAX(EXTRACT(EPOCH FROM (updated_at - created_at))) as max_review_time_seconds
     FROM incidents WHERE status IN ('approved','rejected');"
   
   # If avg_review_time > 300 seconds: GUARDIAN is slow
   ```

2. **Check if GUARDIAN queue is processing**
   ```bash
   # Sample recent reviews
   sqlite3 /path/to/nexus.db "SELECT incident_id, decision, updated_at FROM incidents 
     WHERE status IN ('approved','rejected') 
     AND updated_at > datetime('now','-5 minutes') 
     LIMIT 20;"
   
   # If no results: GUARDIAN isn't processing at all
   ```

3. **Check if there's a system issue blocking reviews**
   ```bash
   # Database locks
   lsof /path/to/nexus.db
   
   # Network connectivity (if GUARDIAN is remote)
   ping guardian-api.company.com
   
   # GUARDIAN service logs
   docker logs guardian-service --tail 50  # if containerized
   tail -50 /var/log/guardian/*.log  # if on-host
   ```

4. **Check for bugs in recent deploys**
   ```bash
   git log --oneline -10
   
   # Any recent changes to review logic?
   git log -p --follow -S "pending_review\|approval_logic" | head -50
   ```

---

## If Backlog Still High (20+ min)

1. **Manual intervention: trigger review processing**
   ```bash
   # If GUARDIAN uses async queue, check if it's stuck
   # Restart the review processor
   docker restart guardian-worker
   systemctl restart nexus-guardian-worker
   
   # Or manually process pending reviews
   curl -X POST https://guardian-api.company.com/process-queue
   ```

2. **Temporary mitigation: prioritize oldest incidents**
   ```bash
   # Manually approve very old pending incidents (> 2 hours old)
   # Only if GUARDIAN is truly stuck
   sqlite3 /path/to/nexus.db "UPDATE incidents 
     SET status='approved', reviewed_by='admin-override', 
     updated_at=datetime('now')
     WHERE status='pending_review' 
     AND created_at < datetime('now','-2 hours')
     LIMIT 10;"
   
   # Log this for audit trail
   echo "Admin override: approved $(sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM incidents WHERE reviewed_by='admin-override'")" 
     >> /var/log/nexus/admin-actions.log
   ```

3. **Scale up GUARDIAN capacity (if applicable)**
   ```bash
   # Increase workers if GUARDIAN is scalable
   kubectl scale deployment guardian-worker --replicas=5
   
   # Or if on VMs, spin up additional review nodes
   ```

4. **Escalation**
   - Slack: `@guardian-ops`
   - Page on-call: if backlog > 200 incidents for > 1 hour
   - Create incident ticket: "GUARDIAN review queue backed up"

---

## Post-Incident

- [ ] Identify root cause: spike, slow GUARDIAN, bug, or resource issue?
- [ ] If spike: did we expect it? Plan for next time
- [ ] If slow GUARDIAN: profile and optimize review logic
- [ ] If bug: fix and test fix in staging
- [ ] Set up dashboard: review queue depth, processing rate, latency
- [ ] Increase alert threshold if 50 is too sensitive
- [ ] Document SLA: max time in pending_review state

---

## Prevention

- Monitor review queue depth continuously
- Set SLA: incidents should exit pending_review within 5 minutes
- Alert if >50% of incidents are pending (not just absolute count)
- Scale GUARDIAN capacity ahead of expected growth
- Implement timeout: if incident pending > 30 min, auto-approve or escalate
- Test spike scenarios regularly

---

## Capacity Planning

- Current GUARDIAN capacity: X decisions/minute
- Current submission rate: Y submissions/minute
- Headroom: if Y > 0.8*X, we need more capacity

---

## Contact & Escalation

- **GUARDIAN Operations:** See wiki
- **GUARDIAN Engineering:** If performance issue
- **Incident Commander:** If backlog > 200 for > 1 hour
