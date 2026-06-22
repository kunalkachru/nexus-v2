# NEXUS — Master Developer Guide

Everything you need to set up locally, run the full test suite, and deploy to production.

---

## QUICK REFERENCE

| Environment | URL | Auto-deploys on |
|---|---|---|
| Local dev | http://localhost:7860 | Manual |
| Oracle Cloud (Production) | https://nexus-triage.duckdns.org | git push origin master |
| Render (Demo) | https://nexus-uny5.onrender.com | git push origin master |

**Test baseline:** 470 tests passing  
**GitHub repo:** https://github.com/kunalkachru/nexus-v2  
**Oracle Cloud server:** 92.5.47.239 (SSH key: ~/Downloads/ssh-key-2026-06-19.key)

---

## PART 1 — LOCAL SETUP (first time only)

### Prerequisites
- Python 3.11+ — check with: `python3 --version`
- Node.js 18+ — check with: `node --version`
- Docker Desktop — download from docker.com if not installed
- Git — check with: `git --version`

### Step 1 — Clone the repo
```bash
git clone https://github.com/kunalkachru/nexus-v2.git
cd nexus-v2
```

### Step 2 — Create Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3 — Install Node dependencies
```bash
npm install
npx playwright install chromium
```

### Step 4 — Set up environment variables
```bash
cp .env.example .env
```

### Step 5 — Start the server
```bash
source venv/bin/activate
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
```

Open http://localhost:7860/queue to confirm it works.

---

## PART 2 — RUNNING THE APP LOCALLY

### Option A — Docker (recommended, clean environment)

The fastest way to run NEXUS locally without managing Python dependencies:

**Standard run:**
```bash
./scripts/docker_fresh.sh
```

**With REPLICA runtime replay (enables 🟢 runtime-backed evidence posture):**
```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

The script stops any existing containers, prunes the Docker build cache, rebuilds the image from scratch, and waits for the health check to pass before exiting. Once complete, open http://127.0.0.1:7860/queue.

Environment variables accepted by docker_fresh.sh:

| Variable | Default | Effect |
|---|---|---|
| ENABLE_RUNTIME_HOST_RELAY | 0 | Set to 1 to enable REPLICA runtime replay |
| NO_CACHE | 1 | Set to 0 to use Docker layer cache (faster rebuilds) |
| HOST | 127.0.0.1 | Host to health-check against |
| PORT | 7860 | Port to health-check against |

**Stop all containers:**
```bash
docker compose down
```

### Option B — Python direct (for active development)

### Start the server (every session)
```bash
cd nexus-v2
source venv/bin/activate
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
```

### Key URLs
| Page | URL |
|---|---|
| Command Center | http://localhost:7860/queue |
| Submit incident | http://localhost:7860/inputs |
| Incident detail | http://localhost:7860/incident?nexus_incident_id=INC001 |
| Training dashboard | http://localhost:7860/training |
| Health check | http://localhost:7860/health |

---

## PART 3 — RUNNING ALL TESTS

### Full Python test suite
```bash
source venv/bin/activate
pytest tests/ -q
```
Expected: 470 passed

### Browser tests (server must be running)
```bash
npm run browser:verify
```
Expected: 16 passed

### Deep enterprise smoke tests (requires server running)

The enterprise smoke script runs 10-12 deeper checks including API contract verification, FORGE reasoning quality, GUARDIAN posture, TRACE fields, and memory enrichment:

```bash
# Basic smoke (10 checks, no relay)
BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh

# Full smoke with runtime relay verification (12 checks, requires ENABLE_RUNTIME_HOST_RELAY=1)
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

Expected output: `=== All smoke checks passed ===`

These tests verify deeper product correctness than the unit or browser tests — they check that INC001/INC002 FORGE reasoning cites runtime outcomes, GUARDIAN confidence is non-zero, TRACE inspection points are substantive, and memory enrichment runbooks have why_now_fit notes.

### Smoke tests against any environment
```bash
bash scripts/test-live.sh http://localhost:7860
bash scripts/test-live.sh https://nexus-triage.duckdns.org
bash scripts/test-live.sh https://nexus-uny5.onrender.com
```

---

## PART 4 — RELEASE GATE (pre-deployment verification)

**Run before any deployment, pilot handoff, or major release.**

The release gate is the single source of truth for "is NEXUS ready?"

### Run the release gate
```bash
bash scripts/run-release-gate.sh
```

Expected output (runtime: ~2-3 minutes):
```
✅ NEXUS RELEASE GATE: PASSED
   Ready for deployment/pilot
```

### What the release gate checks

| Section | What it verifies | Pass threshold |
|---------|---|---|
| 1. Unit tests | All 470 tests pass | 470/470 ✅ |
| 2. Server startup | FastAPI server healthy | Responds within 30s |
| 3. API contracts | Health, pages, webhooks, auth | 10/10 endpoints |
| 4. Browser sim | Scroll depth, viewport clarity, approval flow | Visual verification |
| 5. Production | Live server health check | nexus-triage.duckdns.org responding |
| 6. Security | Webhook signatures, no data leaks | 3/3 checks pass |

### Exit codes

- **Exit 0** = Gate PASSED, safe to deploy
- **Exit 1** = Gate FAILED, do not deploy

### Typical failure reasons

- Unit test count < 470 → fix the failing test
- Server won't start → check port 7861 not in use
- API tests fail → check endpoint paths and auth
- Browser tests fail → check Playwright install
- Production unreachable → wait for network/infrastructure

### Next step after passing

```bash
git add -A
git commit -m "chore: pre-deployment verification passed"
git push origin master
# Then verify in production (see PART 5)
```

---

## PART 5 — DEPLOYING TO CLOUD

Every `git push origin master` automatically deploys to both Render and Oracle Cloud.

### Check deploy status
- Render: https://dashboard.render.com
- Oracle Cloud: https://github.com/kunalkachru/nexus-v2/actions

### Manual deploy to Oracle Cloud
```bash
NEXUS_WEBHOOK_SIGNING_SECRET=your-secret-here bash scripts/deploy-oracle.sh
```

To retrieve your webhook secret: go to https://github.com/kunalkachru/nexus-v2/settings/secrets/actions and find ORACLE_WEBHOOK_SECRET.

### Verify after deploy
```bash
curl https://nexus-triage.duckdns.org/health
curl https://nexus-uny5.onrender.com/health
```

---

## PART 6 — SSH INTO ORACLE CLOUD

```bash
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
```

### Useful server commands
```bash
sudo docker ps
sudo docker logs nexus -f
sudo docker restart nexus
df -h
free -h
```

---

## PART 7 — STANDARD CODE CHANGE WORKFLOW

```bash
source venv/bin/activate
# make changes
pytest tests/ -q
git add -A
git commit -m "your message"
git push origin master
# wait 5 minutes then verify:
bash scripts/test-live.sh https://nexus-triage.duckdns.org
```

---

## PART 8 — TROUBLESHOOTING

### Port 7860 already in use
```bash
kill -9 $(lsof -ti:7860)
```

### Tests failing
```bash
pytest tests/ -v --tb=short
```

### Container not running on Oracle Cloud
```bash
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
sudo docker logs nexus --tail=50
sudo docker restart nexus
```

### GitHub Actions failing
Go to https://github.com/kunalkachru/nexus-v2/actions and check the error. Most common cause: ORACLE_SSH_KEY secret needs refreshing.

---

## PART 9 — ENVIRONMENT VARIABLES

| Variable | Default | Description |
|---|---|---|
| NEXUS_DATABASE_PATH | artifacts/incidents.json | SQLite location |
| NEXUS_ALLOWED_TENANT_IDS | tenant-a,tenant-system | Allowed tenants |
| NEXUS_USE_OPENAI | 0 | Set to 1 for live LLM |
| OPENAI_API_KEY | (blank) | Required if USE_OPENAI=1 |
| APP_ENV | demo | Set to production for strict validation |

---

## PART 10 — KEY FILES

| File | Purpose |
|---|---|
| server/app.py | FastAPI entry point |
| server/agents/ | All 6 agents |
| frontend/ | UI files |
| tests/ | 470 tests |
| scripts/deploy-oracle.sh | Manual deploy |
| scripts/test-live.sh | Smoke tests |
| .github/workflows/deploy.yml | CI/CD |
| docs/CICD.md | Deployment docs |
| AGENTS.md | Claude Code rules |

---

## PART 11 — PRE-DEMO CHECKLIST

Run 5 minutes before any demo:

```bash
# Wake up Render
curl https://nexus-uny5.onrender.com/health

# Verify Oracle Cloud
curl https://nexus-triage.duckdns.org/health
```

Open in incognito: https://nexus-triage.duckdns.org/queue

**Demo flow:**
1. /queue — show Command Center with 5 incidents
2. Click INC001 — show agent timeline and evidence posture
3. Expand a collapsed section — show progressive disclosure
4. Show Guardian approval flow
5. Show /training dashboard
