# NEXUS Troubleshooting Guide

**Version:** 1.0  
**Last Updated:** 2026-06-17  
**Audience:** Operations Engineers, On-Call Support

---

## Quick Links

- **Service Down?** → [Scenario 1](#scenario-1-incident-wont-load)
- **Webhook Rejecting Requests?** → [Scenario 2](#scenario-2-webhook-keeps-rejecting)
- **Auth Failures Spiking?** → [Scenario 3](#scenario-3-auth-failures-spiking)
- **Database Growing Fast?** → [Scenario 4](#scenario-4-database-growing-fast)
- **GUARDIAN Rejecting Safe Actions?** → [Scenario 5](#scenario-5-guardian-keeps-rejecting-safe-actions)
- **Performance Degraded?** → [Scenario 6](#scenario-6-performance-degraded)
- **Can't Access the API?** → [Scenario 7](#scenario-7-cant-access-the-api)

---

## Scenario 1: Incident Won't Load

**Symptoms:**
- Users report incidents stuck in loading state
- API returns 5xx errors or timeouts
- Prometheus shows `nexus_incident_processing_duration_seconds` spiking

### Diagnosis Steps

1. **Check if NEXUS is responding at all**
   ```bash
   curl -v http://localhost:7860/health
   ```
   - If fails: NEXUS is down → go to [NEXUS Service Down runbook](docs/runbooks/nexus-down.md)
   - If succeeds: continue to step 2

2. **Check specific incident in database**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT incident_id, status, created_at FROM incidents WHERE incident_id='<incident_id>';"
   ```
   - If not found: incident never created (check webhook logs)
   - If found but status='pending_review': incident stuck in GUARDIAN → [GUARDIAN runbook](docs/runbooks/guardian-approval-rate.md)
   - If found but status='approved': check why client sees it as loading

3. **Check API response time**
   ```bash
   time curl -s http://localhost:7860/incidents/<incident_id>
   ```
   - If >5 seconds: database query is slow → [Slow Persistence runbook](docs/runbooks/slow-persistence.md)
   - If <1 second: network issue between client and server

4. **Check incident data validity**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT incident_data FROM incidents WHERE incident_id='<incident_id>';" | python -m json.tool
   ```
   - If invalid JSON: data corrupted → escalate to database team
   - If valid: client-side parsing issue

### Fix Steps

- If incident stuck in GUARDIAN: check [pending reviews runbook](docs/runbooks/pending-reviews-backlog.md)
- If query is slow: rebuild indexes and vacuum database (see [slow persistence runbook](docs/runbooks/slow-persistence.md))
- If client parsing fails: verify API response format with spec
- If network timeout: check network connectivity and firewall rules

### Related Runbook
→ [docs/runbooks/nexus-down.md](docs/runbooks/nexus-down.md)
→ [docs/runbooks/pending-reviews-backlog.md](docs/runbooks/pending-reviews-backlog.md)

---

## Scenario 2: Webhook Keeps Rejecting Requests

**Symptoms:**
- Webhook calls return 401 Unauthorized or 403 Forbidden
- Caller says request should be valid
- Prometheus shows `nexus_auth_failures_total` increasing

### Diagnosis Steps

1. **Check webhook signature verification**
   ```bash
   # Check if WEBHOOK_SECRET is configured
   echo $WEBHOOK_SECRET
   
   # Verify it's not empty
   [ -z "$WEBHOOK_SECRET" ] && echo "SECRET NOT SET" || echo "Secret is set"
   ```

2. **Check caller's shared secret**
   - Ask caller: "What value do you have for NEXUS_WEBHOOK_SECRET?"
   - Compare with your `$WEBHOOK_SECRET`
   - If different: one side rotated without updating the other

3. **Check webhook headers**
   ```bash
   # Ask caller to send with verbose headers
   curl -v -X POST \
     -H "X-Webhook-Signature: <signature>" \
     -H "Content-Type: application/json" \
     http://localhost:7860/incidents/webhook \
     -d '{"test": true}'
   ```
   - Verify signature is present and valid format

4. **Verify secret encoding**
   ```bash
   # Your side: secret should be base64 or plain string
   echo -n "test_data" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET"
   
   # Ask caller to do same with their secret
   # Signatures should match if secrets match
   ```

### Fix Steps

**If secrets don't match:**
1. Determine which secret is correct (check configuration management)
2. Notify caller of correct value
3. Ask caller to update their configuration
4. Test webhook again

**If secrets match but still failing:**
1. Check signature calculation algorithm (SHA256 HMAC vs HMAC-SHA256)
2. Verify request body isn't being modified in transit
3. Check if secret contains special characters that need escaping

**If just deployed new code:**
1. Check if signature verification logic changed: `git diff HEAD~1 -- server/webhooks.py`
2. If logic changed, may need to rollback or fix implementation

### Related Runbook
→ [docs/runbooks/auth-failures.md](docs/runbooks/auth-failures.md)

---

## Scenario 3: Auth Failures Spiking

**Symptoms:**
- Alert fires: `SuspiciousAuthFailures`
- Prometheus shows `rate(nexus_auth_failures_total[5m]) > 0.2`
- Audit logs show many failed auth attempts

### Diagnosis Steps

1. **Identify the source of failures**
   ```bash
   # Count failures by type
   sqlite3 /path/to/nexus.db "SELECT failure_type, COUNT(*) FROM audit_logs 
     WHERE event_type='auth_failure' AND created_at > datetime('now','-5 minutes')
     GROUP BY failure_type ORDER BY COUNT(*) DESC;"
   ```
   - Mostly `invalid_signature`? → webhook secret issue
   - Mostly `invalid_token`? → API key issue
   - Mixed? → could be attack or misconfiguration

2. **Check if it's an attack or misconfiguration**
   ```bash
   # Failures from many different sources → attack
   grep "auth_failure" /var/log/nexus/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
   
   # Failures from single source → misconfiguration
   ```

3. **Check if credentials were recently rotated**
   ```bash
   grep -i "secret.*rotation\|credential.*update" /var/log/nexus/audit.log | tail -10
   
   # When was last rotation?
   # Did you notify callers?
   ```

### Fix Steps

**If attack detected:**
- Block attacker IP: `iptables -I INPUT -s <IP> -j DROP`
- Rotate WEBHOOK_SECRET and RUNTIME_HOST_SECRET
- Notify customers of new credentials

**If misconfiguration:**
- Contact webhook owners: "Your secrets are outdated, please update"
- Wait for them to update and re-test

**If recent deployment:**
- Check if auth logic changed: `git log -p --follow -S "verify.*signature" | head -50`
- If broken, rollback: `git revert <commit>`

### Related Runbook
→ [docs/runbooks/auth-failures.md](docs/runbooks/auth-failures.md)

---

## Scenario 4: Database Growing Fast

**Symptoms:**
- Alert fires: `DatabaseGrowthFast`
- Disk usage increasing rapidly (>1GB/day)
- Database file growing visibly

### Diagnosis Steps

1. **Check which table is growing**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT name, page_count * (SELECT page_size FROM pragma_page_size()) as size_bytes 
     FROM sqlite_master WHERE type='table' ORDER BY size_bytes DESC;"
   ```
   - `incidents` table huge? → too many incidents or large incident_data
   - `audit_logs` huge? → audit retention policy missing

2. **Check incident count**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM incidents;"
   sqlite3 /path/to/nexus.db "SELECT AVG(LENGTH(incident_data)) FROM incidents;"
   ```
   - If count normal but avg size large: individual incidents are huge
   - If count very high: need retention policy

3. **Check for unusual data patterns**
   ```bash
   # Largest incidents
   sqlite3 /path/to/nexus.db "SELECT incident_id, LENGTH(incident_data) FROM incidents 
     ORDER BY LENGTH(incident_data) DESC LIMIT 10;"
   
   # Are sizes normal or abnormal?
   ```

### Fix Steps

**If audit logs are huge:**
```bash
# Delete old audit logs
sqlite3 /path/to/nexus.db "DELETE FROM audit_logs WHERE created_at < datetime('now','-90 days');"

# Compact database
sqlite3 /path/to/nexus.db "VACUUM;"
```

**If incidents are huge:**
```bash
# Archive old incidents
sqlite3 /path/to/nexus.db ".mode json" ".output incidents_backup.json" \
  "SELECT * FROM incidents WHERE created_at < datetime('now','-30 days');"

aws s3 cp incidents_backup.json s3://nexus-backups/incidents_archived.json

# Delete archived incidents
sqlite3 /path/to/nexus.db "DELETE FROM incidents WHERE created_at < datetime('now','-30 days');"

# Compact
sqlite3 /path/to/nexus.db "VACUUM;"
```

**If individual incidents are abnormally large:**
- Investigate: why is this incident data so large?
- Consider: implement data size limits or compression

### Related Runbook
→ [docs/runbooks/database-growth.md](docs/runbooks/database-growth.md)

---

## Scenario 5: GUARDIAN Keeps Rejecting Safe Actions

**Symptoms:**
- Alert fires: `GuardianApprovalRateLow`
- Users complain: "Legitimate incidents keep getting rejected"
- Approval rate dropped to <50%

### Diagnosis Steps

1. **Sample recent GUARDIAN decisions**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT incident_id, decision, decision_reason FROM incidents 
     WHERE created_at > datetime('now','-1 hour') AND decision='rejected' 
     LIMIT 20;"
   ```
   - Look for: consistent rejection reason or varied?
   - If consistent: new rule is too strict
   - If varied: GUARDIAN quality degraded

2. **Check if rules changed**
   ```bash
   git log --oneline -20 -- server/guardian.py
   
   # Was there a recent commit that changed decision logic?
   git show <recent-commit> | grep -A 10 -B 10 "decision\|reject\|rule"
   ```

3. **Check GUARDIAN service health (if external)**
   ```bash
   curl -s https://guardian-api.company.com/health
   
   # Check latency
   time curl -s https://guardian-api.company.com/decision -X POST -d '{}'
   ```

### Fix Steps

**If new rule is too strict:**
- Option 1: Revert the commit that added it
- Option 2: Adjust the rule to be less strict
- Option 3: Update alert threshold to accept new baseline

**If GUARDIAN service is slow/down:**
- Check service logs: `docker logs guardian-service --tail 100`
- Restart if needed: `docker restart guardian-service`
- Escalate to GUARDIAN team if persistent

**If decision logic broke:**
- Review the diff: `git diff HEAD~1 HEAD -- server/guardian.py`
- Fix the logic or rollback
- Test with historical incidents to validate fix

### Related Runbook
→ [docs/runbooks/guardian-approval-rate.md](docs/runbooks/guardian-approval-rate.md)

---

## Scenario 6: Performance Degraded

**Symptoms:**
- API responses slow (>1s for incident creation)
- Prometheus shows high latency: `nexus_artifact_persistence_latency_ms > 500`
- Incident submission times slow

### Diagnosis Steps

1. **Check system resources**
   ```bash
   # CPU usage
   top -b -n 1 | grep nexus
   
   # Memory usage
   free -h
   
   # Disk I/O
   iostat -x 1 5
   ```
   - High CPU: query scanning large dataset or inefficient code
   - High memory: memory leak or large cache
   - High I/O: disk is bottleneck

2. **Check database performance**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM incidents;"
   
   # Check if table is fragmented
   sqlite3 /path/to/nexus.db "PRAGMA freelist_count;"
   
   # Check if indexes exist
   sqlite3 /path/to/nexus.db ".indices incidents"
   ```

3. **Check recent deployments**
   ```bash
   git log --oneline -10
   
   # Was there a query change?
   git diff HEAD~1 HEAD -- server/db.py | grep -A 5 -B 5 "SELECT\|WHERE"
   ```

### Fix Steps

**If database is slow:**
```bash
# Rebuild indexes
sqlite3 /path/to/nexus.db "REINDEX;"

# Analyze query planner
sqlite3 /path/to/nexus.db "ANALYZE;"

# Defragment
sqlite3 /path/to/nexus.db "VACUUM;"
```

**If CPU is high:**
- Check if recent deployment added slow queries
- Profile with: `docker exec nexus-app python -m cProfile -s cumtime /app/main.py`

**If disk I/O is high:**
- Check if database is being copied/backed up
- Check if unrelated process is causing I/O
- Consider: is database too large for disk performance?

### Related Runbook
→ [docs/runbooks/slow-persistence.md](docs/runbooks/slow-persistence.md)

---

## Scenario 7: Can't Access the API

**Symptoms:**
- All API calls return connection refused or timeout
- `curl http://localhost:7860/health` hangs or fails
- Service appears down to all users

### Diagnosis Steps

1. **Check if service is running**
   ```bash
   ps aux | grep nexus
   docker ps | grep nexus
   systemctl status nexus
   ```
   - If not running: start it
   - If running but no response: may be hung

2. **Check network connectivity**
   ```bash
   netstat -tlnp | grep 7860
   
   # Should show: LISTEN on 0.0.0.0:7860 or 127.0.0.1:7860
   ```

3. **Check firewall/security groups**
   ```bash
   # If on cloud (AWS/GCP)
   # Check security group rules allow inbound on port 7860
   # Check NACLs
   
   # If on-host firewall
   sudo iptables -L -n | grep 7860
   sudo firewall-cmd --list-ports
   ```

4. **Check if service is in a bad state**
   ```bash
   docker logs nexus-app --tail 100
   tail -100 /var/log/nexus/app.log
   
   # Look for: panic, segfault, OOM, stuck thread
   ```

### Fix Steps

**If service crashed:**
1. Check logs for error message
2. Fix the root cause
3. Restart: `docker restart nexus-app` or `systemctl restart nexus`

**If firewall blocking:**
1. Allow port 7860: `sudo iptables -I INPUT -p tcp --dport 7860 -j ACCEPT`
2. Or update security group in cloud console

**If service hanging:**
1. Kill hung process: `docker kill nexus-app` or `kill -9 <PID>`
2. Restart: `docker start nexus-app`
3. Monitor logs for what caused hang

**If stuck in boot:**
1. Check if port is already in use: `lsof -i :7860`
2. Kill other process or change NEXUS port
3. Restart NEXUS

### Related Runbook
→ [docs/runbooks/nexus-down.md](docs/runbooks/nexus-down.md)

---

## Common Quick Fixes

| Issue | Quick Fix | Test |
|-------|-----------|------|
| Webhook rejected | Check `$WEBHOOK_SECRET` matches caller's | `curl -X POST ... -H "X-Webhook-Signature: ..."` |
| Incident not loading | Check if status='pending_review' | `sqlite3 ... "SELECT status FROM incidents WHERE incident_id=...;"` |
| Auth failures | Rotate secrets if recent change | `grep auth_failure /var/log/nexus/access.log \| wc -l` |
| Slow responses | Run `VACUUM` and `ANALYZE` | `time curl http://localhost:7860/health` |
| Disk full | Archive old incidents and run `VACUUM` | `df -h /path/to/nexus.db` |

---

## When to Escalate

- **Service down >5 minutes:** Page on-call
- **Disk full:** Escalate to infrastructure
- **Database corruption:** Escalate to database team
- **Auth compromise:** Escalate to security team
- **3+ failed troubleshooting attempts:** Escalate to architecture team

---

## Getting Help

- **Operations Questions:** See [Runbooks](docs/runbooks/)
- **Code Questions:** Check [README.md](README.md) and inline docs
- **Escalation:** Slack `#nexus-oncall` or page on-call engineer

---

## Version History

- **1.0** (2026-06-17): Initial guide created with 7 common scenarios
