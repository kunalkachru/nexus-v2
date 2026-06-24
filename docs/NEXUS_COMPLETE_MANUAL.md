# NEXUS — Complete User and Operator Manual
# Version: Post-Sprint, June 2026
# Production URL: https://nexus-triage.duckdns.org

---

## WHAT THIS DOCUMENT IS

This is the single reference for everything you need to:
- Set up NEXUS locally from scratch
- Understand every screen and what it does
- Test every feature manually yourself
- Know exactly what to expect at each step
- Configure the system for different environments

Read it top to bottom once. Then use it as a reference when you're not sure what something should do.

---

## PART 1 — SETUP

### 1.1 Local Setup (first time only)

**Prerequisites — confirm these first:**
```bash
python3 --version    # must be 3.11 or higher
node --version       # must be 18 or higher
git --version        # any recent version
```

**Clone and install:**
```bash
git clone https://github.com/kunalkachru/nexus-v2.git
cd nexus-v2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm install
npx playwright install chromium
```

**Configure environment:**
```bash
cp .env.example .env
```
The default `.env` values work for local development. No changes needed unless you want live OpenAI reasoning (see Section 1.3).

**Start the server:**
```bash
source venv/bin/activate
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
```

**Verify it's running:**
Open http://localhost:7860/health in your browser.
Expected: `{"status": "ok"}`

---

### 1.2 Environment Variables Reference

| Variable | Default | What it does |
|---|---|---|
| NEXUS_DATABASE_PATH | artifacts/incidents.json | Where SQLite database lives |
| NEXUS_ALLOWED_TENANT_IDS | tenant-a,tenant-system | Comma-separated allowed tenant IDs |
| NEXUS_FORGE_MODEL_NAME | gpt-4o | OpenAI model used when live reasoning enabled |
| NEXUS_USE_OPENAI | 0 | Set to 1 to enable live LLM reasoning |
| OPENAI_API_KEY | (blank) | Required only if NEXUS_USE_OPENAI=1 |
| NEXUS_WEBHOOK_SIGNING_SECRET | nexus-demo-webhook-secret | HMAC secret for webhook signature verification |
| APP_ENV | demo | Set to 'production' for strict tenant validation at startup |
| NEXUS_ALLOWED_ORIGINS | localhost:7860, etc | Comma-separated CORS allowed origins |
| NEXUS_MAX_REQUEST_SIZE_BYTES | 1048576 | Max request body size (1MB default) |

---

### 1.3 Enabling Live OpenAI Reasoning

By default NEXUS uses deterministic fallback (no API calls, no cost). To enable live reasoning:

1. Get an OpenAI API key from https://platform.openai.com/api-keys
2. Open `.env` and set:
   ```
   OPENAI_API_KEY=sk-proj-your-real-key-here
   NEXUS_USE_OPENAI=1
   ```
3. Restart the server

What changes with live reasoning enabled:
- FORGE agent generates real narrative recommendations using GPT-4o instead of template text
- TRACE agent generates debugging checklists for arbitrary incident types
- Evidence posture may show "validated_runtime" instead of "inferred_only" for supported families

---

### 1.4 Production Deployment Access

| Environment | URL | Notes |
|---|---|---|
| Production (Oracle Cloud) | https://nexus-triage.duckdns.org | Always on, persistent database |
| Demo (Render) | https://nexus-uny5.onrender.com | Sleeps after 15min inactivity, no persistent disk |
| Local | http://localhost:7860 | Requires server running |

**API authentication headers (required on all API calls):**
```
X-Tenant-ID: tenant-a
X-User-ID: your-name
```

---

### 1.5 Running with Docker (alternative to Python setup)

If you have Docker Desktop installed and don't want to manage a Python virtual environment:

**Quick start:**
```bash
./scripts/docker_fresh.sh
```

**With REPLICA runtime replay:**
```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Open http://127.0.0.1:7860/queue once the script prints "Fresh container is ready."

**Stop:**
```bash
docker compose down
```

This is equivalent to the Python direct run but uses the same Docker container as the production deployment, making it a closer approximation of production behavior.

### 1.6 Architecture Reference

For a visual understanding of how NEXUS works internally, see the architecture documentation:

- **[System Overview](architecture/01-system-overview.md)** —
  how external inputs flow through the 6-agent pipeline to outputs
- **[Agent Pipeline Detail](architecture/02-agent-pipeline.md)** —
  what each agent receives, processes, and produces
- **[Data Flow Diagrams](architecture/03-data-flow.md)** —
  sequence diagrams for fresh incident submission, webhook ingestion,
  and Guardian approval loops
- **[Deployment Architecture](architecture/05-deployment.md)** —
  Oracle Cloud VM, nginx reverse proxy, Docker, SSL, CI/CD pipeline
- **[Sequence Diagrams](architecture/06-sequence-diagrams.md)** —
  step-by-step user journeys (pilot customer first incident, webhook flow, rejections)

See [docs/architecture/README.md](architecture/README.md) for the complete index.

---

## PART 2 — THE FIVE SCREENS

### 2.1 Command Center (/queue)

**What it is:** The landing page and main navigation hub. Shows the active incident, agent crew status, and navigation paths.

**What you see:**
- Hero section with active incident stats (incident ID, current stage, urgency, SLA timer)
- Agent crew strip (SENTINEL, PRISM, FORGE, GUARDIAN cards showing current state)
- Navigation links to start a fresh incident or open a seeded demo
- Collapsed sections: "Choose your path", "Recent incident rail", "Expand queue internals"

**What the collapsed sections contain:**
- **Choose your path** (▸ click to expand): Cards to start from raw logs OR open the strongest seeded incident. Shows the 5 supported incident families as a selectable list.
- **Recent incident rail** (▸ click to expand): Quick links to all 5 seeded incidents for comparison.
- **Expand queue internals** (▸ click to expand): Deep metrics — open incidents count, SLA at risk, primary source, last update, bottleneck.

**Onboarding banner:** On first visit, a dismissible banner explains the 5 demo incidents and links to /inputs. Clicking the ✕ dismisses it permanently (stored in localStorage).

**Manual test steps:**
1. Open https://nexus-triage.duckdns.org/queue
2. Confirm the onboarding banner appears if you've never visited before (try incognito to force it)
3. Click the ✕ on the banner — it disappears
4. Refresh the page — banner should NOT reappear
5. Click "Choose your path" section — it should expand with a rotating chevron
6. Confirm hint text and preview tags are visible before expanding
7. Click "Open incident detail" — should navigate to INC001 detail page
8. Click "Start from raw logs" — should navigate to /inputs

**Expected behavior at every step:**
- Banner: appears on first visit, dismissed permanently on click ✓
- Chevron: rotates 90° when section opens, rotates back when closed ✓
- Hint text: visible below each section title even when collapsed ✓
- Navigation: all links work, no 404 errors ✓

---

### 2.2 Incident Detail (/incident?nexus_incident_id=INC001)

**What it is:** The core investigation view for a single incident. Shows the complete agent investigation pipeline and Guardian approval workflow.

**What you see (always visible, no scrolling needed):**
- Incident header: ID, severity badge, family classification
- Hero stats: stage, evidence posture badge (🟢 runtime-backed / 🟡 inference-first / 🔴 unsupported), SLA, source
- Agent progress grid: 3-column layout showing all 6 agents and their current state
- **Guardian Gate card** (first card below hero): approval buttons (Approve / Reject / Escalate)
- Agent flow caption: "SENTINEL classifies → PRISM diagnoses → REPLICA reproduces → TRACE debugs → FORGE recommends → GUARDIAN approves"

**What the collapsed sections contain:**
- **Investigation Summary & Operator Path** (▸): Full diagnosis thread from classification to recommendation. Root cause, evidence chain, mitigation options.
- **Agent Relay & Crew Details** (▸): Full agent crew status, orchestration flow, BYO OpenAI key configuration.
- **Enterprise Task Board** (▸): Runtime posture details, recommended action, enterprise metrics, runtime comparison (baseline vs mitigated).
- **Expand technical detail** (▸): Raw input evidence, system logs, audit ledger, technical deep-dive.

**The 5 seeded incidents and what they demonstrate:**

| Incident | Family | What to look for |
|---|---|---|
| INC001 | Checkout timeout / retry amplification | Strongest bounded story. Shows runtime replay, TRACE debugging steps, complete Guardian flow |
| INC002 | DB pool exhaustion / session leak | Shows pool metrics, connection analysis, mitigation options |
| INC003 | Deploy regression / 5xx spike | Shows correlation between deploy time and error spike |
| INC005 | Queue / worker backlog | Shows queue depth analysis, worker capacity metrics |
| INC007 | Auth dependency slowdown | Shows auth latency correlation, token validation analysis |

**Manual test steps:**
1. Open https://nexus-triage.duckdns.org/incident?nexus_incident_id=INC001
2. Confirm the page loads with the agent timeline visible in the first viewport (no scrolling needed)
3. Confirm the Guardian Gate card with Approve/Reject/Escalate buttons is visible without scrolling
4. Click "Approve" — confirm the button processes and shows confirmation
5. Reload the page — confirm the approval state persists (buttons gone or approved state shown)
6. Click "Investigation Summary & Operator Path" — confirm it expands with rotating chevron
7. Click "Agent Relay & Crew Details" — confirm it expands, shows all 6 agents
8. Click "Enterprise Task Board" — confirm it expands, shows runtime comparison
9. Navigate back to queue using browser back button or nav link — confirm navigation works

**Evidence posture — what each means:**
- 🟢 **runtime-backed**: REPLICA reproduced this incident in a Docker sandbox. Highest confidence.
- 🟡 **inference-first**: PRISM diagnosed this from logs and patterns. AI-inferred, no reproduction.
- 🔴 **unsupported**: Does not match any supported family. Manual investigation required.

**Expected behavior at every step:**
- Agent timeline: visible in first viewport without scrolling ✓
- Guardian buttons: visible without scrolling, above all collapsed sections ✓
- Approval: persists across page reload ✓
- Collapsed sections: expand/collapse with animated chevron ✓
- Back navigation: returns to queue cleanly ✓

---

### 2.3 Raw Incident Intake (/inputs)

**What it is:** Where you submit a fresh, real incident for NEXUS to investigate.

**What you see:**
- Supported incident families list (5 families with descriptions, always visible)
- Input channels: Raw text, Demo bundle, API webhook
- Text area for incident description
- Submit button

**How to submit a real incident:**
1. Navigate to https://nexus-triage.duckdns.org/inputs
2. Read the 5 supported family descriptions to understand what symptoms to describe
3. In the text area, describe your incident symptoms in plain English. Example:
   ```
   Database connection pool exhausted. All 50 connections in use.
   New requests timing out after 30 seconds. Error: "connection pool
   timeout after 30000ms". Started at 14:32 UTC, coinciding with
   deployment of auth-service v2.3.1.
   ```
4. Click Submit
5. The page navigates immediately to the new incident detail page (no delay)

**What happens after submission:**
- SENTINEL classifies the incident against the 5 supported families
- If matched: investigation proceeds through PRISM → REPLICA → TRACE → FORGE → GUARDIAN
- If not matched: structured error message listing the 5 supported families appears inline

**Manual test steps:**
1. Go to /inputs
2. Confirm the 5 family descriptions are visible before scrolling
3. Submit an empty form — confirm inline error appears, submit button re-enables
4. Submit a valid incident description — confirm navigation to new incident page
5. Check the new incident's URL contains `nexus_incident_id=nxs_...`
6. Submit an unsupported incident ("The office printer is broken") — confirm structured error listing 5 families
7. Confirm no 500 error page appears for unsupported incident

**Expected behavior:**
- Navigation: happens immediately after API responds, no 100ms delay ✓
- Error state: inline on the page, not a browser alert ✓
- Submit button: disabled during submission, re-enables on error ✓
- Unsupported family: structured message listing 5 families, not a generic error ✓

---

### 2.4 Training / Learning & Controls (/training)

**What it is:** The pilot metrics dashboard showing real computed metrics from your actual usage.

**What you see (always visible):**
- Pilot scorecard with real metrics (incidents handled, runtime-backed count, time saved)
- computed_at timestamp showing when metrics were last calculated
- Agent crew performance strip

**What the collapsed sections contain:**
- **Last live triage in this browser** (▸): Most recent incident triage session context
- **Operational Metrics & Health** (▸): Detailed health metrics, deployment readiness status
- **Learning & Governance** (▸): Training progress, governance policies, approval rate history

**Important:** If you haven't submitted any real incidents yet, the scorecard shows zeros or demo values. Submit real incidents via /inputs to see your actual metrics.

**Manual test steps:**
1. Open https://nexus-triage.duckdns.org/training
2. Check the pilot scorecard — does `incidents_handled` reflect the actual number of incidents you've submitted?
3. Check that `computed_at` shows a recent timestamp (not a hardcoded date)
4. Submit a new incident via /inputs, then return to /training
5. Confirm `incidents_handled` increased by 1
6. Expand "Operational Metrics & Health" — confirm it shows real system status
7. Expand "Learning & Governance" — confirm governance policies are visible

**Expected behavior:**
- Scorecard: computed from real database records, not hardcoded values ✓
- computed_at: updates on each call ✓
- incidents_handled: increases when you submit new incidents ✓

---

### 2.5 Health Check (/health)

**What it is:** Simple endpoint confirming the server is running.

**Expected response:**
```json
{"status": "ok"}
```

Use this before any demo to confirm the server is live:
```bash
curl https://nexus-triage.duckdns.org/health
```

---

## PART 3 — THE SIX AGENTS

### 3.1 SENTINEL — Classification Agent

**What it does:** Takes raw incident text and classifies it against the 5 supported families using a scored catalogue. Outputs a classification with confidence score.

**How confidence is calculated:** Best-match score vs runner-up score gap. Wide gap = high confidence. Narrow gap = low confidence.

**What it produces:** Incident family label, confidence score (0-1), evidence extracted from the input text.

**When it runs:** Immediately on incident submission via /inputs or webhook.

**Test it:**
Submit this text via /inputs:
```
Checkout service timeout rate spiked to 45%. Retry logic is amplifying the problem.
P99 latency went from 120ms to 8400ms. Started 20 minutes ago.
```
Expected: Classified as "checkout_timeout", high confidence.

---

### 3.2 PRISM — Diagnosis Agent

**What it does:** Takes SENTINEL's classification and runs a diagnosis. Identifies the specific failure mechanism, contributing factors, and most likely root cause.

**Two paths:**
- Deterministic (NEXUS_USE_OPENAI=0): Uses curated diagnosis catalogue for the 5 families
- Live LLM (NEXUS_USE_OPENAI=1): Uses OpenAI to generate diagnosis based on SENTINEL output

**What it produces:** Root cause hypothesis, contributing factors, evidence mapped to the hypothesis, confidence in diagnosis.

**Test it:** Open INC001 and expand "Investigation Summary" — PRISM's diagnosis appears as the first section of the investigation thread.

---

### 3.3 REPLICA — Runtime Reproduction Agent

**What it does:** Attempts to reproduce the incident in a Docker sandbox using curated environment packs for each of the 5 families.

**Important limitation on cloud deployment:** REPLICA requires Docker-in-Docker, which is not available on the Oracle Cloud free tier. On the cloud deployment, REPLICA returns "inferred_only" posture (inference-first evidence badge). On a self-hosted deployment with Docker available, REPLICA can run actual reproduction.

**What it produces:** Evidence posture (runtime_backed or inferred_only), reproduction timeline if successful, bounded replay artifacts.

**Test it:** Open INC001 and look at the evidence posture badge in the hero section. On the cloud deployment you'll see 🟡 inference-first. On a local deployment with Docker available you'd see 🟢 runtime-backed.

---

### 3.4 TRACE — Debugging Agent

**What it does:** Generates a structured debugging checklist for operators to follow. For the 5 supported families, uses curated debugging packs. For arbitrary incidents with NEXUS_USE_OPENAI=1, uses OpenAI to generate a custom checklist.

**What it produces:** Ordered list of debugging steps, each with expected outcome and what to do if it fails.

**Test it:** Open any seeded incident and expand "Investigation Summary" — the TRACE debugging steps appear in the operator path section.

---

### 3.5 FORGE — Remediation Agent

**What it does:** Produces the recommended remediation action — a runbook or rollback procedure the operator can execute after Guardian approval.

**Two modes:**
- Deterministic (NEXUS_USE_OPENAI=0): Template-based recommendation for the matched family
- Live LLM (NEXUS_USE_OPENAI=1): GPT-4o generated narrative recommendation

**What it produces:** Recommended action description, risk level, estimated time, rollback plan.

**Test it:** Open INC001, look at the Guardian Gate card — the recommended action is displayed there for Guardian to review before approving.

---

### 3.6 GUARDIAN — Governance Agent

**What it does:** The human governance gate. Receives FORGE's recommendation and presents it to a human operator who must explicitly Approve, Reject, or Escalate before any action is taken.

**Three actions:**
- **Approve**: Confirms the recommended action is safe to execute. State persists in database.
- **Reject**: Records that the recommendation was reviewed and rejected. Incident stays open.
- **Escalate**: Routes to senior on-call or engineering lead for review.

**Important:** GUARDIAN never takes action autonomously. The human operator is always the final decision maker.

**Test the full flow:**
1. Open https://nexus-triage.duckdns.org/incident?nexus_incident_id=INC001
2. Find the Guardian Gate card (visible without scrolling)
3. Click "Approve"
4. Reload the page
5. Confirm the approval state persisted (button state shows approved)

---

## PART 4 — API REFERENCE

### 4.1 Key Endpoints

All API calls require headers:
```
X-Tenant-ID: tenant-a
X-User-ID: your-name
X-Roles: operator
Content-Type: application/json
```

The `X-Roles` header is required for all write operations (creating, updating, approving incidents). Valid roles: `operator`, `incident_manager`, `guardian`, `admin`.

**Submit a fresh incident:**
```bash
curl -X POST https://nexus-triage.duckdns.org/api/v1/incidents/raw-text \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-a" \
  -H "X-User-ID: test-user" \
  -H "X-Roles: operator" \
  -d '{"raw_text": "Database connection pool exhausted, all 50 connections in use"}'
```
Expected: `{"nexus_incident_id": "nxs_...", "status": "created"}`

**Get incident queue:**
```bash
curl https://nexus-triage.duckdns.org/api/v1/incidents/queue \
  -H "X-Tenant-ID: tenant-a" \
  -H "X-User-ID: test-user" \
  -H "X-Roles: operator"
```
Expected: JSON array of incidents

**Get pilot scorecard:**
```bash
curl https://nexus-triage.duckdns.org/api/v1/tenant/pilot-scorecard \
  -H "X-Tenant-ID: tenant-a" \
  -H "X-User-ID: test-user" \
  -H "X-Roles: operator"
```
Expected: JSON with `incidents_handled`, `incidents_runtime_backed`, `computed_at`

**Health check:**
```bash
curl https://nexus-triage.duckdns.org/health
```
Expected: `{"status": "ok"}`

**Full API documentation:**
Open https://nexus-triage.duckdns.org/docs in your browser — FastAPI auto-generated OpenAPI docs with all 30+ endpoints documented.

---

### 4.2 Webhook Ingestion

NEXUS accepts incidents via webhook with HMAC-SHA256 signature verification.

**Required headers:**
```
X-Signature: hmac-sha256=<signature>
X-Tenant-ID: tenant-a
Content-Type: application/json
```

**Signature calculation:**
```python
import hmac, hashlib
secret = "nexus-demo-webhook-secret"  # or your configured secret
payload = '{"raw_text": "your incident text"}'
signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
header_value = f"hmac-sha256={signature}"
```

**Test webhook security:**
```bash
# Missing signature — should return 401
curl -X POST https://nexus-triage.duckdns.org/webhooks/incident \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-a" \
  -d '{"raw_text": "test"}' 
```
Expected: 401 Unauthorized

---

## PART 5 — COMPLETE MANUAL TEST WALKTHROUGH

Run these in order. Each one verifies a specific piece of functionality. Takes about 20-30 minutes total.

### Test 1 — Server is alive
```bash
curl https://nexus-triage.duckdns.org/health
```
✅ Expected: `{"status":"ok"}`
❌ If fails: Server is down. Check Oracle Cloud console.

---

### Test 2 — All three pages load
Open each URL and confirm the page loads with content:
- https://nexus-triage.duckdns.org/queue ✅ Should show Command Center with NEXUS branding
- https://nexus-triage.duckdns.org/incident?nexus_incident_id=INC001 ✅ Should show incident detail with agent grid
- https://nexus-triage.duckdns.org/training ✅ Should show pilot scorecard
- https://nexus-triage.duckdns.org/inputs ✅ Should show intake form with 5 family descriptions

---

### Test 3 — Onboarding banner
1. Open https://nexus-triage.duckdns.org/queue in an **incognito window**
✅ Expected: Welcome banner appears at top of page
2. Click the ✕ button on the banner
✅ Expected: Banner disappears immediately
3. Refresh the page
✅ Expected: Banner does NOT reappear
❌ If banner reappears: localStorage not working or banner dismiss logic broken

---

### Test 4 — Collapsed sections are intuitive
On the queue page:
1. Look at "Choose your path" section header before clicking
✅ Expected: Chevron ▸ visible on right side, hint text below title, preview tags showing content
2. Click the section header
✅ Expected: Section expands, chevron rotates to ▾
3. Click again
✅ Expected: Section collapses, chevron rotates back to ▸
❌ If no chevron visible: CSS not loaded correctly

---

### Test 5 — Guardian buttons visible without scrolling
1. Open https://nexus-triage.duckdns.org/incident?nexus_incident_id=INC001
2. Without scrolling at all, can you see the Approve/Reject/Escalate buttons?
✅ Expected: Yes, buttons visible in the first screen
❌ If not visible: Guardian card positioning issue

---

### Test 6 — Guardian approval persists
1. On INC001 incident page, click "Approve"
✅ Expected: Button processes, shows confirmation
2. Reload the page (Cmd+R / F5)
✅ Expected: Approval state still showing, not reset
❌ If resets: Database persistence issue

---

### Test 7 — Fresh incident submission and navigation
1. Go to https://nexus-triage.duckdns.org/inputs
2. Type this in the text area:
```
Checkout service timeout rate spiked to 45%. Users cannot complete purchases. 
P99 latency went from 120ms to 8400ms. Started 20 minutes ago at 14:32 UTC.
```
3. Click Submit
✅ Expected: Page navigates immediately to a new incident URL like `/incident?nexus_incident_id=nxs_...`
❌ If stays on /inputs: Navigation fix not working

---

### Test 8 — Unsupported incident handling
1. Go to https://nexus-triage.duckdns.org/inputs
2. Type: "The office coffee machine is broken and nobody can get coffee"
3. Click Submit
✅ Expected: Inline error message appears listing the 5 supported families. No 500 error page.
❌ If 500 error: Classification miss handling broken

---

### Test 9 — Real scorecard metrics
```bash
curl -s https://nexus-triage.duckdns.org/api/v1/tenant/pilot-scorecard \
  -H "X-Tenant-ID: tenant-a" \
  -H "X-User-ID: test-user" \
  -H "X-Roles: operator" | python3 -m json.tool
```
✅ Expected: Response contains `computed_at` field with a recent timestamp
✅ Expected: `incidents_handled` matches actual number of incidents you've submitted
❌ If `incidents_handled` always shows 5: Scorecard still hardcoded (not fixed)

---

### Test 10 — CORS security
```bash
curl -s -I -H "Origin: https://evil.com" https://nexus-triage.duckdns.org/health
```
✅ Expected: No `Access-Control-Allow-Origin: https://evil.com` header in response
❌ If evil.com gets CORS headers: CORS not configured

---

### Test 11 — Request size limit
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://nexus-triage.duckdns.org/api/v1/incidents/raw-text \
  -H "Content-Type: application/json" \
  -H "Content-Length: 2000000" \
  -H "X-Tenant-ID: tenant-a" \
  -H "X-User-ID: test-user" \
  -H "X-Roles: operator" \
  -d '{}'
```
✅ Expected: 413
❌ If 422 or 200: Size limit not working

---

### Test 12 — Webhook security
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://nexus-triage.duckdns.org/webhooks/incident \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-a" \
  -d '{"raw_text": "test incident"}'
```
✅ Expected: 401 (missing signature rejected)
❌ If 200: Webhook security not working

---

### Test 13 — Full agent pipeline (demo incidents)
1. Open INC001, INC002, INC003, INC005, INC007 in separate tabs
2. For each: confirm the incident family label matches the incident (INC001=checkout timeout, INC002=DB pool, etc.)
3. For each: expand "Investigation Summary" and read the diagnosis
4. Confirm the diagnosis makes sense for the incident type
✅ Expected: Each incident shows appropriate classification and diagnosis
❌ If wrong classification: Agent catalogue mismatch

---

### Test 14 — Run automated test suite
```bash
cd /Users/kunalkachru/Documents/nexus-v3
source venv/bin/activate
pytest tests/ --ignore=tests/test_production_gate3.py -q 2>&1 | tail -3
```
✅ Expected: `470 passed`
```bash
npm run browser:verify 2>&1 | tail -3
```
✅ Expected: `16 passed`

---

### Test 15 — Release gate (everything in one)
```bash
bash scripts/run-release-gate.sh
```
✅ Expected: NEXUS RELEASE GATE: ✅ PASSED
❌ If fails: Read which section failed and investigate that specific area

---

## PART 6 — KNOWN LIMITATIONS

These are real limitations, not bugs. Be aware of them before any demo or pilot:

**1. REPLICA runtime replay not available on cloud:**
The evidence posture badge will show 🟡 inference-first on the cloud deployment because Docker-in-Docker isn't available. On a self-hosted deployment with Docker, you'd see 🟢 runtime-backed.

**2. 5 incident families only:**
Submitting an incident outside the 5 supported families returns a structured error. No silent failures, but limited coverage.

**3. TRACE and FORGE use templates without OpenAI:**
With NEXUS_USE_OPENAI=0 (default), debugging checklists and recommendations come from curated templates, not live AI reasoning. Set NEXUS_USE_OPENAI=1 with a valid API key for live reasoning.

**4. Single-tenant per instance:**
The current deployment supports one organization. Multi-tenant isolation (separate data, audit trails, billing) is planned for a later release.

**5. 1GB RAM on Oracle free tier:**
The current Oracle Cloud VM has 1GB RAM. Under heavy load or with multiple concurrent users, performance may degrade. Sufficient for pilot with a small team.

**6. DuckDNS domain:**
The current URL uses DuckDNS (a free dynamic DNS service). For a formal enterprise pilot, a proper domain is recommended.

---

## PART 7 — TROUBLESHOOTING

### Application won't start locally
```bash
# Check port is free
lsof -i :7860
# Kill if occupied
kill -9 $(lsof -ti:7860)
# Restart
source venv/bin/activate
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
```

### Tests failing locally
```bash
# Make sure server is NOT running when running pytest
# pytest starts its own test server on a different port
pytest tests/ -v --tb=short 2>&1 | grep FAILED
```

### Production not responding
```bash
# Check if container is running
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239 "sudo docker ps"
# View logs
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239 "sudo docker logs nexus --tail=50"
# Restart if needed
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239 "sudo docker restart nexus"
```

### Deploy new changes to production
```bash
# Just push to master — GitHub Actions handles the rest
git push origin master
# Check deploy status
open https://github.com/kunalkachru/nexus-v2/actions
# Verify after deploy (wait 5 minutes)
bash scripts/test-live.sh https://nexus-triage.duckdns.org
```

### Guardian approval not persisting
This means the database volume is not mounted correctly on the deployment. Check:
```bash
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239 "sudo docker inspect nexus | grep -A 5 Mounts"
```
Should show the `nexus-data` volume mounted at `/app/artifacts`.

### Render sleeping (slow first load)
Render free tier sleeps after 15 minutes of inactivity. Wake it before any demo:
```bash
curl https://nexus-uny5.onrender.com/health
```
Wait for `{"status":"ok"}` — may take 30-60 seconds on first wake.

---

## PART 8 — PRE-DEMO CHECKLIST

Run this 5 minutes before showing NEXUS to anyone:

```bash
# 1. Wake Render if using that URL
curl https://nexus-uny5.onrender.com/health

# 2. Verify Oracle Cloud is up
curl https://nexus-triage.duckdns.org/health

# 3. Run smoke tests
bash scripts/test-live.sh https://nexus-triage.duckdns.org
```

Then open in an incognito browser tab:
**https://nexus-triage.duckdns.org/queue**

**Suggested demo flow (10 minutes):**
1. Queue page — show Command Center, explain the 5 demo incidents and agent crew
2. Click into INC001 — show agent timeline, evidence posture badge, Guardian buttons
3. Expand "Investigation Summary" — walk through SENTINEL → PRISM → FORGE output
4. Click "Approve" on Guardian — show the governance gate in action
5. Go to /inputs — submit a fresh incident live, show it navigate to the new incident
6. Show /training — explain the real metrics from actual usage
7. Show /docs — demonstrate the full API is documented

---

## QUICK REFERENCE CARD

| Task | Command / URL |
|---|---|
| Start local server | `source venv/bin/activate && python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload` |
| Run all unit tests | `pytest tests/ --ignore=tests/test_production_gate3.py -q` |
| Run browser tests | `npm run browser:verify` |
| Run release gate | `bash scripts/run-release-gate.sh` |
| Smoke test production | `bash scripts/test-live.sh https://nexus-triage.duckdns.org` |
| Deploy to production | `git push origin master` |
| SSH to server | `ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239` |
| View server logs | SSH then `sudo docker logs nexus -f` |
| Restart server | SSH then `sudo docker restart nexus` |
| Production URL | https://nexus-triage.duckdns.org |
| Demo URL | https://nexus-uny5.onrender.com |
| API docs | https://nexus-triage.duckdns.org/docs |
| GitHub Actions | https://github.com/kunalkachru/nexus-v2/actions |
