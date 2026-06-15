# Operations

Current as of 2026-06-05.

This document is the runtime guide for the shipped NEXUS v2 product and the current support-triage demo flow.

It focuses on what is runnable now while staying aligned with the broader product direction.

## Runtime Posture

Today’s shipped product is:

- deterministic by default
- safe for public demo
- able to use request-scoped BYO-key live reasoning when a user explicitly opts in
- built around the visible four-agent flow:
  - `SENTINEL`
  - `PRISM`
  - `FORGE`
  - `GUARDIAN`

The broader product direction adds:

- `REPLICA` for reproduction
- `TRACE` for debugging

Those are not required for current runtime operation.

## Deployment Modes

### 1. Public demo mode

Used for:

- Hugging Face Spaces
- public product review
- live walkthroughs

Characteristics:

- deterministic by default
- no server OpenAI key required
- safe for public access
- optional user-supplied OpenAI key from the UI

### 2. Local development mode

Used for:

- feature work
- browser validation
- regression checks
- end-to-end flagship use case review

Characteristics:

- Docker-first workflow
- same frontend and backend served together
- easy rebuild path

## Role-Based Access Control

NEXUS implements a bounded role model to govern who can perform critical operations.

### Role Matrix

| Role | Description | Can Read Incidents | Can Create Incidents | Can Trigger Replay | Can Send Handoff | Can View Settings | Can Update Bootstrap | Can Approve Actions | Can Review Actions |
|------|-------------|-------------------|----------------------|-------------------|------------------|-------------------|----------------------|---------------------|--------------------|
| operator | Support operator | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| incident_manager | Incident manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| guardian | Guardian reviewer | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| admin | Administrator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Passing Roles in Requests

Roles are passed via the `x-roles` header as a comma-separated list:

```bash
curl -H "x-user-id: user123" \
  -H "x-tenant-id: tenant-a" \
  -H "x-roles: operator,incident_manager" \
  http://localhost:7860/api/v1/incidents/queue
```

### UI Role-Based Visibility

The product automatically hides or disables controls based on the user's assigned roles:

- **Replay button**: Hidden/disabled for users without `trigger_replay` capability
- **Handoff send button**: Hidden/disabled for users without `send_handoff` capability
- **Guardian approval buttons**: Hidden for users without `approve_action` capability
- **Bootstrap config endpoints**: Restricted to `admin` role only

## Delivery Lifecycle and Reliability

### Delivery States

Each handoff send attempt goes through the following lifecycle states:

| State | Meaning | Retryable |
|-------|---------|-----------|
| **queued** | Delivery is waiting to be sent | ✓ |
| **sent** | Successfully sent to the target | ✗ |
| **retrying** | Previous attempt failed but is retryable (e.g., timeout, connection error) | ✓ |
| **failed** | Temporary failure (deprecated; see terminal_failure or retrying) | ✓ |
| **terminal_failure** | Permanent failure (e.g., invalid credentials, target not found) | ✗ |

### Retry Behavior

- **Automatic retry**: The system automatically classifies failures as retryable (timeout/connection errors) vs. terminal (auth/validation errors)
- **Manual retry**: Operators can manually retry failed deliveries from the incident detail page
- **Retry limits**: Automatic retries are limited to 2 attempts before marking as terminal_failure
- **Auditing**: All retry attempts are tracked in the delivery history with timestamps and error details

### Viewing Delivery Status

Navigate to the incident detail page and scroll to the **Delivery History** section to see:

- Target (GitHub, Slack, etc.)
- Current delivery state (sent, retrying, terminal_failure, etc.)
- Attempt count for failed/retrying deliveries
- Failure reason (if applicable)
- Timestamp of the attempt
- Manual retry button (if applicable)

### Operator Recovery Steps

If a delivery fails:

1. Check the failure reason in the delivery history
2. Verify the target configuration (credentials, permissions, etc.)
3. If it looks like a temporary issue, click the **Retry** button
4. If it's a terminal failure, update the target configuration and try a new send

## Tenant Onboarding and Bootstrap

### Required Bootstrap Fields

Before a tenant can use NEXUS, the following must be configured:

1. **Owners**: Service owners and escalation contacts (team names, Slack channels, or email lists)
2. **Repos**: Repository mapping (service name to repository URL or path)
3. **Delivery Targets**: Downstream workflow destinations (GitHub, Slack, Jira, etc.)
4. **Approval Policy**: Guardian approval requirements by incident severity (P0/P1/P2 rules)
5. **Enabled Packs**: Which runtime packs are enabled for this tenant environment

### Viewing Bootstrap Status

The **Settings** page shows the current bootstrap status for a tenant:

- Navigate to `/settings`
- Look for the **Tenant Onboarding & Deployment Readiness** section
- See which fields are configured and which are still pending

### Configuring Bootstrap Fields

Bootstrap configuration can be updated via:

```bash
# Get current bootstrap config
curl -H "Authorization: Bearer <token>" \
  http://localhost:7860/api/v1/tenant/bootstrap-config

# Update bootstrap config
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "owners": {"team_checkout": "checkout-team@example.com"},
    "repos": {"checkout": "github.com/example/checkout"},
    "delivery_targets": {"github": true, "slack": true},
    "approval_policy": {"p0": "incident_manager", "p1": "operator"},
    "enabled_packs": ["checkout-python-fastapi-auth-redis-v1", "checkout-python-fastapi-postgres-v1"]
  }' \
  http://localhost:7860/api/v1/tenant/bootstrap-config
```

### Onboarding Checklist

- [ ] Define service owners and escalation contacts
- [ ] Map services to their repositories
- [ ] Configure downstream delivery targets
- [ ] Set approval policies for incident severity levels
- [ ] Enable appropriate runtime packs for your stack
- [ ] Verify bootstrap status shows "Ready" on the Settings page

## Recommended Start Commands

### Fresh local rebuild

```bash
./scripts/docker_fresh.sh
```

### Direct server run

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Public Spaces

### Production

- Space page: [https://huggingface.co/spaces/kunalkachru23/nexus](https://huggingface.co/spaces/kunalkachru23/nexus)
- Public app: [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)

### Staging

- Space page: [https://huggingface.co/spaces/kunalkachru23/nexus-staging](https://huggingface.co/spaces/kunalkachru23/nexus-staging)
- Public app: [https://kunalkachru23-nexus-staging.hf.space](https://kunalkachru23-nexus-staging.hf.space)

## Key Runtime Rules

- default public posture is deterministic
- `OPENAI_API_KEY` is not required for the public app
- a user can optionally attach their own key in `Incident Detail`
- user keys are request-scoped and masked in the UI
- history and archive review should stay deterministic by default

## Health Check

Use:

- `/health`

Expected:

```json
{"status":"ok"}
```

## Primary Manual Checks

Use the flagship support-triage story while validating:

1. `/inputs` can create a fresh `nxs_...` incident from raw logs
2. the created incident reads like a prepared support case
3. `GUARDIAN` approval visibly changes the execution state
4. `/training` maps the latest live triage into the broader runtime summary
5. `/history` opens archived incidents quickly in deterministic review mode

## Local Verification Commands

### Python tests

```bash
pytest tests/ -v
```

### Browser tests

```bash
npm run browser:verify
```

### Judge demo script

```bash
python demo.py
```

## If The UI Looks Stale Locally

1. run `./scripts/docker_fresh.sh`
2. wait for `Fresh container is ready.`
3. reload the browser tab

## If The Public HF Space Feels Slow

The product should behave like a review and triage surface, not a hidden re-analysis path.

If a warm page is repeatedly taking several seconds:

1. reload once
2. retry the route
3. compare with local Docker
4. check whether the route is hitting a Space-side cold/warm latency issue
5. confirm the flow is not accidentally re-triggering expensive live reasoning on review screens

## Source Of Truth Docs

- [README.md](/Users/kunalkachru/Documents/nexus-v3/README.md)
- [PRODUCT_STRATEGY_AND_GTM.md](/Users/kunalkachru/Documents/nexus-v3/docs/PRODUCT_STRATEGY_AND_GTM.md)
- [SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/SUPPORT_TRIAGE_PRODUCT_EXECUTION_PLAN.md)
- [FINAL_SUBMISSION_GUIDE.md](/Users/kunalkachru/Documents/nexus-v3/docs/FINAL_SUBMISSION_GUIDE.md)
