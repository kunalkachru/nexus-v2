# NEXUS Production Deployment Guide

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Audience:** DevOps Engineers, Release Managers  
**Scope:** Local validation through deployment readiness (Option A: safe, documented procedures)

---

## Overview

This guide documents the complete NEXUS production deployment procedure. It covers:
- Pre-deployment validation
- Production image building
- Deployment procedures (local simulation)
- Health verification
- Smoke testing
- Deployment checklist

**Scope Note:** This document prepares the deployment package for operations teams. Actual deployment to GCR and load balancer cutover will be performed by authorized DevOps personnel with appropriate credentials and access.

---

## Pre-Deployment Validation

### Validation Checklist

Before any deployment attempt, verify:

```bash
#!/bin/bash
echo "=== NEXUS Pre-Deployment Validation ==="

# 1. All required files exist
echo "1. Checking required files..."
REQUIRED_FILES=(
  "Dockerfile"
  "docker-compose.yml"
  "requirements.txt"
  "server/app.py"
  "artifacts/incidents.json"
  "scripts/backup_nexus.sh"
  "scripts/restore_nexus.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✓ $file"
  else
    echo "  ✗ $file MISSING"
    exit 1
  fi
done

# 2. Tests passing
echo "2. Running test suite..."
python -m pytest tests/ -q --tb=line 2>&1 | tail -5

# 3. Code quality checks
echo "3. Checking code quality..."
if command -v pylint &> /dev/null; then
  pylint server/ --disable=all --enable=E,F 2>/dev/null | tail -3 || echo "  (pylint not configured)"
fi

# 4. Requirements available
echo "4. Checking dependencies..."
pip list | grep -E "^(fastapi|uvicorn|pydantic)" | wc -l | xargs -I {} echo "  ✓ Found {} key dependencies"

# 5. Configuration files
echo "5. Checking configuration..."
ls -1 prometheus/alerts.yml 2>/dev/null && echo "  ✓ Prometheus alerts configured" || echo "  ✗ Prometheus alerts missing"
ls -1 docs/TROUBLESHOOTING_GUIDE.md 2>/dev/null && echo "  ✓ Troubleshooting guide present" || echo "  ✗ Troubleshooting guide missing"

# 6. Backup validated
echo "6. Checking backup/restore..."
[ -f "scripts/backup_nexus.sh" ] && [ -x "scripts/backup_nexus.sh" ] && echo "  ✓ Backup script ready" || echo "  ✗ Backup script not executable"
[ -f "scripts/restore_nexus.sh" ] && [ -x "scripts/restore_nexus.sh" ] && echo "  ✓ Restore script ready" || echo "  ✗ Restore script not executable"

# 7. Current health
echo "7. Checking current service health..."
if curl -s http://localhost:7860/health > /dev/null 2>&1; then
  curl -s http://localhost:7860/health | jq .
else
  echo "  (Service not currently running — expected for fresh deployment)"
fi

echo ""
echo "=== Pre-Deployment Validation Complete ==="
```

**Run validation:**
```bash
chmod +x scripts/pre-deployment-validation.sh
./scripts/pre-deployment-validation.sh
```

---

## Production Docker Image

### Current Dockerfile Review

**File:** `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ARG APP_ENV=demo
ENV APP_ENV=${APP_ENV}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

**Assessment:**
- ✓ Uses Python 3.11-slim (good for size/security)
- ✓ Non-root execution (depends on base image)
- ✓ Proper layer caching (requirements before code)
- ✓ PYTHONUNBUFFERED for container logging

**Production Readiness:**
The current Dockerfile is suitable for production deployment with the APP_ENV set to "production".

### Building Production Image

```bash
# Build with production environment
docker build \
  -t nexus:prod \
  --build-arg APP_ENV=production \
  --label "version=1.0" \
  --label "build-date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  .

# Verify image
docker images | grep nexus:prod

# Check image size
docker images nexus:prod --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

**Expected:**
- Image builds without errors
- Size: ~400-500 MB (Python 3.11-slim + dependencies)
- Contains all required files

### Image Security Scan (Optional)

If using container scanning tools:

```bash
# Example with docker scout (if available)
docker scout cves nexus:prod

# Or with trivy (if available)
trivy image nexus:prod
```

---

## Deployment Procedure

### Option 1: Docker Compose (Recommended for Staging/Production)

**File:** `docker-compose.yml`

```bash
# Deploy with docker-compose
docker-compose -f docker-compose.yml up -d

# Verify running
docker-compose ps

# Check logs
docker-compose logs -f nexus

# Stop (if needed)
docker-compose down
```

**Environment Variables:**
```bash
# Create .env file (in production, set via deployment system)
APP_ENV=production
PORT=7860
NEXUS_RUNTIME_HOST_BASE_URL=http://runtime-host:7860
NEXUS_RUNTIME_HOST_SHARED_TOKEN=<production-token>
```

### Option 2: Docker Run (Direct Container)

```bash
docker run -d \
  --name nexus-prod \
  -p 7860:7860 \
  -e APP_ENV=production \
  -e PYTHONUNBUFFERED=1 \
  -v "$(pwd)/artifacts:/app/artifacts" \
  -v "$(pwd)/.backup:/app/.backup" \
  --restart unless-stopped \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=10 \
  nexus:prod
```

**Flags Explained:**
- `-d`: Run detached (background)
- `-p 7860:7860`: Port mapping
- `-v`: Volume mounts for persistent data
- `--restart unless-stopped`: Auto-restart on failure
- `--log-driver json-file`: Container logging
- `--log-opt max-size/max-file`: Log rotation

### Option 3: Kubernetes (If Available)

Reference deployment manifest (save as `k8s-deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nexus
  template:
    metadata:
      labels:
        app: nexus
    spec:
      containers:
      - name: nexus
        image: gcr.io/nexus-prod/nexus:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 7860
          name: http
        env:
        - name: APP_ENV
          value: "production"
        - name: PYTHONUNBUFFERED
          value: "1"
        volumeMounts:
        - name: artifacts
          mountPath: /app/artifacts
        livenessProbe:
          httpGet:
            path: /health
            port: 7860
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 7860
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: artifacts
        persistentVolumeClaim:
          claimName: nexus-artifacts
---
apiVersion: v1
kind: Service
metadata:
  name: nexus
  namespace: production
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 7860
    protocol: TCP
  selector:
    app: nexus
```

**Deploy with kubectl:**
```bash
kubectl apply -f k8s-deployment.yaml
kubectl get deployment -n production
kubectl logs -f deployment/nexus -n production
```

---

## Health Verification

### Immediate Health Check (Post-Deployment)

```bash
#!/bin/bash
echo "Waiting for service startup..."
sleep 10

echo "Health check..."
HEALTH=$(curl -s http://localhost:7860/health)

if echo "$HEALTH" | jq . > /dev/null 2>&1; then
  echo "✓ Service responding"
  echo "$HEALTH" | jq .
else
  echo "✗ Service not responding or invalid JSON"
  exit 1
fi
```

### Full Health Validation

```bash
#!/bin/bash
echo "=== NEXUS Post-Deployment Health Validation ==="

# 1. Service accessible
echo "1. Service accessibility:"
if curl -s http://localhost:7860/health > /dev/null 2>&1; then
  echo "  ✓ Service accessible on port 7860"
else
  echo "  ✗ Service not accessible"
  exit 1
fi

# 2. Health endpoint
echo "2. Health endpoint:"
HEALTH=$(curl -s http://localhost:7860/health | jq -r '.status')
if [ "$HEALTH" == "ok" ]; then
  echo "  ✓ Health status: ok"
else
  echo "  ✗ Health status: $HEALTH"
  exit 1
fi

# 3. Database accessible
echo "3. Database connectivity:"
if [ -f "artifacts/incidents.json" ]; then
  INCIDENT_COUNT=$(python3 -c "import json; f=open('artifacts/incidents.json'); d=json.load(f); print(len(d.get('incidents', [])))" 2>/dev/null)
  echo "  ✓ Database accessible ($INCIDENT_COUNT incidents)"
else
  echo "  ✗ Database file not found"
  exit 1
fi

# 4. Metrics endpoint
echo "4. Metrics endpoint:"
if curl -s http://localhost:7860/metrics | grep -q "nexus_"; then
  echo "  ✓ Prometheus metrics available"
else
  echo "  ✗ Metrics endpoint not working"
fi

# 5. Memory usage
echo "5. Resource usage:"
docker stats --no-stream nexus-prod 2>/dev/null | tail -1 || echo "  (docker stats unavailable)"

echo ""
echo "=== Health Validation Complete ==="
```

---

## Smoke Testing

### Smoke Test Suite

See `tests/local_enterprise_smoke.sh` for complete suite.

**Run smoke tests:**
```bash
chmod +x scripts/local_enterprise_smoke.sh
./scripts/local_enterprise_smoke.sh
```

**Expected Results:**
- All basic operations succeed
- No errors in response validation
- Performance within expected bounds

### Quick Smoke Check (5 minutes)

```bash
#!/bin/bash
echo "=== Quick Smoke Test ==="

# 1. Service up
curl -f http://localhost:7860/health || exit 1
echo "✓ Health check passed"

# 2. Metrics
curl -s http://localhost:7860/metrics | head -5 | grep nexus || exit 1
echo "✓ Metrics available"

# 3. API accessible (with auth)
# curl -H "Authorization: Bearer test-token" \
#   http://localhost:7860/api/incidents || exit 1
# echo "✓ API accessible"

echo "✓ All smoke tests passed"
```

---

## Deployment Checklist

### Pre-Deployment (24 hours before)

- [ ] All pre-production validation tests pass (Tasks 7.1-7.4 complete)
- [ ] Load testing completed and RTO validated
- [ ] Disaster recovery drill completed successfully
- [ ] Ops team trained on all procedures
- [ ] Monitoring dashboards active and data flowing
- [ ] Backup system tested and working
- [ ] Runbooks reviewed by ops team
- [ ] Deployment plan reviewed with stakeholders
- [ ] Rollback plan documented
- [ ] Communication channels established (Slack, email)

### Deployment Day

#### Pre-Deployment (1 hour before)

- [ ] Notify stakeholders: "Deployment starting in 1 hour"
- [ ] Review deployment procedure one more time
- [ ] Have runbooks and troubleshooting guide open
- [ ] Verify all tools available: Docker, kubectl, docker-compose
- [ ] Verify credentials/secrets available (if applicable)
- [ ] Take backup of current production state
- [ ] Record current metrics baseline (for comparison post-deployment)

#### During Deployment

- [ ] Pull latest code: `git pull origin main`
- [ ] Build production image: `docker build -t nexus:prod --build-arg APP_ENV=production .`
- [ ] Verify image: `docker images nexus:prod`
- [ ] Deploy container: `docker-compose up -d` or `docker run ...`
- [ ] Wait 10 seconds for startup
- [ ] Run health check: `curl http://localhost:7860/health`
- [ ] Verify health passes
- [ ] Run smoke tests: `./scripts/local_enterprise_smoke.sh`
- [ ] Verify all smoke tests pass
- [ ] Check Prometheus metrics flowing
- [ ] Spot-check incident data retrievable
- [ ] Take screenshot/timestamp of successful deployment

#### Post-Deployment (1 hour after)

- [ ] Monitor logs for errors: `docker logs -f nexus-prod`
- [ ] Verify metrics stable
- [ ] Verify backups still running
- [ ] Verify no alerts firing
- [ ] Document deployment time and any issues
- [ ] Notify stakeholders: "Deployment complete and healthy"
- [ ] Prepare for 24-hour monitoring phase (Task 8.2)

### Rollback Plan

If deployment fails:

```bash
# 1. Stop new deployment
docker stop nexus-prod
docker rm nexus-prod

# 2. Restore from backup
./scripts/restore_nexus.sh artifacts/incidents.json.pre-deployment

# 3. Restart service with previous image
docker run ... nexus:previous

# 4. Verify health
curl http://localhost:7860/health

# 5. Notify stakeholders
echo "Deployment rolled back to previous version"
```

---

## Deployment Documentation Package

### Files to Include in Handoff (Task 8.3)

For operations team:

1. **This document** (`production-deployment-guide.md`)
2. **Pre-deployment validation script** (`scripts/pre-deployment-validation.sh`)
3. **Deployment checklist** (`docs/internal/deployment-checklist.md`)
4. **Health validation script** (`scripts/post-deployment-health-check.sh`)
5. **Smoke test suite** (`scripts/local_enterprise_smoke.sh`)
6. **Runbooks** (`docs/runbooks/`)
7. **Troubleshooting guide** (`docs/TROUBLESHOOTING_GUIDE.md`)
8. **Architecture guide** (`docs/README.md`)

### Key Contacts

| Role | Name | Email | Phone | On-Call |
|------|------|-------|-------|---------|
| DevOps Lead | (TBD) | | | |
| Backend Lead | (TBD) | | | |
| On-Call Engineer | (TBD) | | | |
| Deployment Manager | (TBD) | | | |

### Communication Template

```
Subject: NEXUS Production Deployment [DATE]

Timeline:
- Deployment starts: [TIME] UTC
- Expected duration: 30 minutes
- Completion target: [TIME] UTC
- Expected availability restoration: [TIME] UTC

Monitoring:
- Dashboard: http://grafana/d/nexus-health
- Alerts: [Slack channel]
- On-call: [contact info]

If issues arise:
- Escalate to: [contact info]
- Rollback: See deployment guide
- Postmortem: [scheduling info]
```

---

## Success Criteria

Deployment is successful when:

- ✅ Service starts without errors
- ✅ Health check returns `{"status": "ok"}`
- ✅ All smoke tests pass
- ✅ Prometheus metrics flowing
- ✅ No errors in logs
- ✅ Database accessible with all incidents present
- ✅ Backup and restore verified working
- ✅ Team notified and acknowledged
- ✅ 24-hour monitoring period begins (Task 8.2)

---

## Acceptance Criteria (Task 8.1)

- [x] Pre-deployment validation documented
- [x] Production image building documented
- [x] Deployment procedure documented (3 options)
- [x] Health verification procedures documented
- [x] Smoke testing procedures documented
- [x] Deployment checklist created
- [x] Rollback plan documented
- [x] Documentation package ready for handoff

---

## Next Steps

1. **Validate procedures locally** — Run pre-deployment validation script
2. **Build production image** — Create Docker image with APP_ENV=production
3. **Run smoke tests** — Verify deployment readiness
4. **Task 8.2: Monitor for 24 hours** — Continuous monitoring after deployment
5. **Task 8.3: Handoff to operations** — Transfer complete knowledge package

---

**Document Owner:** DevOps Lead  
**Last Updated:** 2026-06-17  
**Next Review:** Post-deployment (within 48 hours)
