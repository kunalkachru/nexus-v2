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

### 3. Pilot deployment mode

Used for:

- real customer evaluation
- bounded operational testing
- support team enablement

Characteristics:

- same product as local development, deployed to production infrastructure
- authentication required for all API endpoints
- audit logging of all operations
- runtime host relay enabled for bounded replay
- tenant bootstrap configuration defines pilot readiness

## Pilot Setup and Onboarding

To prepare NEXUS for a real pilot, a new tenant environment must complete the following steps.

### Minimum Viable Pilot Setup

A tenant is ready for a bounded pilot when all of these are configured:

1. **Supported Outage Families**: At least one curated incident pack enabled
   - `INC001`: Timeout/Retry Amplification (requires `checkout-python-fastapi-auth-redis-v1` pack)
   - `INC002`: DB Pool Exhaustion (requires `checkout-python-fastapi-postgres-v1` pack)
   - `INC003`: Deploy Regression / 5xx Spike (requires catalog pack)

2. **Owner Mappings**: Teams and engineers responsible for each supported outage family
   - Maps issue families to on-call engineers
   - Enables NEXUS to route investigations to the right owner
   - Example: `{"timeout_retry": "checkout-team", "db_pool": "infra-team"}`

3. **Repository Information**: Code repositories where investigations will point
   - Service-to-repo mappings for TRACE handoff
   - Enables "inspect here first" packet generation
   - Example: `{"checkout-service": "github.com/acme/checkout"}`

4. **Delivery Targets**: Where investigation packets should be sent
   - At least one of: GitHub, Slack, or Email integration configured
   - Enables downstream handoff to engineering
   - Example: `{"github": {"org": "acme", "repo": "incidents"}}`

5. **Approval Policy**: Guardian approval requirements by incident severity
   - Defines who can approve actions by severity level
   - Example: `{"P0": "incident_manager", "P1-P2": "operator", "P3+": "operator"}`

6. **Enabled Packs**: Runtime reproduction packs available for this tenant
   - At least one bounded pack enabled (see "Supported Outage Families" above)
   - Packs are configured in the tenant bootstrap configuration
   - Example: `["checkout-python-fastapi-auth-redis-v1", "checkout-python-fastapi-postgres-v1"]`

### Bootstrap Configuration Workflow

1. Navigate to **Settings** from the training page (or via `/settings`)
2. Review the **Tenant Onboarding & Deployment Readiness** section
3. Under **Required Setup Steps**, see which fields are missing
4. Contact your administrator to configure each missing field
5. Refresh the settings page to confirm all fields are configured
6. The **Supported Outage Families** section will show which incident types are enabled

### Example Bootstrap Configuration

```json
{
  "tenant_id": "acme-pilot",
  "owners": {
    "timeout_retry_amplification": "checkout-team@acme.com",
    "db_pool_exhaustion": "infra-team@acme.com"
  },
  "repos": {
    "checkout-service": "https://github.com/acme/checkout",
    "payment-service": "https://github.com/acme/payment"
  },
  "delivery_targets": {
    "github": {
      "org": "acme",
      "repo": "incidents",
      "token_env": "GITHUB_INCIDENTS_TOKEN"
    },
    "slack": {
      "webhook_env": "SLACK_INCIDENTS_WEBHOOK"
    }
  },
  "approval_policy": {
    "P0": "incident_manager",
    "P1": "incident_manager",
    "P2": "operator",
    "P3": "operator"
  },
  "enabled_packs": [
    "checkout-python-fastapi-auth-redis-v1",
    "checkout-python-fastapi-postgres-v1"
  ]
}
```

## Product Observability and Health Monitoring

NEXUS provides operators and maintainers with visibility into the product's own health and operational status.

### Health Endpoints

#### GET /health
Basic health check returning `{"status": "ok"}`. Use this for infrastructure health probes.

#### GET /api/v1/observability/health
Comprehensive product health summary including:

- **App**: Response times and overall application status
- **Replay**: Current execution state and recent replay activity history
- **Queue**: Incident queue depth and degradation thresholds
- **Downstream Integrations**: Health status of GitHub, Slack, and other targets

Returns a status object with detailed metrics:

```json
{
  "status": "ok",
  "timestamp": "2026-06-15T12:34:56Z",
  "app": {
    "status": "healthy",
    "response_time_ms": 0
  },
  "replay": {
    "status": "idle",
    "current_execution": {...},
    "recent_executions": [...]
  },
  "queue": {
    "status": "healthy",
    "items_pending": 5,
    "threshold_warning": 100,
    "threshold_critical": 500
  },
  "downstream_integrations": {
    "status": "healthy",
    "github": {"available": true},
    "slack": {"available": true}
  }
}
```

### Viewing Product Health in the UI

Navigate to the **Learning & Controls** page to see the **Product Health & Observability** section, which displays:

- Application status and response time
- Current replay execution state and recent activity count
- Incident queue health and pending item count
- Downstream integration availability

### Interpreting Health Status

| Status | Meaning | Action |
|--------|---------|--------|
| **healthy** | System is operating normally | None required |
| **degraded** | System is experiencing elevated load or latency | Monitor closely; may need to reduce load or investigate |
| **unhealthy** | System is experiencing critical issues | Immediate investigation required |
| **idle** | No operations in progress | Normal between replay executions |
| **running** | Operations in progress | Wait for completion or investigate if stuck |

### Queue Thresholds

- **Warning**: 100+ items pending (yellow)
- **Critical**: 500+ items pending (red)

If queue exceeds warning threshold, consider reducing new incident intake or investigating processing delays.

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

## Post-Handoff Workflow and Feedback Closure

### Handoff Lifecycle

Once a case is handed off to engineering, NEXUS tracks the workflow through these stages:

1. **Delivered**: Handoff sent to GitHub, Slack, or other target
2. **Acknowledged**: Engineering team received and acknowledged the case
3. **Acted On**: Engineering took action based on the handoff
4. **Rejected**: Engineering decided not to act on the suggested mitigation
5. **Follow-up Needed**: Case requires additional investigation before action

### Recording Engineering Feedback

Operators and managers can record engineering feedback to close the loop:

**Option 1: Manual Feedback Entry**
- Navigate to the incident detail page
- Scroll to the **Engineering Feedback** section
- Click **Add Feedback**
- Select the feedback state: acknowledged, acted_on, rejected, follow_up_needed
- Add an optional comment explaining the decision
- Click **Submit**

**Option 2: Webhook Integration**
- Engineering team can post feedback via webhook: `POST /api/v1/incidents/{incident_id}/engineering-feedback`
- Payload:
  ```json
  {
    "status": "acted_on",
    "reason": "Mitigation deployed to production at 2026-06-15 14:32:00"
  }
  ```
- This automatically updates the delivery history with the feedback state

### Viewing Delivery Closure

The **Delivery History** section on the incident detail page shows:

- **Sent**: When and where the handoff was delivered
- **Attempt count**: How many times delivery was attempted
- **Status**: Current delivery state (delivered, retrying, terminal_failure, etc.)
- **Feedback recorded**: Whether engineering provided feedback
- **Feedback state**: What feedback was provided (acknowledged, acted_on, rejected, follow_up_needed)
- **Feedback recorded at**: When engineering provided the feedback

### Feedback Impact on Learning

Delivery feedback feeds back into the learning system:

- **Acted On cases**: Outcomes increase memory ranking for similar future cases
- **Rejected cases**: Reasoning for rejection is captured for process improvement
- **Follow-up cases**: Flagged for manual review and potential escalation
- **Acknowledged cases**: Confirm successful delivery and baseline understanding

### Operator Guidance for Feedback Closure

**If engineering acknowledged the case:**
- Monitor for feedback updates on whether action was taken
- Proceed to follow-up step if no action taken within expected timeframe

**If engineering acted on the case:**
- Capture the action taken and outcome (rollback successful, fix deployed, etc.)
- Update case status to "resolved" if fully resolved, otherwise keep as "investigating"
- This feedback improves similar case handling in the future

**If engineering rejected the case:**
- Understand why (false positive detection, already fixed, not a priority, etc.)
- Use feedback to improve future triage for this incident family
- Consider whether the NEXUS hypothesis was incorrect or the engineering assessment was

**If follow-up is needed:**
- Schedule additional investigation (more logs needed, reproduction conditions unclear, etc.)
- Engineering may provide specific questions or requirements for next iteration
- Re-run triage once additional information is available

## Security and Secrets Handling

NEXUS handles authentication credentials, API keys, and integration secrets. This section documents the security posture for market-ready v1.

### Security Baseline

**What is protected:**

- OpenAI API keys: Request-scoped, never persisted to disk, passed via `x-openai-api-key` header only
- Webhook signatures: Verified via HMAC-SHA256, checked on every incoming webhook
- Runtime host authentication: Token-based, checked on runtime-to-app communication
- User identities: Validated via headers, required for all authenticated endpoints

**What is NOT encrypted or specially protected:**

- Bootstrap configuration (owners, repos, delivery targets) is stored in plaintext JSON
- User roles and tenant IDs are passed in request headers
- Audit logs are stored in plaintext JSON files
- Incident payloads and normalized evidence are stored in plaintext JSON

**What we do NOT support (out of scope for v1):**

- At-rest encryption for incident data or configuration
- Key rotation for webhook secrets or runtime host tokens
- TLS mutual authentication
- Hardware security module (HSM) integration
- Encryption key management beyond environment variables

### Secret Entry Points

1. **OpenAI API Key**
   - Entry: Request header `x-openai-api-key`
   - Scope: Request-scoped only, never persisted
   - Handling: Validated format, never logged

2. **Webhook Signature Secret**
   - Entry: Environment variable `NEXUS_WEBHOOK_SIGNING_SECRET`
   - Scope: Server-wide, used to verify incoming webhooks
   - Handling: Used in HMAC-SHA256 computation, never exposed in responses

3. **Runtime Host Token**
   - Entry: Environment variable `NEXUS_RUNTIME_HOST_SHARED_TOKEN`
   - Scope: Runtime-to-app communication only
   - Handling: Compared via constant-time comparison, never exposed

4. **Bootstrap Configuration Secrets**
   - Entry: PUT `/api/v1/tenant/bootstrap-config` endpoint
   - Scope: Stored in plaintext, accessible to admin role only
   - Handling: Not masked in responses (consider your security model before storing secrets here)

### Recommendations

For production use of NEXUS:

1. **Do** use separate credentials for each environment (dev, staging, prod)
2. **Do** rotate webhook and runtime host secrets regularly (manual process)
3. **Do** run NEXUS with minimal IAM permissions in your infrastructure
4. **Do** restrict access to the incident database and configuration files
5. **Do NOT** store production API keys or OAuth tokens in bootstrap config
6. **Do NOT** expose NEXUS directly to the internet without authentication
7. **Do NOT** log or debug with customer incident data
8. **Consider** running NEXUS in a private network or behind a VPN

### Honest Security Statement for Customers

> NEXUS is a support-triage automation tool with a market-ready v1 security posture. It does not encrypt incident data at rest, and secrets should not be stored in bootstrap configuration. For production use, ensure NEXUS runs in a secured network environment with restricted access to its configuration and database files. The product is suitable for internal teams within secure infrastructure; external deployment requires additional hardening not included in v1.

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
