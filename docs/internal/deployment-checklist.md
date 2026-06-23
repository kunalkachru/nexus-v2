# NEXUS Production Deployment Checklist

**Deployment Date:** ___________________  
**Deployed By:** ___________________  
**Approved By:** ___________________  
**Deployment Time:** ___________________  

---

## Pre-Deployment (24-48 Hours Before)

### Validation & Sign-Off

- [ ] All pre-production validation tests pass
  - [ ] Task 7.1: Security review passed
  - [ ] Task 7.2: Load testing completed
  - [ ] Task 7.3: DR drill completed
  - [ ] Task 7.4: Ops team trained

- [ ] Backup system verified working
  - [ ] Latest backup verified: `ls -lh .backup/nexus/ | head -1`
  - [ ] Backup integrity checked: `gzip -t <backup_file>`
  - [ ] Restore procedure tested locally

- [ ] Monitoring system verified
  - [ ] Prometheus scraping: `curl http://localhost:9090/api/v1/targets`
  - [ ] Grafana dashboards accessible: `http://localhost:3000`
  - [ ] Alert rules loaded: `curl http://localhost:9090/api/v1/rules`

- [ ] Runbooks reviewed
  - [ ] Incident response runbooks reviewed
  - [ ] Troubleshooting guide reviewed
  - [ ] Escalation procedures confirmed

### Infrastructure Check

- [ ] Deployment environment ready
  - [ ] Docker/Kubernetes available and operational
  - [ ] Container registry access confirmed (if applicable)
  - [ ] Load balancer/DNS ready for cutover (if applicable)

- [ ] Resource allocation
  - [ ] 2+ GB memory available: `free -h`
  - [ ] 5+ GB disk space available: `df -h /`
  - [ ] CPU not throttled: `top -bn1 | head -5`

### Communication

- [ ] Stakeholders notified of deployment window
  - [ ] Email sent to: (list emails)
  - [ ] Slack announcement posted to: #deployments
  - [ ] PagerDuty deployment window created

- [ ] Escalation contacts confirmed
  - [ ] DevOps Lead contact verified
  - [ ] On-Call Engineer contact verified
  - [ ] Backend Lead contact verified
  - [ ] Deployment Manager contact verified

### Documentation

- [ ] Deployment guide reviewed: `docs/internal/production-deployment-guide.md`
- [ ] Rollback plan documented and understood
- [ ] Pre-deployment validation script tested: `scripts/pre-deployment-validation.sh`
- [ ] Post-deployment health check script tested: `scripts/post-deployment-health-check.sh`

---

## Deployment Day

### Pre-Deployment (1 Hour Before)

**Time Started:** ___________________

- [ ] Final notification sent: "Deployment starting in 1 hour"
  - [ ] Slack notification posted
  - [ ] Team channel notified
  - [ ] Support team notified

- [ ] Prerequisites verified one more time
  - [ ] Docker running: `docker ps`
  - [ ] Database accessible: `ls -lh artifacts/incidents.json`
  - [ ] Scripts executable: `ls -x scripts/*.sh`
  - [ ] No service currently running: `curl http://localhost:7860/health` (should fail)

- [ ] Backups taken
  - [ ] Database backup: `cp artifacts/incidents.json artifacts/incidents.json.pre-deployment`
  - [ ] Current state recorded

- [ ] Tools verified
  - [ ] Docker version: `docker --version`
  - [ ] Python version: `python3 --version`
  - [ ] Git status: `git status` (clean working directory)
  - [ ] All required scripts present: `ls -1 scripts/pre-deployment-validation.sh scripts/post-deployment-health-check.sh`

- [ ] Baseline metrics recorded
  - [ ] Current incident count: ___________________
  - [ ] Current database size: ___________________
  - [ ] System resources before: ___________________

### During Deployment

**Deployment Started:** ___________________

#### Phase 1: Validation (5 minutes)

- [ ] Run pre-deployment validation: `./scripts/pre-deployment-validation.sh`
  - [ ] All checks passed
  - [ ] No critical failures
  - [ ] Ready to proceed

- [ ] Review any warnings: ___________________

#### Phase 2: Image Building (10 minutes)

**Build Started:** ___________________

- [ ] Build Docker image
  ```bash
  docker build \
    -t nexus:prod \
    --build-arg APP_ENV=production \
    --label "version=1.0" \
    --label "build-date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    .
  ```

  - [ ] Build completed without errors
  - [ ] Image tagged: `docker images | grep nexus:prod`
  - [ ] Image size: ___________________
  - [ ] Build time: ___________________

**Build Completed:** ___________________

#### Phase 3: Deployment (5 minutes)

**Deployment Started:** ___________________

- [ ] Stop any existing service
  - [ ] `docker stop nexus-prod 2>/dev/null || true`
  - [ ] `docker rm nexus-prod 2>/dev/null || true`

- [ ] Deploy new service
  - [ ] Using docker-compose: `docker-compose -f docker-compose.yml up -d`
  - OR using docker run with production settings

- [ ] Wait for startup
  - [ ] `sleep 10` (allow service initialization)

**Deployment Completed:** ___________________

#### Phase 4: Health Verification (10 minutes)

**Verification Started:** ___________________

- [ ] Immediate health check
  - [ ] `curl -s http://localhost:7860/health | jq .`
  - [ ] Status shows: `"status": "ok"`
  - [ ] No errors in response

- [ ] Run full health check script
  - [ ] `./scripts/post-deployment-health-check.sh`
  - [ ] All checks passed
  - [ ] No critical issues

- [ ] Verify database accessibility
  - [ ] `curl -H "Authorization: Bearer test" http://localhost:7860/api/incidents`
  - [ ] Response valid (or auth error, not server error)
  - [ ] All incidents still present: ___________________

- [ ] Verify metrics flowing
  - [ ] `curl -s http://localhost:7860/metrics | head -10`
  - [ ] Prometheus metrics present
  - [ ] Metric values reasonable

**Verification Completed:** ___________________

#### Phase 5: Smoke Testing (10 minutes)

**Tests Started:** ___________________

- [ ] Run smoke test suite
  - [ ] `./scripts/local_enterprise_smoke.sh`
  - [ ] All tests passed
  - [ ] No failures or warnings

- [ ] Smoke test results
  - [ ] Duration: ___________________
  - [ ] Status: PASSED / FAILED
  - [ ] Issues found: ___________________

**Tests Completed:** ___________________

#### Phase 6: Monitoring Setup (5 minutes)

- [ ] Verify Prometheus collecting metrics
  - [ ] `curl -s http://localhost:9090/api/v1/query?query=nexus_incidents_created_total`
  - [ ] Metrics appearing in Prometheus

- [ ] Verify Grafana dashboards
  - [ ] Dashboard URL: `http://localhost:3000/d/nexus-health`
  - [ ] All panels loading
  - [ ] Data visualizing correctly

- [ ] Verify alerting active
  - [ ] Alert rules loaded: `curl http://localhost:9090/api/v1/rules | jq '.data.groups | length'`
  - [ ] At least 5 alert rules present

- [ ] Start monitoring period
  - [ ] Begin continuous monitoring (Task 8.2)
  - [ ] Set timer for 24-hour period

**Monitoring Started:** ___________________

### Post-Deployment (1 Hour After)

**Post-Deployment Started:** ___________________

- [ ] Monitor application logs
  - [ ] `docker logs -f nexus-prod` (5 minutes)
  - [ ] OR `tail -f /var/log/nexus.log`
  - [ ] No ERROR messages
  - [ ] No unexpected warnings

- [ ] Verify metrics stable
  - [ ] Request rate consistent
  - [ ] Error rate < 1%
  - [ ] Response time < 100ms p95

- [ ] Verify backup running
  - [ ] Check backup log: `tail -10 /var/log/nexus-backup.log`
  - [ ] Most recent backup time: ___________________
  - [ ] File size: ___________________

- [ ] Final health check
  - [ ] `curl http://localhost:7860/health`
  - [ ] Status: ok
  - [ ] All systems nominal

- [ ] Record deployment metrics
  - [ ] Deployment start time: ___________________
  - [ ] Deployment end time: ___________________
  - [ ] Total deployment time: ___________________
  - [ ] Issues encountered: ___________________
  - [ ] Resolutions applied: ___________________

- [ ] Notify stakeholders
  - [ ] Slack notification: "Deployment complete and healthy"
  - [ ] Email to stakeholders with results
  - [ ] Status page updated (if applicable)

**Post-Deployment Completed:** ___________________

---

## Deployment Outcome

### Result

- [ ] SUCCESSFUL - All checks passed, service healthy, proceeding to 24-hour monitoring
- [ ] ISSUES - Service running but with warnings, continue monitoring closely
- [ ] FAILED - Critical issues, initiating rollback

### Issues Encountered

| # | Issue | Severity | Resolution | Owner | Status |
|---|-------|----------|-----------|-------|--------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

### Performance vs. Baseline

| Metric | Pre-Deployment | Post-Deployment | Status |
|--------|----------------|-----------------|--------|
| Incident Count | | | ✓ / ✗ |
| Database Size | | | ✓ / ✗ |
| Response Time | | | ✓ / ✗ |
| Error Rate | | | ✓ / ✗ |
| Memory Usage | | | ✓ / ✗ |
| CPU Usage | | | ✓ / ✗ |

---

## Rollback Decision

**If deployment failed or critical issues found:**

### Rollback Authorization

- [ ] Rollback approved by: ___________________
- [ ] Approval time: ___________________
- [ ] Authorized by: (title) ___________________

### Rollback Execution

**Rollback Started:** ___________________

- [ ] Stop new deployment: `docker stop nexus-prod`
- [ ] Remove new deployment: `docker rm nexus-prod`
- [ ] Restore from backup: `./scripts/restore_nexus.sh artifacts/incidents.json.pre-deployment`
- [ ] Restart previous version: `docker-compose up -d`
- [ ] Verify health: `curl http://localhost:7860/health`
- [ ] Confirm incident count restored: ___________________

**Rollback Completed:** ___________________

### Rollback Analysis

- [ ] Root cause identified: ___________________
- [ ] Issue documentation: ___________________
- [ ] Next steps: ___________________
- [ ] Retry date: ___________________

---

## Sign-Off

### Deployment Approval

**Deployment was successful and approved for continued operation.**

| Role | Name | Signature | Date | Time |
|------|------|-----------|------|------|
| Deployed By | | | | |
| Verified By | | | | |
| Approved By (DevOps) | | | | |
| Approved By (Engineering) | | | | |

### Next Phase

- [ ] Proceed to Task 8.2: 24-hour monitoring
- [ ] On-call engineer notified and standing by
- [ ] Monitoring period begins: ___________________
- [ ] Expected completion: ___________________

---

## Related Documentation

- [Production Deployment Guide](./production-deployment-guide.md)
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md)
- [Runbooks](../runbooks/)
- [Health Validation Scripts](../../scripts/post-deployment-health-check.sh)

---

**Document Owner:** DevOps Lead  
**Last Updated:** 2026-06-17  
**Checklist Template Version:** 1.0
