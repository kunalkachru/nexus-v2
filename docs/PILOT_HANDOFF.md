# NEXUS Pilot Handoff

## What NEXUS Does

When production incidents occur, SRE teams spend hours manually gathering evidence from logs, metrics, traces, and configuration—diagnosing root causes while pressure mounts and customers wait. This manual process is slow, error-prone, and repeats for every incident.

NEXUS automates this investigation. It runs a structured investigation pipeline with six agents that gather evidence, classify the incident type, diagnose the root cause, attempt to reproduce it in a Docker sandbox, generate a step-by-step debugging checklist, and propose a fix. The GUARDIAN gate then surfaces all findings to a human operator who reviews, approves, or rejects the recommended action before it runs. This isn't autonomous remediation—it's human-led investigation with AI-powered evidence gathering and confidence scoring.

What makes NEXUS different from generic LLM debugging: the evidence posture system. Every finding is tagged with how confident you should be—either "runtime-backed" (we reproduced this in your actual Docker environment with your actual code), or "inference-first" (the AI inferred this from logs). You're not trusting "AI says this"; you're trusting "we reproduced this in your sandbox" or understanding exactly what you're inferring from when you can't reproduce it.

## Your Pilot Access

**Production URL**: https://nexus-triage.duckdns.org

**Authentication**: Include these headers on all API calls:
- `X-Tenant-ID: tenant-a`
- `X-User-ID: your-name`
- `X-Roles: operator`

The `X-Roles` header is required for all API write operations. Valid roles are: `operator`, `incident_manager`, `guardian`, `admin`. Use `operator` for standard incident submission and investigation.

**Demo incidents**: The 5 demo incidents (INC001–INC007) are pre-loaded and always available. Click through each one to see how NEXUS investigates. Try clicking the Guardian approve button on one to see the approval flow.

**Submit a real incident**: Go to `/inputs` and describe your incident symptoms in plain English. NEXUS will attempt to investigate and generate findings.

## What NEXUS Currently Supports

NEXUS handles these five incident families:

1. **Checkout timeout / retry amplification** — Checkout requests start timing out and retries make the problem worse. Describe timeouts, retry counts, and whether client-side retries are making things worse.

2. **Database connection pool exhaustion** — The DB connection pool fills up and new requests are blocked. Describe pool size limits, active connections, and whether pool waits or resets happened.

3. **Deploy regression / 5xx spike** — A recent deployment caused an increase in server errors. Describe the deployment time, error spike time, what changed, and error patterns.

4. **Queue / worker backlog** — A job queue is backing up and transactions are delayed. Describe queue depth, worker capacity, when the backlog started, and what jobs are stuck.

5. **Auth dependency slowdown** — An authentication service becomes slow and token validation fails. Describe auth latency, error rate, and whether requests timeout waiting for auth.

For each incident type, describe the symptoms you observe—timeouts, errors, latency changes, capacity limits—in plain text. NEXUS will match it against these families and investigate.

**What happens outside these 5**: You'll receive a structured error message listing the supported families. No crash, no silent failure. If you need a new incident family, tell us.

## What NEXUS Does NOT Do (Be Honest)

- **Does not replace human judgment** — The GUARDIAN gate requires a human to approve every recommended action. NEXUS proposes; you decide.

- **Does not support arbitrary incident types yet** — The 5 families above are the current scope. Other incident types will return "unsupported incident family."

- **Does not have REPLICA runtime replay on the cloud deployment** — The bounded reproduction feature requires Docker, which isn't available on the current hosting. When you submit an incident, Evidence Posture will show "inference-first" rather than "runtime-backed" because we can't spin up your Docker environment on the cloud. (On self-hosted deployments with Docker available, you'd get "runtime-backed" evidence.)

- **Is not multi-tenant in this pilot** — This instance is dedicated to your organization. Real multi-tenancy with separate data, audit trails, and billing comes in a later release.

- **Does not have uptime SLAs on the current free hosting tier** — The current cloud hosting is best-effort. For production pilots requiring reliability and guaranteed response time, a dedicated server is available.

## 30-Day Pilot Structure

**Week 1: Explore the demo incidents**
- Go to `/queue`. Click through incidents INC001 through INC007.
- Read how each agent in the investigation chain contributes evidence.
- Try approving one incident to see the approval flow and outcome.
- Get comfortable with how findings are presented.

**Week 2–3: Submit real incidents from your environment**
- Go to `/inputs`. Submit at least 5 real incidents from your operations.
- For each one, describe what you observed (latencies, errors, timeouts, capacity limits).
- Compare what NEXUS found to what your team found manually.
- Note which pieces of evidence matched your root cause. Note what was missing.

**Week 4: Review outcomes and metrics**
- Visit the Training dashboard. Check your actual metrics.
- Prepare feedback on:
  - Which incident types you wanted to submit that weren't supported
  - What information was missing or confusing in the findings
  - What would make you confident enough to act on a Guardian recommendation

**Success Criteria**: 5+ real incidents processed, GUARDIAN approval flow used 3+ times, Training dashboard shows non-zero real incident metrics.

## How to Give Feedback and Get Support

**Report issues**: Open an issue in the project repository or email support.

**Response time**: 
- Non-urgent questions: within 48 hours
- Incidents affecting the pilot: within 4 hours

**Request a new incident family**: Describe the incident type, typical symptoms you see, and whether you have a Docker-based environment where we could reproduce it. This helps us understand priority and feasibility.

---

**Ready to start?** Go to https://nexus-triage.duckdns.org and explore incident INC001.
