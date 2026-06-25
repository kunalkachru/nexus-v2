# NEXUS

NEXUS is an AI-assisted support-to-engineering investigation product that compresses recurring incident workflows into one structured handoff.

**Pipeline:** SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN

**Production:** **[https://nexus-triage.duckdns.org](https://nexus-triage.duckdns.org)** 🚀

---

## Where to Start

| I want to... | Go here |
|---|---|
| Understand the system architecture | [docs/architecture/01-system-overview.md](docs/architecture/01-system-overview.md) |
| See how the 6 agents work together | [docs/architecture/02-agent-pipeline.md](docs/architecture/02-agent-pipeline.md) |
| Trace incident data flow end to end | [docs/architecture/03-data-flow.md](docs/architecture/03-data-flow.md) |
| Run it myself locally | [docs/NEXUS_COMPLETE_MANUAL.md](docs/NEXUS_COMPLETE_MANUAL.md) |
| Demo it to someone | [docs/NEXUS_COMPLETE_MANUAL.md](docs/NEXUS_COMPLETE_MANUAL.md) — Part 8 |
| Hand off to a pilot customer | [docs/PILOT_HANDOFF.md](docs/PILOT_HANDOFF.md) + [production link](https://nexus-triage.duckdns.org) |
| Set up local development | [docs/MASTER_GUIDE.md](docs/MASTER_GUIDE.md) |
| Deploy to production | [docs/MASTER_GUIDE.md](docs/MASTER_GUIDE.md) — Part 5 |
| Understand CI/CD pipeline | [docs/CICD.md](docs/CICD.md) |
| Read pilot results | [docs/PILOT_SIMULATION_RESULTS.md](docs/PILOT_SIMULATION_RESULTS.md) + [docs/MERIDIAN_PILOT_RESULTS_V2.md](docs/MERIDIAN_PILOT_RESULTS_V2.md) |
| Browse all documentation | [docs/README.md](docs/README.md) |
| Browse all architecture diagrams | [docs/architecture/README.md](docs/architecture/README.md) |
| Check production readiness | [docs/GATE2_DECISION.md](docs/GATE2_DECISION.md) |

---

## Running Locally

### Option A — Docker (Recommended)

**Standard run:**
```bash
./scripts/docker_fresh.sh
```
Open http://127.0.0.1:7860/queue

**With REPLICA runtime replay (enables runtime-backed evidence):**
```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

**Stop all containers:**
```bash
docker compose down
```

### Option B — Python Direct

**First time:**
```bash
git clone https://github.com/kunalkachru/nexus-v2.git
cd nexus-v2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
npm install
npx playwright install chromium
cp .env.example .env
```

**Every session:**
```bash
# Optional: Set OPENAI_API_KEY for live model-backed reasoning
export OPENAI_API_KEY=sk-...

source venv/bin/activate
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860 --reload
```
Open http://localhost:7860/queue

(Without `OPENAI_API_KEY`, NEXUS runs in demo mode with pre-trained responses.)

---

## Deployment

**Automatic deploy:** Every `git push origin master` automatically triggers test → deploy → smoke

**Manual deploy to Oracle Cloud:**
```bash
NEXUS_WEBHOOK_SIGNING_SECRET=your-secret bash scripts/deploy-oracle.sh
```
(Retrieve the secret from GitHub repo Settings → Secrets and variables → Actions → ORACLE_WEBHOOK_SECRET)

**Force redeploy from scratch:**
```bash
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
sudo docker ps
sudo docker rm -f nexus
sudo docker build -t nexus .
sudo docker run -d --name nexus --restart always -p 7860:7860 \
  -e NEXUS_DATABASE_PATH=/app/artifacts/incidents.json \
  -v nexus-data:/app/artifacts nexus
```

**Full guide:** [docs/MASTER_GUIDE.md](docs/MASTER_GUIDE.md) — Part 5

**Operations reference:** [docs/internal/OPERATIONS.md](docs/internal/OPERATIONS.md) — Oracle Cloud manual restart and live reasoning commands

---

## Production Environments

| Environment | URL | Persistence | Notes |
|---|---|---|---|
| **Oracle Cloud** | https://nexus-triage.duckdns.org | Persistent | Always on, primary, HTTPS |
| **Render** | https://nexus-uny5.onrender.com | Ephemeral | Sleeps after 15 minutes inactivity |
| **Local Docker** | http://127.0.0.1:7860 | Persistent | Via docker_fresh.sh |
| **API Docs** | https://nexus-triage.duckdns.org/docs | — | OpenAPI reference |

---

## Validation

All validation commands with current baseline numbers:

```bash
# Unit tests (495 passed, 1 skipped)
pytest tests/ --ignore=tests/test_production_gate3.py -q

# Browser verification (16 passed)
npm run browser:verify

# Release gate (PASSED)
bash scripts/run-release-gate.sh

# Smoke test production (5/5 passing)
bash scripts/test-live.sh https://nexus-triage.duckdns.org
```

**Current validated baseline:**

| Check | Expected |
|---|---|
| pytest tests/ --ignore=tests/test_production_gate3.py -q | **495 passed, 1 skipped** |
| npm run browser:verify | **16 passed** |
| bash scripts/run-release-gate.sh | **PASSED** |
| bash scripts/test-live.sh https://nexus-triage.duckdns.org | **5/5 passing** |

---

## What It Does

Supports **8 incident families** with two evidence postures:

| ID | Family | Severity | Evidence Posture |
|---|---|---|---|
| **INC001** | API Timeout / Retry Amplification | P2 | 🟢 Runtime-backed |
| **INC002** | Database Connection Pool Exhaustion | P1 | 🟢 Runtime-backed |
| **INC003** | Deploy Regression / 5xx Spike | P1 | 🟢 Runtime-backed |
| **INC005** | Queue Backlog Surge | P1 | 🟢 Runtime-backed |
| **INC007** | Auth Dependency Slowdown | P1 | 🟢 Runtime-backed |
| **INC009** | CDN / Cache Invalidation Storm | P2 | 🟡 Inference-first |
| **INC010** | ML Model Degradation | P2 | 🟡 Inference-first |
| **INC011** | Geographic Routing Failure | P2 | 🟡 Inference-first |

**Evidence postures:**
- 🟢 **Runtime-backed** — REPLICA reproduces the incident in Docker; three curated packs available (INC001, INC002, INC003)
- 🟡 **Inference-first** — PRISM diagnoses from logs and metrics without replay capability
- 🔴 **Roadmap** — INC004, INC006, INC008 are catalogued but not yet wired. On roadmap for Phase 4.

---

## Architecture Diagrams

Visual documentation of how NEXUS works internally (all diagrams render natively on GitHub):

| Diagram | What it shows |
|---|---|
| [System Overview](docs/architecture/01-system-overview.md) | High-level view of inputs, pipeline, storage, and outputs |
| [Agent Pipeline](docs/architecture/02-agent-pipeline.md) | How SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN hand off |
| [Data Flow](docs/architecture/03-data-flow.md) | Incident data from raw text submission to Guardian decision |
| [Class Structure](docs/architecture/04-class-structure.md) | Key models and their relationships |
| [Deployment](docs/architecture/05-deployment.md) | Oracle Cloud, nginx, Docker, CI/CD pipeline |
| [Sequence Diagrams](docs/architecture/06-sequence-diagrams.md) | Key user journeys step by step |

📍 **Full index:** [docs/architecture/README.md](docs/architecture/README.md)

---

## Repository Structure

| Path | Purpose |
|---|---|
| `server/app.py` | FastAPI entry point |
| `server/services/incidents.py` | Core incident orchestration |
| `server/services/intake.py` | Log intake and normalization |
| `server/services/classification.py` | Incident family classification |
| `server/services/investigation.py` | Investigation orchestration |
| `server/services/replay.py` | Runtime replay orchestration |
| `server/services/runtime_state.py` | Replay state tracking |
| `server/services/enterprise_runtime.py` | Live graph incident tracking |
| `server/services/replica_runtime.py` | Docker-capable replay host relay |
| `frontend/` | Operator UI (queue, inputs, incident, training, settings) |
| `incidents/` | Incident family definitions and catalogue |
| `tests/` | Unit, API contract, and browser verification tests |
| `replica_packs/` | Curated reproduction packs for INC001, INC002, INC003 |
| `training/` | Evidence posture training data and proof surfaces |
| `scripts/` | Deployment, testing, and operations automation |
| `docs/` | Complete documentation (master guide, deployment, pilot handoff, results) |

---

## Quick Commands

```bash
# Start locally with Docker
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh

# Run demo walkthrough (with OPENAI_API_KEY set for live reasoning)
export OPENAI_API_KEY=sk-...
python demo.py

# Run all tests
pytest tests/ --ignore=tests/test_production_gate3.py -q && npm run browser:verify

# Release gate (pre-deployment verification)
bash scripts/run-release-gate.sh

# Deploy to Oracle Cloud
git push origin master
# OR manually:
NEXUS_WEBHOOK_SIGNING_SECRET=your-secret bash scripts/deploy-oracle.sh

# SSH to production server
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239

# Smoke test production
bash scripts/test-live.sh https://nexus-triage.duckdns.org

# Check health
curl https://nexus-triage.duckdns.org/health
```

---

## Key Concepts

**SENTINEL** — Log collector and normalizer  
**PRISM** — ML-first incident classifier  
**REPLICA** — Bounded runtime reproducer (curated packs only)  
**TRACE** — Bounded debugger and code inspector  
**FORGE** — Mitigation ranker and confidence scorer  
**GUARDIAN** — Human approval gate before action  

**Real today:**
- Fresh incident intake and normalization
- Bounded REPLICA runtime replay for curated packs
- Bounded TRACE debugging and engineering handoff
- Runtime-host relay via Docker
- Operator, pilot, and buyer proof surfaces

**Still bounded:**
- Reproduction only works for curated packs (not arbitrary environments)
- TRACE is bounded to curated debugging (not a universal debugger)
- Execution remains governed and human-approved

---

## Next Steps

- **Setup:** Follow [docs/MASTER_GUIDE.md](docs/MASTER_GUIDE.md)
- **Demo:** Use [docs/NEXUS_COMPLETE_MANUAL.md](docs/NEXUS_COMPLETE_MANUAL.md)
- **Deploy:** See [docs/MASTER_GUIDE.md](docs/MASTER_GUIDE.md) — Part 5
- **Questions:** Check [docs/TROUBLESHOOTING_GUIDE.md](docs/TROUBLESHOOTING_GUIDE.md)
- **All docs:** [docs/README.md](docs/README.md)
