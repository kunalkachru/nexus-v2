# NEXUS Operator Runbook

Quick reference for support operators triaging and managing incidents through NEXUS.

## The 6-Step Flow

1. Triage: Command Center → select incident
2. Review: read the investigation summary and suggested action
3. Decide: approve, reject, or request modification
4. Execute: if approved, action runs and results are captured
5. Handoff: send investigation packet to engineering
6. Follow-up: track delivery and engineering feedback

## Key Concepts

- `runtime-backed`: replay really ran for this incident family
- `inference-first`: NEXUS can frame and guide the case, but replay did not validate it
- `unsupported`: NEXUS can still triage, but the incident is outside the current bounded wedge

## Current Supported Bounded Families

- `INC001` timeout / retry amplification
- `INC002` DB pool exhaustion / session leak
- `INC003` deploy regression / 5xx spike
- `INC005` queue / worker backlog
- `INC007` auth dependency slowdown / token validation failures

## If Replay Is Not Available

1. confirm whether the issue family is supported
2. check runtime-host status in Settings or Training
3. proceed with inference-first handoff if replay is unavailable
4. do not describe the incident as validated unless replay actually ran

## Governance & Role Model

NEXUS uses a role-based access control (RBAC) model with four primary roles:

**Operator** — Support operators who triage incidents and trigger replays
- Can: Read incidents, create incidents, trigger replay, send handoff
- Cannot: Approve runbooks, update configuration
- Typical use: Daily triage, bounded replay execution

**Incident Manager** — Incident managers who review and coordinate responses
- Can: All operator capabilities + review incidents
- Cannot: Approve runbooks, update configuration
- Typical use: Incident coordination, progress review

**Guardian** — Reviewers who approve or block runbooks before execution
- Can: Read incidents, review incidents, approve/reject runbooks
- Cannot: Create incidents, trigger replay, send handoff
- Typical use: Safety gate before execution, compliance review

**Administrator** — System administrators with full access
- Can: All actions including bootstrap configuration
- Cannot: Nothing (full system access)
- Typical use: Deployment, configuration, user management

### Critical Actions & Approval Flows

The following actions are considered governance-sensitive and are logged with actor context:

| Action | Allowed Roles | Purpose |
|--------|---------------|---------|
| Approve runbook | admin, guardian | Final gate before execution |
| Trigger replay | operator, incident_manager, admin | Bounded replay for validation |
| Send handoff | operator, incident_manager, admin | Downstream notification |
| Update bootstrap | admin only | Tenant configuration changes |

**Important:** Each action is logged with:
- Who performed it (user ID)
- What role they used
- What tenant they belong to
- Timestamp and decision details

This audit trail is essential for compliance and incident review.

### Approval Workflow

When a runbook is proposed:

1. **Operator** — Operator triages incident and runs bounded replay
2. **Guardian Review** — Guardian reviews the runbook and audit trail
3. **Approval Decision** — Guardian approves or requests modifications
4. **Execution** — Approved runbook proceeds (if operator chooses)
5. **Handoff** — Operator sends result to engineering team

The approval decision is **always audited** with the guardian's identity and role.

### Checking Available Capabilities

View the current role matrix and critical actions in the Settings UI:
- Navigate to Settings > Governance & Roles
- See which roles can perform each critical action
- Confirm your own role assignments
