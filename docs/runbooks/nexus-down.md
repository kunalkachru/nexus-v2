# Runbook: NEXUS Service Down

**Alert:** `NexusDown`  
**Severity:** CRITICAL  
**On-Call Owner:** Backend Team  
**Estimated Resolution Time:** 15-30 minutes

---

## Symptoms

- NEXUS service is not responding to HTTP requests
- Prometheus shows `up{job="nexus"} == 0` for >5 minutes
- Users report inability to submit incidents or access the NEXUS API
- Webhook deliveries are timing out

---

## Immediate Actions (< 5 min)

1. **Confirm the alert is real (not a false positive)**
   ```bash
   curl -v http://localhost:7860/health
   ```
   - If response is `200 OK`, service is up but Prometheus scrape is failing (skip to "If Immediate Actions Don't Work")
   - If connection refused or timeout, proceed to step 2

2. **Check service status**
   ```bash
   docker ps | grep nexus
   systemctl status nexus  # if systemd
   ```
   - Note: Is container/process running? What's the status?

3. **Check logs for crash reason**
   ```bash
   docker logs nexus-app --tail 50
   tail -f /var/log/nexus/app.log
   ```
   - Look for: OOM errors, panic, unhandled exception, database connection errors
   - Document the last error message

4. **Restart the service**
   ```bash
   docker restart nexus-app
   # OR
   systemctl restart nexus
   ```
   - Wait 30 seconds for startup
   - Re-run health check: `curl -v http://localhost:7860/health`

5. **Verify metrics are flowing**
   - Prometheus should show `up{job="nexus"} == 1` within 1 minute (15s scrape interval)
   - Check Grafana System Health dashboard for uptime metric updating

---

## If Immediate Actions Don't Work (5-15 min)

1. **Check dependencies**
   ```bash
   # Database connectivity
   sqlite3 /path/to/nexus.db "SELECT COUNT(*) FROM incidents;"
   
   # Network/firewall
   netstat -tlnp | grep 7860
   ```

2. **Check for resource exhaustion**
   ```bash
   df -h  # Disk space
   free -h  # Memory
   top -b -n 1 | head -20  # CPU
   ```
   - If disk full (>95%): clean up old logs/backups
   - If memory critical: kill unrelated processes

3. **Check environment configuration**
   ```bash
   docker inspect nexus-app | grep -A 20 Env
   echo $DATABASE_PATH $WEBHOOK_SECRET $LOG_LEVEL
   ```
   - Verify `DATABASE_PATH`, `WEBHOOK_SECRET`, `RUNTIME_HOST_SECRET` are set

4. **Try manual startup with debug logging**
   ```bash
   # Kill the broken instance
   docker kill nexus-app
   
   # Start with DEBUG logging
   docker run --rm -e LOG_LEVEL=DEBUG \
     -p 7860:7860 \
     -v ./incidents.json:/app/incidents.json \
     nexus:latest
   ```
   - Watch console output for specific errors

---

## If Still Broken (15+ min)

1. **Escalation to Platform Team**
   - Slack: `@platform-oncall`
   - Email: `platform-team@company.com`
   - Include: last error message, logs, resource metrics

2. **Last resort: Database recovery**
   ```bash
   # Backup current (possibly corrupted) database
   cp /path/to/nexus.db /path/to/nexus.db.backup.$(date +%s)
   
   # Restore from last-known-good backup
   aws s3 cp s3://nexus-backups/latest/nexus.db /path/to/nexus.db
   
   # Restart service
   docker restart nexus-app
   ```

3. **If still down after DB restore**
   - Check if Docker image is corrupt: `docker image inspect nexus:latest`
   - Redeploy image from registry: `docker pull nexus:latest && docker restart nexus-app`
   - Check for network/DNS issues: `ping 8.8.8.8`

---

## Post-Incident

- [ ] Identify root cause (crash, resource, dependency)
- [ ] Check logs for warnings preceding the crash
- [ ] Implement fix (code, config, resource limit)
- [ ] Add health check monitoring to Datadog/PagerDuty
- [ ] Create ticket to improve startup resilience
- [ ] Run disaster recovery drill using `docs/runbooks/disaster-recovery-procedure.md`

---

## Contact & Escalation

- **Backend Team Lead:** See wiki for contact
- **Platform Oncall:** Slack `#platform-oncall`
- **VP Engineering (after 30 min down):** Escalate immediately
