# NEXUS Master Setup and Testing Guide

**Last Updated:** 2026-06-17  
**Status:** Production Ready  
**Audience:** Developers, DevOps, QA, Operators

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Complete Setup (30 minutes)](#complete-setup)
3. [Configuration Guide](#configuration-guide)
4. [Testing & Validation](#testing--validation)
5. [Feature Testing Checklist](#feature-testing-checklist)
6. [Troubleshooting](#troubleshooting)
7. [Deployment Paths](#deployment-paths)

---

## Quick Start

The fastest way to get NEXUS running with all features enabled.

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key (for live reasoning; optional but recommended)
- 30 seconds of setup time

### Steps

```bash
# 1. Clone/navigate to repository
cd /Users/kunalkachru/Documents/nexus-v3

# 2. Start with Docker (includes runtime host for demo playback)
export OPENAI_API_KEY=sk-proj-xxxxx  # Replace with your key
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh

# 3. Open browser
# → http://127.0.0.1:7860
```

**Expected output:**
```
Fresh container is ready.
CONTAINER ID   IMAGE     COMMAND           STATUS        PORTS
abc123def456   nexus     uvicorn ...       Up 2 seconds  0.0.0.0:7860->7860/tcp
```

### Verify It's Working

```bash
# Health check
curl http://127.0.0.1:7860/health
# Expected: {"status": "healthy", ...}
```

---

## Complete Setup

Detailed setup for development, testing, or production deployment.

### 1. Environment Setup

#### 1.1 Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 1.2 Node/Frontend Dependencies

```bash
# Install npm dependencies
npm install

# Verify installation
npm list @playwright/test
```

### 2. Configuration

#### 2.1 Create `.env` File

```bash
# Copy template
cp .env .env.local

# Edit with your values
nano .env.local
```

#### 2.2 Environment Variables

| Variable | Default | Purpose | Required? |
|----------|---------|---------|-----------|
| `OPENAI_API_KEY` | (none) | Enable live LLM reasoning | Recommended |
| `NEXUS_WEBHOOK_SIGNING_SECRET` | `nexus-demo-webhook-secret` | Webhook signature verification | ✅ |
| `NEXUS_ALLOWED_TENANT_IDS` | `tenant-a,tenant-system` | Allowed tenants | ✅ |
| `NEXUS_DATABASE_PATH` | `artifacts/nexus.db` | SQLite database location | ✅ |
| `NEXUS_FORGE_MODEL_NAME` | `gpt-4o` | LLM model for reasoning | Optional |
| `NEXUS_USE_OPENAI` | `1` | Enable OpenAI integration | Optional |
| `NEXUS_RUNTIME_HOST_BASE_URL` | `http://runtime-host:7860` | Runtime host URL (Docker) | For runtime relay |
| `NEXUS_RUNTIME_HOST_SHARED_TOKEN` | `nexus-runtime-host-token` | Auth token for runtime host | For runtime relay |
| `NEXUS_REPLICA_PACKS_ROOT` | `replica_packs` | Path to curated demo packs | For runtime relay |

**Complete `.env.local` example:**

```bash
# Core configuration
OPENAI_API_KEY=sk-proj-your-key-here
NEXUS_WEBHOOK_SIGNING_SECRET=your-webhook-secret
NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system,tenant-pilot-1
NEXUS_DATABASE_PATH=artifacts/nexus.db
NEXUS_FORGE_MODEL_NAME=gpt-4o
NEXUS_USE_OPENAI=1

# Runtime host (for demo playback)
NEXUS_RUNTIME_HOST_BASE_URL=http://runtime-host:7860
NEXUS_RUNTIME_HOST_SHARED_TOKEN=nexus-runtime-host-token
NEXUS_REPLICA_PACKS_ROOT=${PWD}/replica_packs

# Optional: for local development
NEXUS_RUNTIME_HTTP_HOST=127.0.0.1
```

### 3. Database Initialization

#### 3.1 Fresh Start

The database is automatically created on first run:

```bash
# When you first start the server, it creates:
# - artifacts/nexus.db (SQLite database)
# - Incident schema with indexes
# - Audit log schema with indexes

# Verify database
sqlite3 artifacts/nexus.db ".tables"
# Output: audit_logs incidents
```

#### 3.2 View Schema

```bash
# View incidents table
sqlite3 artifacts/nexus.db ".schema incidents"

# View audit_logs table
sqlite3 artifacts/nexus.db ".schema audit_logs"

# Check record counts
sqlite3 artifacts/nexus.db "SELECT COUNT(*) as incidents FROM incidents; SELECT COUNT(*) as audit_logs FROM audit_logs;"
```

### 4. Starting the Server

#### Option A: Docker (Recommended for Testing)

```bash
# Fresh build with all features
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh

# Or minimal (NEXUS only, no runtime host)
./scripts/docker_fresh.sh

# Check logs
docker compose logs -f nexus
```

#### Option B: Direct Python (Development)

```bash
# Activate venv first
source venv/bin/activate

# Start server
uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload

# Output should show:
# Uvicorn running on http://0.0.0.0:7860
# Application startup complete
```

#### Option C: Docker Compose (Custom)

```bash
# Start specific services
docker compose up nexus
docker compose up nexus runtime-host  # With demo playback

# In background
docker compose up -d nexus
```

### 5. Verify Services Are Running

```bash
# Health check
curl http://127.0.0.1:7860/health
# Expected: {"status": "healthy", "db": "connected", ...}

# Check runtime host (if enabled)
curl http://localhost:7860/health
# (Same health endpoint)

# View running containers
docker ps
```

---

## Configuration Guide

### Database Configuration

#### SQLite (Current, Production-Ready)

```python
# Automatically created in: artifacts/nexus.db
# Features:
# - Multi-tenant isolation (tenant_id in all queries)
# - Flexible JSON storage for incidents
# - Complete audit trail
# - Indexes for fast queries

# Connection verified automatically on startup
```

**Scaling considerations:**
- < 100K incidents: ✅ SQLite sufficient
- 100K - 1M incidents: ⚠️ Monitor performance
- > 1M incidents: Consider PostgreSQL migration (schema compatible)

#### Tenant Configuration

```bash
# Allow multiple tenants in .env
NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system,tenant-pilot-1,tenant-pilot-2

# Each tenant is completely isolated at the database level
# - All queries include tenant_id filter
# - Incidents from one tenant are never visible to another
# - Audit logs are tenant-scoped
```

### API Configuration

#### Webhook Configuration

```bash
# Set signing secret (must match caller's secret)
NEXUS_WEBHOOK_SIGNING_SECRET=your-secret-here

# Webhook endpoint: POST /incidents/webhook
# Required headers:
#   X-Webhook-Signature: sha256=<signature>
#   Content-Type: application/json
```

#### Authentication

```bash
# Token-based auth for runtime host relay
NEXUS_RUNTIME_HOST_SHARED_TOKEN=your-shared-token

# Client must send: Authorization: Bearer <token>
```

### LLM Configuration

#### With OpenAI (Recommended for Full Features)

```bash
OPENAI_API_KEY=sk-proj-your-key-here
NEXUS_USE_OPENAI=1
NEXUS_FORGE_MODEL_NAME=gpt-4o
```

**What works with OpenAI:**
- Live incident reasoning and triage
- Automated investigation generation
- TRACE debugging guidance
- Custom incident classification

#### Without OpenAI (Fallback Mode)

```bash
# Unset OPENAI_API_KEY or set to empty
OPENAI_API_KEY=
NEXUS_USE_OPENAI=0
```

**What works in fallback:**
- All demo bundled incidents
- UI navigation and incident viewing
- Handoff and audit surfaces
- All static content and runbooks

---

## Testing & Validation

### Run Full Test Suite

```bash
# Backend tests (410 total: 76 core + 334 production readiness/load/DR/ops training)
pytest tests/ -q
# Expected: 410 passed

# Browser tests (16 total)
npm run browser:verify
# Expected: 16 passed

# Combined test report
echo "=== Backend Tests ===" && pytest tests/ -q && echo "=== Browser Tests ===" && npm run browser:verify
```

### Run Subset of Tests

```bash
# Test specific area
pytest tests/test_api_contract.py -v

# Test with specific pattern
pytest -k "test_incident" -v

# Test with coverage
pytest --cov=server tests/

# Browser tests headed (see test run)
npm run browser:verify:headed
```

### Run Validation Scripts

```bash
# Pre-deployment validation
./scripts/pre-deployment-validation.sh

# Post-deployment health check
./scripts/post-deployment-health-check.sh

# Local enterprise smoke test
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

### Performance Testing

```bash
# Load test (concurrent users and requests)
pytest tests/load_test.py -v

# Expected results:
# - 100 concurrent submissions: p99 < 5000ms, throughput > 800 req/s
# - 100 concurrent views: p99 < 5000ms, throughput > 1000 req/s
# - Mixed 50+50: throughput > 700 req/s
```

### Disaster Recovery Testing

```bash
# Backup automation
./scripts/backup_nexus.sh

# Restore from backup
./scripts/restore_nexus.sh <backup-file.tar.gz>

# DR drill (simulates corruption and recovery)
pytest tests/test_dr_drill.py -v
# Expected: RTO < 1 second, 100% data recovery
```

---

## Feature Testing Checklist

Use this checklist to verify all functionality works end-to-end.

### Setup & Startup ✅

- [ ] Docker fresh build starts without errors
- [ ] Service health check returns 200 at `/health`
- [ ] Database initialized with schema
- [ ] All environment variables loaded
- [ ] OpenAI connection works (if configured)

### UI Navigation ✅

- [ ] `/queue` loads and shows seeded incidents
- [ ] `/inputs` loads with demo bundle picker
- [ ] `/incident?nexus_incident_id=INC001` shows incident details
- [ ] `/training` shows pilot scores and triage metrics
- [ ] `/settings` shows system configuration
- [ ] Navigation menu works on all pages
- [ ] Search/filter works on queue

### Fresh Log Intake ✅

- [ ] `/inputs` accepts demo bundle submission
- [ ] Create fresh `nxs_...` incident from logs
- [ ] New incident appears in `/queue`
- [ ] Incident lands at top of queue
- [ ] Incident shows top brief summary
- [ ] Can navigate into fresh incident details

### Five Incident Families ✅

Test each supported family:

- [ ] `INC001` - Checkout timeout / retry amplification
  - [ ] Title displays correctly
  - [ ] Root cause identified
  - [ ] Mitigation suggestions appear
  
- [ ] `INC002` - DB pool exhaustion / session leak
  - [ ] Title displays correctly
  - [ ] Root cause identified
  - [ ] Mitigation suggestions appear
  
- [ ] `INC003` - Deploy regression / 5xx spike
  - [ ] Title displays correctly
  - [ ] Root cause identified
  - [ ] Mitigation suggestions appear
  
- [ ] `INC005` - Queue / worker backlog
  - [ ] Title displays correctly
  - [ ] Root cause identified
  - [ ] Mitigation suggestions appear
  
- [ ] `INC007` - Auth dependency slowdown
  - [ ] Title displays correctly
  - [ ] Root cause identified
  - [ ] Mitigation suggestions appear

### Agent Pipeline (SENTINEL → GUARDIAN) ✅

- [ ] SENTINEL normalizes incoming logs
- [ ] PRISM triages and classifies incident
- [ ] REPLICA provides runtime replay (if demo pack)
- [ ] TRACE generates debugging guidance
- [ ] FORGE creates investigation narrative
- [ ] GUARDIAN approval gate enforces governance
- [ ] Show evidence of each agent output in UI

### GUARDIAN Approval Gate ✅

- [ ] Incidents enter pending review state
- [ ] GUARDIAN makes approve/reject decision
- [ ] Decision reason displays clearly
- [ ] Operators can override (if configured)
- [ ] Audit log records decision and reason
- [ ] Can view decision in incident details

### Handoff & Engineering Export ✅

- [ ] Engineering handoff packet can be generated
- [ ] Export contains all investigation evidence
- [ ] Export format is importable by engineering tools
- [ ] Audit log records export event
- [ ] Delivery tracking shows handoff status

### Observability & Metrics ✅

- [ ] Prometheus metrics endpoint at `/metrics`
- [ ] Key metrics present: incident_count, latency, errors
- [ ] Health endpoint returns system status
- [ ] Can query database for incident counts
- [ ] Audit logs record all operations

### Database Integrity ✅

- [ ] SQLite database file created at `artifacts/nexus.db`
- [ ] Multi-tenant isolation enforced
  - [ ] Incidents from tenant-a not visible to tenant-system
  - [ ] Queries include tenant_id filter
- [ ] Audit logs record all changes
- [ ] Can backup and restore database
- [ ] Database VACUUM and ANALYZE work

### Backup & Restore ✅

- [ ] `./scripts/backup_nexus.sh` creates backup
- [ ] Backup file is gzip compressed
- [ ] Can restore from backup
- [ ] Restored data is identical to original
- [ ] RTO is < 1 second

### Error Handling ✅

- [ ] 404 for missing incident
- [ ] 401 for invalid webhook signature
- [ ] 500 with clear error message for server errors
- [ ] Graceful handling of malformed JSON
- [ ] Database connection errors handled
- [ ] OpenAI timeout handled gracefully

### Security ✅

- [ ] Webhook signature verification enforced
- [ ] Tenant isolation prevents cross-tenant access
- [ ] Audit logs cannot be tampered with
- [ ] Secrets not logged or exposed
- [ ] CORS headers properly configured
- [ ] No SQL injection vulnerabilities

### Performance ✅

- [ ] Incident retrieval < 100ms
- [ ] Incident creation < 1 second
- [ ] Load test: 1000+ req/s sustainable
- [ ] Database queries use indexes
- [ ] No memory leaks (run for 1 hour)
- [ ] CPU usage stable under load

### Demo Packs ✅

- [ ] All 5 demo bundles available in `/inputs`
- [ ] Can submit each demo bundle
- [ ] Each creates correct incident family
- [ ] REPLICA plays back runtime scenario (if enabled)
- [ ] Evidence displays correctly

---

## Troubleshooting

### Service Won't Start

**Symptom:** Docker container crashes or won't start

```bash
# Check logs
docker compose logs nexus | tail -50

# Common issues:
# 1. Port 7860 already in use
lsof -i :7860
kill -9 <PID>

# 2. Database file locked
rm artifacts/nexus.db  # or restore from backup

# 3. Missing dependencies
pip install -r requirements.txt

# 4. Permission denied on scripts
chmod +x scripts/*.sh
```

### Health Check Fails

**Symptom:** `curl http://127.0.0.1:7860/health` returns error

```bash
# Check if service is running
docker ps | grep nexus

# Check logs
docker compose logs nexus | tail -20

# Restart service
docker compose restart nexus

# Wait for startup
sleep 5 && curl http://127.0.0.1:7860/health
```

### Database Corruption

**Symptom:** SQLite error or missing tables

```bash
# Verify schema
sqlite3 artifacts/nexus.db ".tables"

# If tables missing, restore from backup
./scripts/restore_nexus.sh <backup-file>

# Or start fresh (loses data)
rm artifacts/nexus.db
# Service will recreate on restart
```

### Tests Failing

**Symptom:** `pytest tests/ -q` shows failures

```bash
# Run with verbose output
pytest tests/ -vv --tb=short

# Run specific test
pytest tests/test_api_contract.py::test_incident_retrieval -vv

# Check dependencies
pip install -r requirements.txt

# Ensure database is clean
rm artifacts/nexus.db
pytest tests/ -q
```

### OpenAI Connection Issues

**Symptom:** Slow responses or API errors from OpenAI

```bash
# Check API key
echo $OPENAI_API_KEY

# Test connection
python -c "import openai; openai.api_key='${OPENAI_API_KEY}'; print(openai.Model.list()[:1])"

# Check rate limits
# If rate limited, wait 30 seconds and retry

# Fallback to non-OpenAI mode
unset OPENAI_API_KEY
```

### Multi-Tenant Issues

**Symptom:** Incidents from wrong tenant visible

```bash
# Verify tenant configuration
grep NEXUS_ALLOWED_TENANT_IDS .env

# Check incident tenant_id
sqlite3 artifacts/nexus.db "SELECT DISTINCT tenant_id FROM incidents;"

# Verify queries include tenant filter
grep -r "WHERE.*tenant_id" server/

# Test with specific tenant
curl -H "X-Tenant-ID: tenant-a" http://127.0.0.1:7860/incidents
```

### Webhook Rejections

**Symptom:** POST to `/incidents/webhook` returns 401

```bash
# Verify webhook secret matches
echo $NEXUS_WEBHOOK_SIGNING_SECRET

# Test webhook manually
python -c "
import hmac
import hashlib
import json

secret = 'your-secret'
payload = json.dumps({'test': True})
signature = hmac.new(
    secret.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()

print(f'X-Webhook-Signature: sha256={signature}')
"

# Send test webhook
curl -X POST http://127.0.0.1:7860/incidents/webhook \
  -H "X-Webhook-Signature: sha256=<signature>" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Slow Responses

**Symptom:** API responses > 1 second

```bash
# Check database performance
sqlite3 artifacts/nexus.db "ANALYZE;"
sqlite3 artifacts/nexus.db "VACUUM;"

# Check system resources
top -b -n 1 | grep nexus
free -h

# Check query plans
sqlite3 artifacts/nexus.db "EXPLAIN QUERY PLAN SELECT * FROM incidents WHERE tenant_id='tenant-a';"

# If using many incidents, consider archiving old ones
# See Database Growth section in TROUBLESHOOTING_GUIDE.md
```

---

## Deployment Paths

### Local Development

```bash
# Direct Python with reload
source venv/bin/activate
uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload

# Docker for testing
./scripts/docker_fresh.sh

# With runtime host for demo playback
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

### Staging/Pre-Production

```bash
# Full validation before production
./scripts/pre-deployment-validation.sh

# Run full test suite
pytest tests/ -q
npm run browser:verify

# Run load tests
pytest tests/load_test.py

# Run DR drill
pytest tests/test_dr_drill.py

# Full smoke test
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

### Production (Cloud Deployment)

```bash
# Build production image
docker build -t nexus:latest --build-arg APP_ENV=product .

# Push to registry
docker tag nexus:latest gcr.io/project/nexus:latest
docker push gcr.io/project/nexus:latest

# Deploy with Kubernetes/Docker Compose
# See docs/internal/production-deployment-guide.md for detailed procedures

# Monitor health
curl https://production-nexus.example.com/health

# Backup before any major changes
./scripts/backup_nexus.sh
```

### Pilot Deployment

```bash
# Setup for pilot customer
1. Run full pre-deployment validation
2. Set pilot tenant IDs in NEXUS_ALLOWED_TENANT_IDS
3. Deploy to staging environment
4. Run ops team training (docs/internal/ops-team-training-guide.md)
5. Execute 24-hour monitoring (docs/internal/monitoring-playbook-24hr.md)
6. Deploy to production
7. Monitor with alert procedures (docs/internal/alert-response-procedures.md)
```

---

## Verification Checklist Before Going Live

- [ ] **All 410 backend tests passing:** `pytest tests/ -q` (76 core + 334 production readiness)
- [ ] **All 16 browser tests passing:** `npm run browser:verify`
- [ ] **Load test baseline met:** `pytest tests/load_test.py`
- [ ] **DR drill successful:** `pytest tests/test_dr_drill.py`
- [ ] **Security review passed:** All 7 checks in `docs/security-review-checklist.md`
- [ ] **All 5 incident families testable** in UI
- [ ] **Demo packs render correctly** in `/inputs`
- [ ] **Backup/restore working:** `./scripts/backup_nexus.sh && ./scripts/restore_nexus.sh`
- [ ] **Webhook authentication working** with correct signature
- [ ] **Multi-tenant isolation verified** (incidents properly scoped)
- [ ] **Database scaling plan** documented (SQLite or PostgreSQL upgrade path)
- [ ] **Monitoring configured** (Prometheus metrics, Grafana dashboards)
- [ ] **Alerting configured** (Alert rules in `prometheus/alerts.yml`)
- [ ] **Runbooks accessible** (All 6 in `docs/runbooks/`)
- [ ] **Ops team trained** (Training guide in `docs/internal/`)
- [ ] **24-hour monitoring plan** documented
- [ ] **Handoff procedures** prepared

---

## Getting Help

| Issue Type | Resource |
|-----------|----------|
| Setup questions | See [Configuration Guide](#configuration-guide) |
| Test failures | See [Troubleshooting](#troubleshooting) |
| Feature not working | See [Feature Testing Checklist](#feature-testing-checklist) |
| Production issues | See [TROUBLESHOOTING_GUIDE.md](docs/TROUBLESHOOTING_GUIDE.md) |
| Operations | See [docs/internal/OPERATOR_RUNBOOK.md](docs/internal/OPERATOR_RUNBOOK.md) |
| Database schema | See [DATABASE.md](docs/DATABASE.md) |

---

## Document Status

- **Version:** 1.0
- **Last Updated:** 2026-06-17
- **Status:** Complete and Verified
- **Test Coverage:** 76 backend + 16 browser tests all passing
- **Production Ready:** Yes

---

**Next Steps:**

1. Run: `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh`
2. Navigate to: http://127.0.0.1:7860
3. Follow the demo guide: [MASTER_OPERATOR_DEMO_GUIDE.md](docs/public/MASTER_OPERATOR_DEMO_GUIDE.md)
4. Validate functionality using [Feature Testing Checklist](#feature-testing-checklist)
