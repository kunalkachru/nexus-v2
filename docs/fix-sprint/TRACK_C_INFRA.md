You are running a focused infrastructure and documentation sprint for NEXUS. Work continuously through all items below without stopping for approval between items. Apply governance rules throughout: compact at 50% context, 2-failure retry limit then mark blocked, never call ScheduleWakeup, ask only if genuinely uncertain.

IMPORTANT: Item C1 requires a domain to already be purchased and its A record pointed to 92.5.47.239. If the domain is not yet set up, skip C1 and come back to it. Start with C2, C3, C4 while the domain propagates.

---

ITEM C1 — Set up nginx + HTTPS on Oracle Cloud (SKIP IF DOMAIN NOT READY)

Prerequisites (done manually by the user before this item):
- Domain purchased (e.g. nexustriage.io)
- A record pointed to 92.5.47.239
- Port 443 opened in Oracle Cloud security list (same steps as port 7860)

Implementation — SSH into the server and run these commands:

1. SSH into Oracle Cloud:
   ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239

2. Install nginx and certbot:
   sudo apt-get update -y
   sudo apt-get install -y nginx certbot python3-certbot-nginx

3. Create nginx config:
   sudo tee /etc/nginx/sites-available/nexus << 'EOF'
   server {
       listen 80;
       server_name YOUR_DOMAIN_HERE;
       
       location / {
           proxy_pass http://localhost:7860;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 60s;
           proxy_connect_timeout 10s;
       }
   }
   EOF

4. Enable the site:
   sudo ln -sf /etc/nginx/sites-available/nexus /etc/nginx/sites-enabled/nexus
   sudo rm -f /etc/nginx/sites-enabled/default
   sudo nginx -t
   sudo systemctl reload nginx

5. Get SSL certificate (replace YOUR_DOMAIN_HERE with actual domain):
   sudo certbot --nginx -d YOUR_DOMAIN_HERE --non-interactive --agree-tos --email kunalkachru23@gmail.com

6. Verify:
   curl https://YOUR_DOMAIN_HERE/health

7. Set up auto-renewal:
   sudo systemctl enable certbot.timer
   sudo systemctl start certbot.timer

After SSH steps complete, update all documentation with the new domain:
- Replace all occurrences of "nexus-triage.duckdns.org:7860" with "YOUR_DOMAIN_HERE" (no port) in:
  - scripts/test-live.sh
  - scripts/deploy-oracle.sh
  - .github/workflows/deploy.yml
  - docs/MASTER_GUIDE.md
  - docs/CICD.md
- Commit: git add -A && git commit -m "infra: add nginx + HTTPS, update all URLs to new domain"

Done when:
- curl https://YOUR_DOMAIN_HERE/health returns {"status": "ok"}
- No :7860 in the URL
- SSL certificate valid (no browser warnings)
- All documentation updated

---

ITEM C2 — Update AGENTS.md and WORKING_STATE.md baselines (DOCUMENTATION)

AGENTS.md still shows old baseline (410 tests, 16 browser). Every new Claude Code session starts by reading AGENTS.md — wrong baseline means wrong ground truth.

Implementation:
1. Read AGENTS.md in full
2. Find the "Current validated baseline" section
3. Update these values:
   - pytest tests/ -q → 450 passed (add note: excludes test_production_gate3.py which requires live server)
   - npm run browser:verify → 21 passed
   - Update the date to 2026-06-19
4. Add a new "Governance rules for autonomous sessions" section to AGENTS.md:
   ## Governance Rules for Autonomous Sessions
   
   These rules apply to all Claude Code autonomous loop sessions:
   
   - Launch with: `claude --max-turns 30` (hard turn cap)
   - Set before launching: `export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`
   - 2-failure retry limit per item — mark blocked and move on, never retry a third time
   - Checkpoint and report every 3 completed items
   - Never call ScheduleWakeup under any circumstances
   - Use `--dangerously-skip-permissions` only for bounded repo work (not system commands)
   - `/compact` and `/context` must be typed directly by the user — cannot be invoked via bash tool calls
   - Compact at 50% context without waiting to be told

5. Add a "Production deployments" section to AGENTS.md:
   ## Production Deployments
   
   | Environment | URL | Auto-deploys on |
   |---|---|---|
   | Oracle Cloud | http://nexus-triage.duckdns.org:7860 | git push origin master via GitHub Actions |
   | Render | https://nexus-uny5.onrender.com | git push origin master |
   
   SSH access: ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
   Smoke test: bash scripts/test-live.sh http://nexus-triage.duckdns.org:7860
   Release gate: bash scripts/run-release-gate.sh

6. Read WORKING_STATE.md and update the baseline numbers to match current state

Done when: AGENTS.md baseline matches actual pytest and browser test counts, governance rules documented, production URLs documented.

Test gate: Run pytest tests/ -q and npm run browser:verify — output must match what AGENTS.md now claims.

---

ITEM C3 — Write pilot handoff document (GTM CRITICAL)

No document exists to hand to a pilot customer. Create it.

Create docs/PILOT_HANDOFF.md with exactly this structure and content (write it properly, not as a placeholder):

SECTION 1 — What NEXUS does (plain English, no jargon)
Write 2 paragraphs explaining:
- The problem: when a production incident happens, an SRE team spends hours gathering evidence, diagnosing the root cause, and deciding what to do — all manually, under pressure
- What NEXUS does: it runs a structured investigation pipeline (6 agents) that gathers evidence, classifies the incident, diagnoses the root cause, attempts to reproduce it in a sandbox, generates a debugging checklist, proposes a fix, and surfaces all of this to a human GUARDIAN who approves or rejects the recommended action
- What makes it different: the evidence posture system (runtime-backed vs inference-first) tells operators exactly how confident to be in each finding — not "AI says this" but "we reproduced this in your environment"

SECTION 2 — Your pilot access
- Production URL: http://nexus-triage.duckdns.org:7860
- How to authenticate: include X-Tenant-ID: tenant-a and X-User-ID: your-name headers on API calls
- The 5 demo incidents (INC001-INC007) are pre-loaded and always available
- To submit a real incident: go to /inputs and describe the symptoms in plain text

SECTION 3 — What NEXUS currently supports
List the 5 incident families with plain descriptions:
1. Checkout timeout / retry amplification — When checkout requests start timing out and retries make the problem worse
2. Database connection pool exhaustion — When the DB connection pool fills up and new requests are blocked
3. Deploy regression / 5xx spike — When a recent deployment caused an increase in server errors
4. Queue / worker backlog — When a job queue is backing up and transactions are delayed
5. Auth dependency slowdown — When an authentication service becomes slow and token validation fails

For each family: one sentence on what symptoms to describe when submitting.
What happens outside these 5: structured error message listing the supported families — no crash, no silent failure.

SECTION 4 — What NEXUS does NOT do (be honest, this builds trust)
- Does not replace human judgment — the GUARDIAN gate requires a human to approve every recommended action
- Does not support arbitrary incident types yet — the 5 families above are the current scope
- Does not have REPLICA runtime replay on the cloud deployment — the bounded reproduction feature requires Docker which isn't available on the current hosting. Evidence posture will show "inference-first" rather than "runtime-backed" on the cloud deployment.
- Is not multi-tenant in this pilot — this instance is dedicated to your organization
- Does not have uptime SLAs on the current free hosting tier — for production pilots requiring reliability, a dedicated server is available

SECTION 5 — 30-day pilot structure
Week 1: Explore the 5 demo incidents. Click through each one. Follow the agent investigation chain. Try clicking Guardian approve on one incident.
Week 2-3: Submit at least 5 real incidents from your environment using /inputs. Compare what NEXUS finds to what your team found manually.
Week 4: Review the Training dashboard. Check your actual metrics. Prepare feedback on: which incident types you wanted to submit that weren't supported, what information was missing or confusing, what would make you trust the GUARDIAN recommendation enough to act on it.

Success criteria: 5+ real incidents processed, GUARDIAN approval flow used 3+ times, Training dashboard shows non-zero real metrics.

SECTION 6 — How to give feedback and get support
- Report issues: [GitHub Issues link or email]
- Response time: within 48 hours for non-urgent questions, within 4 hours for incidents affecting the pilot
- To request a new incident family: describe the incident type, the typical symptoms, and whether you have a Docker-based environment to reproduce it

Done when: docs/PILOT_HANDOFF.md exists, covers all 6 sections, is written in plain English a non-technical stakeholder can read, is honest about limitations, is professional enough to send to a real customer.

---

ITEM C4 — Wire release gate into CI/CD pipeline (RELIABILITY)

The release gate exists but runs manually. Every push to master should run tests before deploying.

Implementation:
1. Read .github/workflows/deploy.yml in full
2. Add a test job before the deploy job:

   test:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v3
       
       - name: Set up Python
         uses: actions/setup-python@v4
         with:
           python-version: '3.11'
       
       - name: Install dependencies
         run: pip install -r requirements.txt
       
       - name: Run unit tests
         run: pytest tests/ --ignore=tests/test_production_gate3.py -q
         
       - name: Report test count
         run: pytest tests/ --ignore=tests/test_production_gate3.py -q 2>&1 | tail -3

3. Add needs: test to the existing deploy job so it only runs after tests pass:
   deploy:
     needs: test
     runs-on: ubuntu-latest
     ...

4. Add a smoke test step at the END of the deploy job, after the deployment is complete:
   - name: Wait for deployment to stabilize
     run: sleep 30
   
   - name: Smoke test production
     run: bash scripts/test-live.sh http://nexus-triage.duckdns.org:7860

5. Commit and push a test commit to verify the pipeline runs correctly:
   git commit --allow-empty -m "ci: verify release gate pipeline"
   git push origin master
   
   Then check https://github.com/kunalkachru/nexus-v2/actions and confirm three stages completed: test ✅ → deploy ✅ → smoke ✅

Done when:
- GitHub Actions shows test → deploy → smoke as three distinct stages
- A failing test would prevent deployment (verify by checking the needs: test dependency)
- Smoke tests run automatically after every successful deploy

---

AFTER ALL ITEMS:

1. Run final verification:
   bash scripts/test-live.sh http://nexus-triage.duckdns.org:7860
   Report all 5 results

2. Commit all remaining changes:
   git add -A && git commit -m "infra: AGENTS.md baselines, pilot handoff doc, CI/CD release gate" && git push origin master

3. Report final status table:
   | Item | Status | Notes |
   |------|--------|-------|
   | C1: HTTPS domain | PASS/FAIL/SKIPPED | Domain: |
   | C2: AGENTS.md update | PASS/FAIL | |
   | C3: Pilot handoff doc | PASS/FAIL | |
   | C4: CI/CD release gate | PASS/FAIL | |
