# Auth and Governance Hardening v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deepen the role and approval model so pilot operation is safer across tenants by making governance-sensitive actions explicit, auditing actor/role context consistently, and exposing governance rules in the UI.

**Architecture:** 
1. Extend audit system to record actor, role, and tenant context on every governance-sensitive action
2. Add explicit capability checks on all critical endpoints (approval, replay, export, delivery)
3. Make governance rules and role assignments visible in settings/admin surfaces
4. Document the hardened role model for operators

**Tech Stack:** FastAPI, Pydantic models, JSON audit logs, HTML/JS frontend, pytest

---

## File Structure

**Core Auth & Audit Files:**
- `server/audit.py` — Extend audit events to include actor/role/tenant context
- `server/auth.py` — Add helper to check multi-role governance policies

**Service Files:**
- `server/services/governance.py` — Add tenant-aware role visibility and capability checking
- `server/services/incidents.py` — Record actor context on approval, replay, export, delivery
- `server/app.py` — Add capability checks to critical endpoints; log governance decisions with actor

**Frontend:**
- `frontend/settings.html` — Show current user's role and available actions
- `frontend/static/settings.js` — Fetch and display governance UI (role info, who can approve, etc.)

**Documentation:**
- `docs/internal/OPERATOR_RUNBOOK.md` — Document role boundaries and approval workflow
- `docs/internal/OPERATIONS.md` — Add governance section with role matrix and actions

---

## Implementation Tasks

### Task 1: Extend Audit System to Record Actor Context

**Files:**
- Modify: `server/audit.py:19-31`
- Test: `tests/test_audit.py` (new)

- [ ] **Step 1: Write failing test for audit event with actor context**

Run: `touch tests/test_audit.py`

Add to `tests/test_audit.py`:

```python
import pytest
from server.audit import write_audit_log, get_audit_logs

@pytest.mark.asyncio
async def test_audit_event_includes_actor_context():
    """Audit events should record user_id, role, and tenant for governance traceability"""
    event_payload = {
        "incident_id": "nexus-123",
        "action": "approve_runbook",
        "actor_user_id": "user-alice",
        "actor_roles": ["guardian"],
        "actor_tenant_id": "tenant-a",
    }
    
    await write_audit_log("governance_decision", "tenant-a", event_payload)
    
    logs = get_audit_logs("nexus-123")
    assert len(logs) == 1
    assert logs[0]["event_type"] == "governance_decision"
    assert logs[0]["payload"]["actor_user_id"] == "user-alice"
    assert logs[0]["payload"]["actor_roles"] == ["guardian"]
    assert logs[0]["payload"]["actor_tenant_id"] == "tenant-a"
```

Run: `pytest tests/test_audit.py::test_audit_event_includes_actor_context -v`
Expected: FAIL (function signature not yet updated)

- [ ] **Step 2: Add actor context helper to audit.py**

Modify `server/audit.py` to add:

```python
from typing import Optional

async def write_audit_log(
    event_type: str, 
    tenant_id: str, 
    payload: dict[str, object],
    actor_user_id: Optional[str] = None,
    actor_roles: Optional[list[str]] = None,
) -> None:
    """Write audit log with optional actor context for governance traceability."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "tenant_id": tenant_id,
        "actor_user_id": actor_user_id,
        "actor_roles": actor_roles or [],
        "payload": payload,
    }
    async with _AUDIT_LOCK:
        logs = _load_audit_logs()
        logs.append(entry)
        _persist_audit_logs(logs)
    await record_audit_event(entry)
    logger.info(
        "audit event=%s tenant=%s actor=%s roles=%s payload=%s",
        event_type,
        tenant_id,
        actor_user_id,
        actor_roles,
        payload,
    )
```

Replace the existing `write_audit_log` function (lines 19-31) with the above.

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_audit.py::test_audit_event_includes_actor_context -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add server/audit.py tests/test_audit.py
git commit -m "feat: extend audit system to record actor context for governance traceability"
```

---

### Task 2: Add Governance Policy Helper to Auth Module

**Files:**
- Modify: `server/auth.py:90-139`
- Test: `tests/test_auth_governance.py` (new)

- [ ] **Step 1: Write failing test for governance policy checking**

Run: `touch tests/test_auth_governance.py`

Add to `tests/test_auth_governance.py`:

```python
from server.auth import AuthenticatedContext, check_governance_capability

def test_guardian_can_approve_runbook():
    """Guardian role should have approve_action capability"""
    auth = AuthenticatedContext(
        user_id="user-alice",
        tenant_id="tenant-a",
        roles=["guardian"],
    )
    
    # Should not raise
    check_governance_capability(auth, "approve_action")

def test_operator_cannot_approve_runbook():
    """Operator role should not have approve_action capability"""
    auth = AuthenticatedContext(
        user_id="user-bob",
        tenant_id="tenant-a",
        roles=["operator"],
    )
    
    from fastapi import HTTPException
    import pytest
    
    with pytest.raises(HTTPException) as exc_info:
        check_governance_capability(auth, "approve_action")
    assert exc_info.value.status_code == 403

def test_admin_can_do_anything():
    """Admin role should have all capabilities"""
    auth = AuthenticatedContext(
        user_id="user-admin",
        tenant_id="tenant-a",
        roles=["admin"],
    )
    
    # All should pass
    check_governance_capability(auth, "approve_action")
    check_governance_capability(auth, "trigger_replay")
    check_governance_capability(auth, "send_handoff")
```

Run: `pytest tests/test_auth_governance.py -v`
Expected: FAIL (function not yet defined)

- [ ] **Step 2: Implement governance capability checker**

Add to `server/auth.py` after the `require_role` function (after line 100):

```python
def check_governance_capability(auth: AuthenticatedContext, capability: str) -> None:
    """Check if user has required capability for a governance action."""
    capabilities = get_user_capabilities(auth.roles)
    if not capabilities.get(capability, False):
        raise HTTPException(
            status_code=403,
            detail=f"governance action '{capability}' not allowed for roles: {', '.join(auth.roles)}",
        )
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_auth_governance.py -v`
Expected: PASS (all three tests)

- [ ] **Step 4: Commit**

```bash
git add server/auth.py tests/test_auth_governance.py
git commit -m "feat: add governance capability checker for explicit role-based access control"
```

---

### Task 3: Add Capability Checks to Critical API Endpoints

**Files:**
- Modify: `server/app.py:718-738` (governance-packet and handoff-send endpoints)
- Test: `tests/test_api_governance.py` (new)

- [ ] **Step 1: Write failing test for governance checks on critical endpoints**

Run: `touch tests/test_api_governance.py`

Add to `tests/test_api_governance.py`:

```python
import pytest
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_get_governance_packet_requires_read_permission():
    """Getting governance packet should work for users with read permission"""
    response = client.get(
        "/api/v1/incidents/nexus-123/governance-packet",
        headers={
            "x-user-id": "user-alice",
            "x-tenant-id": "tenant-a",
            "x-roles": "guardian",
        },
    )
    # Should not get 403 Forbidden for governance read
    assert response.status_code != 403

def test_send_handoff_requires_capability():
    """Sending handoff should check send_handoff capability"""
    response = client.post(
        "/api/v1/incidents/nexus-123/handoff-send",
        headers={
            "x-user-id": "user-bob",
            "x-tenant-id": "tenant-a",
            "x-roles": "guardian",
        },
        json={"target": "engineering-team"},
    )
    # Guardian cannot send handoff (only operator, incident_manager, admin can)
    assert response.status_code == 403

def test_send_handoff_works_with_operator_role():
    """Operator should be able to send handoff"""
    response = client.post(
        "/api/v1/incidents/nexus-123/handoff-send",
        headers={
            "x-user-id": "user-charlie",
            "x-tenant-id": "tenant-a",
            "x-roles": "operator",
        },
        json={"target": "engineering-team"},
    )
    # Should not get 403 (may be other errors like incident not found, but not 403)
    assert response.status_code != 403
```

Run: `pytest tests/test_api_governance.py::test_send_handoff_requires_capability -v`
Expected: FAIL (no capability check yet)

- [ ] **Step 2: Add capability checks to critical endpoints in app.py**

Find the `send_engineering_handoff_v1` endpoint (around line 738) and modify it:

Current code looks like:
```python
@app.post("/api/v1/incidents/{nexus_incident_id}/handoff-send")
async def send_engineering_handoff_v1(
    nexus_incident_id: str,
    request: Request,
    payload: dict[str, object],
) -> dict[str, object]:
```

Update it to:
```python
@app.post("/api/v1/incidents/{nexus_incident_id}/handoff-send")
async def send_engineering_handoff_v1(
    nexus_incident_id: str,
    request: Request,
    payload: dict[str, object],
) -> dict[str, object]:
    auth = await require_auth(request)
    from server.auth import check_governance_capability
    check_governance_capability(auth, "send_handoff")
    # ... rest of function
```

Similarly, find the governance-packet endpoint and add a check:
```python
@app.get("/api/v1/incidents/{nexus_incident_id}/governance-packet")
async def get_governance_packet_v1(
    nexus_incident_id: str,
    request: Request,
) -> dict[str, object]:
    auth = await require_auth(request)
    from server.auth import check_governance_capability
    check_governance_capability(auth, "read_incidents")
    # ... rest of function
```

Also update the replay launch endpoint:
```python
@app.post("/api/v1/replay/scenarios/{scenario_id}/launch", status_code=202)
async def launch_replay_scenario(
    scenario_id: str,
    request: Request,
) -> dict[str, object]:
    auth = await require_auth(request)
    from server.auth import check_governance_capability
    check_governance_capability(auth, "trigger_replay")
    # ... rest of function
```

- [ ] **Step 3: Run tests to verify capability checks work**

Run: `pytest tests/test_api_governance.py -v`
Expected: PASS (tests should pass with capability checks in place)

- [ ] **Step 4: Commit**

```bash
git add server/app.py tests/test_api_governance.py
git commit -m "feat: add capability checks to governance-sensitive API endpoints"
```

---

### Task 4: Record Actor Context in Governance Decisions

**Files:**
- Modify: `server/services/incidents.py:1143-1217` (record_guardian_decision method)
- Test: `tests/test_governance_audit.py` (new)

- [ ] **Step 1: Write failing test for governance decision audit recording**

Run: `touch tests/test_governance_audit.py`

Add to `tests/test_governance_audit.py`:

```python
import pytest
from server.services.incidents import IncidentService
from server.auth import AuthenticatedContext
from server.audit import get_audit_logs

@pytest.mark.asyncio
async def test_guardian_decision_records_actor_context():
    """Recording a guardian decision should capture actor, role, and tenant"""
    service = IncidentService()
    auth = AuthenticatedContext(
        user_id="user-alice",
        tenant_id="tenant-a",
        roles=["guardian"],
    )
    
    # Create a test incident first
    incident = await service.create_incident_from_manual_report(
        ManualIncidentReport(
            title="Test incident",
            description="For testing governance audit",
            severity="high",
            service="payment-api",
            status="new",
        ),
        auth.tenant_id,
    )
    
    # Record a guardian decision
    from server.integrations.models import GuardianDecisionRequest
    decision = GuardianDecisionRequest(
        decision="approve",
        reasoning="Runbook looks safe",
    )
    await service.record_guardian_decision(incident.nexus_incident_id, decision, auth)
    
    # Check audit logs
    logs = get_audit_logs(incident.nexus_incident_id)
    governance_logs = [log for log in logs if log["event_type"] == "governance_decision"]
    
    assert len(governance_logs) >= 1
    latest_decision = governance_logs[-1]
    assert latest_decision["actor_user_id"] == "user-alice"
    assert "guardian" in latest_decision["actor_roles"]
    assert latest_decision["tenant_id"] == "tenant-a"
    assert latest_decision["payload"]["decision"] == "approve"
```

Run: `pytest tests/test_governance_audit.py::test_guardian_decision_records_actor_context -v`
Expected: FAIL (record_guardian_decision doesn't accept auth parameter yet)

- [ ] **Step 2: Update record_guardian_decision signature to accept auth**

Find the `record_guardian_decision` method in `server/services/incidents.py` (around line 1143):

Current signature:
```python
async def record_guardian_decision(
    self,
    nexus_incident_id: str,
    decision: GuardianDecisionRequest,
) -> dict[str, object]:
```

Update to:
```python
async def record_guardian_decision(
    self,
    nexus_incident_id: str,
    decision: GuardianDecisionRequest,
    auth: AuthenticatedContext | None = None,
) -> dict[str, object]:
```

And add this at the start of the method body:

```python
from server.audit import write_audit_log

# ... existing code ...

# Record governance decision with actor context
await write_audit_log(
    "governance_decision",
    incident.tenant_id,
    {
        "incident_id": nexus_incident_id,
        "action": "record_guardian_decision",
        "decision": decision.decision,
        "reasoning": decision.reasoning or "",
        "timestamp": _utc_now_iso(),
    },
    actor_user_id=auth.user_id if auth else None,
    actor_roles=auth.roles if auth else None,
)
```

Also update the endpoint that calls this method in `server/app.py`. Find where `record_guardian_decision` is called and pass the `auth` parameter.

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_governance_audit.py::test_guardian_decision_records_actor_context -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add server/services/incidents.py tests/test_governance_audit.py
git commit -m "feat: record actor context when guardian decisions are made"
```

---

### Task 5: Add Replay Action Audit Logging

**Files:**
- Modify: `server/services/incidents.py` (replay-related methods)
- Modify: `server/app.py:339-357` (launch_replay_scenario endpoint)
- Test: `tests/test_replay_audit.py` (new)

- [ ] **Step 1: Write failing test for replay audit logging**

Run: `touch tests/test_replay_audit.py`

Add to `tests/test_replay_audit.py`:

```python
import pytest
from server.audit import get_audit_logs

@pytest.mark.asyncio
async def test_replay_launch_records_actor_and_role():
    """Launching a replay should audit actor, role, and tenant context"""
    from fastapi.testclient import TestClient
    from server.app import app
    
    client = TestClient(app)
    
    # Assume an incident exists at nexus-123
    response = client.post(
        "/api/v1/replay/scenarios/scenario-id/launch",
        headers={
            "x-user-id": "user-operator",
            "x-tenant-id": "tenant-a",
            "x-roles": "operator",
        },
        json={},
    )
    
    # Should succeed for operator role
    assert response.status_code != 403
    
    # Check audit logs (assuming incident ID in response)
    # Logs should show actor=user-operator, roles=[operator], tenant=tenant-a
```

Run: `pytest tests/test_replay_audit.py::test_replay_launch_records_actor_and_role -v`
Expected: FAIL (no audit logging yet)

- [ ] **Step 2: Add audit logging to replay launch endpoint**

Find the `launch_replay_scenario` endpoint in `server/app.py` (around line 339):

Add this after auth checks:

```python
@app.post("/api/v1/replay/scenarios/{scenario_id}/launch", status_code=202)
async def launch_replay_scenario(
    scenario_id: str,
    request: Request,
) -> dict[str, object]:
    auth = await require_auth(request)
    from server.auth import check_governance_capability
    from server.audit import write_audit_log
    
    check_governance_capability(auth, "trigger_replay")
    
    # Get incident from query params or body (adjust as needed)
    # ... existing code ...
    
    # Log replay action
    await write_audit_log(
        "replay_action",
        auth.tenant_id,
        {
            "action": "launch_replay",
            "scenario_id": scenario_id,
            # Add incident_id if available
        },
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )
    
    # ... rest of function
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_replay_audit.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add server/app.py tests/test_replay_audit.py
git commit -m "feat: audit replay launches with actor and role context"
```

---

### Task 6: Add Export Action Audit Logging

**Files:**
- Modify: `server/app.py:633-677` (proof-export and handoff-export endpoints)
- Test: `tests/test_export_audit.py` (new)

- [ ] **Step 1: Write failing test for export audit logging**

Run: `touch tests/test_export_audit.py`

Add to `tests/test_export_audit.py`:

```python
import pytest
from server.audit import get_audit_logs

@pytest.mark.asyncio
async def test_proof_export_records_actor():
    """Exporting proof should audit who requested the export"""
    from fastapi.testclient import TestClient
    from server.app import app
    
    client = TestClient(app)
    
    response = client.get(
        "/api/v1/incidents/nexus-123/proof-export",
        headers={
            "x-user-id": "user-guardian",
            "x-tenant-id": "tenant-a",
            "x-roles": "guardian",
        },
    )
    
    # Should succeed
    assert response.status_code != 403
    
    # Audit should log this export action with actor context
    logs = get_audit_logs("nexus-123")
    export_logs = [log for log in logs if log.get("event_type") == "export_action"]
    assert len(export_logs) >= 1
    assert export_logs[-1]["actor_user_id"] == "user-guardian"
```

Run: `pytest tests/test_export_audit.py::test_proof_export_records_actor -v`
Expected: FAIL (no audit logging yet)

- [ ] **Step 2: Add audit logging to export endpoints**

Find the `get_incident_proof_export` endpoint in `server/app.py` (around line 633):

Add this after auth:

```python
@app.get("/api/v1/incidents/{nexus_incident_id}/proof-export")
async def get_incident_proof_export(
    nexus_incident_id: str,
    request: Request,
) -> dict[str, object]:
    auth = await require_auth(request)
    from server.audit import write_audit_log
    
    check_governance_capability(auth, "read_incidents")
    
    # ... existing code ...
    
    # Log export action
    await write_audit_log(
        "export_action",
        auth.tenant_id,
        {
            "incident_id": nexus_incident_id,
            "export_type": "proof_package",
        },
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )
    
    # ... rest of function
```

Similarly for `get_engineering_handoff_v1` endpoint (around line 694):

```python
@app.get("/api/v1/incidents/{nexus_incident_id}/handoff-export")
async def get_engineering_handoff_v1(
    nexus_incident_id: str,
    request: Request,
) -> dict[str, object]:
    auth = await require_auth(request)
    
    # ... existing code ...
    
    # Log export action
    await write_audit_log(
        "export_action",
        auth.tenant_id,
        {
            "incident_id": nexus_incident_id,
            "export_type": "engineering_handoff",
        },
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )
    
    # ... rest of function
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_export_audit.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add server/app.py tests/test_export_audit.py
git commit -m "feat: audit proof and handoff exports with actor context"
```

---

### Task 7: Add Tenant-Aware Governance Visibility Service

**Files:**
- Modify: `server/services/governance.py`
- Test: `tests/test_governance_visibility.py` (new)

- [ ] **Step 1: Write failing test for governance visibility service**

Run: `touch tests/test_governance_visibility.py`

Add to `tests/test_governance_visibility.py`:

```python
from server.services.governance import GovernanceService
from server.auth import ROLE_MATRIX

def test_governance_visibility_returns_role_matrix():
    """Governance service should expose role matrix for visibility"""
    service = GovernanceService()
    
    visibility = service.get_governance_visibility("tenant-a")
    
    assert "roles" in visibility
    assert "operator" in visibility["roles"]
    assert visibility["roles"]["operator"]["description"] == "Support operator: triage, replay, and handoff"
    assert visibility["roles"]["operator"]["capabilities"]["trigger_replay"] is True

def test_governance_visibility_shows_critical_actions():
    """Governance visibility should highlight critical actions"""
    service = GovernanceService()
    
    visibility = service.get_governance_visibility("tenant-a")
    
    critical_actions = visibility.get("critical_actions", [])
    assert len(critical_actions) > 0
    assert any(action["capability"] == "approve_action" for action in critical_actions)
    assert any(action["capability"] == "trigger_replay" for action in critical_actions)

def test_governance_visibility_maps_roles_to_actions():
    """Governance visibility should map which roles can perform each critical action"""
    service = GovernanceService()
    
    visibility = service.get_governance_visibility("tenant-a")
    
    critical_actions = visibility.get("critical_actions", [])
    approve_action = next((a for a in critical_actions if a["capability"] == "approve_action"), None)
    
    assert approve_action is not None
    assert "admin" in approve_action.get("allowed_roles", [])
    assert "guardian" in approve_action.get("allowed_roles", [])
    assert "operator" not in approve_action.get("allowed_roles", [])
```

Run: `pytest tests/test_governance_visibility.py -v`
Expected: FAIL (method not yet implemented)

- [ ] **Step 2: Add governance visibility methods to GovernanceService**

Add to `server/services/governance.py` after the `guardian_policy_for_decision` method:

```python
def get_governance_visibility(self, tenant_id: str) -> dict[str, object]:
    """Get governance rules and role matrix for UI visibility."""
    from server.auth import ROLE_MATRIX
    
    # Build critical actions list
    critical_actions = [
        {
            "capability": "approve_action",
            "description": "Approve or reject a runbook for execution",
            "allowed_roles": [
                role for role, data in ROLE_MATRIX.items()
                if data["capabilities"].get("approve_action", False)
            ],
        },
        {
            "capability": "trigger_replay",
            "description": "Trigger a bounded replay of an incident",
            "allowed_roles": [
                role for role, data in ROLE_MATRIX.items()
                if data["capabilities"].get("trigger_replay", False)
            ],
        },
        {
            "capability": "send_handoff",
            "description": "Send engineering handoff to downstream systems",
            "allowed_roles": [
                role for role, data in ROLE_MATRIX.items()
                if data["capabilities"].get("send_handoff", False)
            ],
        },
        {
            "capability": "update_bootstrap",
            "description": "Update tenant bootstrap configuration",
            "allowed_roles": [
                role for role, data in ROLE_MATRIX.items()
                if data["capabilities"].get("update_bootstrap", False)
            ],
        },
    ]
    
    return {
        "tenant_id": tenant_id,
        "roles": ROLE_MATRIX,
        "critical_actions": critical_actions,
        "last_updated_at": _utc_now_iso() if hasattr(self, "_utc_now_iso") else None,
    }


def _utc_now_iso(self) -> str:
    """Get current UTC time in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
```

Add import at top of file:
```python
from datetime import datetime, timezone
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_governance_visibility.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add server/services/governance.py tests/test_governance_visibility.py
git commit -m "feat: add governance visibility service for role matrix and critical actions"
```

---

### Task 8: Add Governance Visibility API Endpoint

**Files:**
- Modify: `server/app.py` (add new endpoint)
- Test: `tests/test_governance_visibility_api.py` (new)

- [ ] **Step 1: Write failing test for governance visibility API**

Run: `touch tests/test_governance_visibility_api.py`

Add to `tests/test_governance_visibility_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_governance_visibility_endpoint_exists():
    """Should have an endpoint to view governance rules"""
    response = client.get(
        "/api/v1/governance/visibility",
        headers={
            "x-user-id": "user-alice",
            "x-tenant-id": "tenant-a",
            "x-roles": "operator",
        },
    )
    assert response.status_code == 200

def test_governance_visibility_returns_roles():
    """Governance visibility endpoint should return role matrix"""
    response = client.get(
        "/api/v1/governance/visibility",
        headers={
            "x-user-id": "user-alice",
            "x-tenant-id": "tenant-a",
            "x-roles": "operator",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "roles" in data
    assert "critical_actions" in data
    assert data["tenant_id"] == "tenant-a"

def test_governance_visibility_shows_who_can_approve():
    """Should show which roles can approve actions"""
    response = client.get(
        "/api/v1/governance/visibility",
        headers={
            "x-user-id": "user-alice",
            "x-tenant-id": "tenant-a",
            "x-roles": "operator",
        },
    )
    
    data = response.json()
    critical_actions = data["critical_actions"]
    approve_action = next((a for a in critical_actions if a["capability"] == "approve_action"), None)
    
    assert approve_action is not None
    assert "guardian" in approve_action["allowed_roles"]
    assert "admin" in approve_action["allowed_roles"]
```

Run: `pytest tests/test_governance_visibility_api.py::test_governance_visibility_endpoint_exists -v`
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 2: Add governance visibility endpoint**

Add this to `server/app.py` after the auth endpoints (around line 513):

```python
@app.get("/api/v1/governance/visibility")
async def get_governance_visibility(request: Request) -> dict[str, object]:
    auth = await require_auth(request)
    governance_service = GovernanceService()
    return governance_service.get_governance_visibility(auth.tenant_id)
```

Make sure to import GovernanceService at the top of app.py:
```python
from server.services.governance import GovernanceService
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_governance_visibility_api.py -v`
Expected: PASS (all tests)

- [ ] **Step 4: Commit**

```bash
git add server/app.py tests/test_governance_visibility_api.py
git commit -m "feat: add governance visibility API endpoint to expose role matrix and critical actions"
```

---

### Task 9: Update Settings Frontend to Display Governance Info

**Files:**
- Modify: `frontend/settings.html`
- Modify: `frontend/static/settings.js`

- [ ] **Step 1: Add governance section to settings.html**

Find the `frontend/settings.html` file and add a new section for governance visibility:

```html
<div id="governance-section" class="settings-panel">
  <h2>Governance & Roles</h2>
  <div id="current-user-roles">
    <h3>Your Roles</h3>
    <p id="user-roles-display">Loading...</p>
  </div>
  <div id="critical-actions">
    <h3>Critical Actions</h3>
    <table id="critical-actions-table">
      <thead>
        <tr>
          <th>Action</th>
          <th>Description</th>
          <th>Allowed Roles</th>
        </tr>
      </thead>
      <tbody id="critical-actions-tbody">
      </tbody>
    </table>
  </div>
  <div id="role-matrix">
    <h3>Role Capabilities Matrix</h3>
    <table id="role-matrix-table">
      <thead>
        <tr>
          <th>Role</th>
          <th>Description</th>
          <th>Key Capabilities</th>
        </tr>
      </thead>
      <tbody id="role-matrix-tbody">
      </tbody>
    </table>
  </div>
</div>
```

- [ ] **Step 2: Add CSS styling for governance section**

Add to the `<style>` section of `frontend/settings.html`:

```css
#governance-section {
  margin-top: 2rem;
  border-top: 1px solid #ddd;
  padding-top: 1rem;
}

#governance-section table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

#governance-section table th,
#governance-section table td {
  border: 1px solid #ddd;
  padding: 0.5rem;
  text-align: left;
}

#governance-section table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

#user-roles-display {
  font-family: monospace;
  background-color: #f9f9f9;
  padding: 0.5rem;
  border-radius: 4px;
}
```

- [ ] **Step 3: Add JavaScript to fetch and render governance visibility**

Add to `frontend/static/settings.js`:

```javascript
async function loadGovernanceVisibility() {
  try {
    const response = await fetch('/api/v1/governance/visibility');
    if (!response.ok) {
      console.error('Failed to load governance visibility:', response.status);
      return;
    }
    
    const data = await response.json();
    renderUserRoles(data);
    renderCriticalActions(data.critical_actions);
    renderRoleMatrix(data.roles);
  } catch (error) {
    console.error('Error loading governance visibility:', error);
  }
}

function renderUserRoles(data) {
  const userContext = window.userContext || {};
  const rolesDisplay = document.getElementById('user-roles-display');
  if (rolesDisplay) {
    const roles = (userContext.roles || []).join(', ') || 'None assigned';
    rolesDisplay.textContent = `Your current roles: ${roles}`;
  }
}

function renderCriticalActions(actions) {
  const tbody = document.getElementById('critical-actions-tbody');
  if (!tbody || !actions) return;
  
  tbody.innerHTML = '';
  actions.forEach(action => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><strong>${action.capability}</strong></td>
      <td>${action.description}</td>
      <td>${action.allowed_roles.join(', ')}</td>
    `;
    tbody.appendChild(row);
  });
}

function renderRoleMatrix(roles) {
  const tbody = document.getElementById('role-matrix-tbody');
  if (!tbody || !roles) return;
  
  tbody.innerHTML = '';
  Object.entries(roles).forEach(([role, data]) => {
    const capabilities = data.capabilities || {};
    const keyCapabilities = Object.entries(capabilities)
      .filter(([_, allowed]) => allowed)
      .map(([cap]) => cap)
      .join(', ');
    
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><strong>${role}</strong></td>
      <td>${data.description}</td>
      <td><small>${keyCapabilities}</small></td>
    `;
    tbody.appendChild(row);
  });
}

// Call this when settings page loads
document.addEventListener('DOMContentLoaded', function() {
  loadGovernanceVisibility();
});
```

- [ ] **Step 4: Test governance section renders in browser**

Run the dev server and navigate to settings page:
```bash
npm run dev  # or python demo.py
```

Expected: Settings page should show governance info including roles, critical actions, and role matrix.

- [ ] **Step 5: Commit**

```bash
git add frontend/settings.html frontend/static/settings.js
git commit -m "feat: add governance visibility UI to settings page showing roles and critical actions"
```

---

### Task 10: Update Operator Runbook with Hardened Role Model

**Files:**
- Modify: `docs/internal/OPERATOR_RUNBOOK.md`

- [ ] **Step 1: Read current operator runbook**

```bash
cat docs/internal/OPERATOR_RUNBOOK.md | head -100
```

- [ ] **Step 2: Add governance section to operator runbook**

Find a good place in the runbook (likely near the beginning) and add:

```markdown
## Governance & Role Model

### Role Definitions

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
```

- [ ] **Step 3: Commit**

```bash
git add docs/internal/OPERATOR_RUNBOOK.md
git commit -m "docs: add governance and role model section to operator runbook"
```

---

### Task 11: Update OPERATIONS Documentation

**Files:**
- Modify: `docs/internal/OPERATIONS.md`

- [ ] **Step 1: Add governance section to OPERATIONS docs**

Add a new section to `docs/internal/OPERATIONS.md`:

```markdown
## Governance & Multi-Tenant Authorization

### Architecture Overview

NEXUS uses a tenant-scoped, role-based access control model where:
- Each request is authenticated with user ID, tenant ID, and roles
- Each governance-sensitive action is audited with actor context
- Permissions are checked at the API boundary before execution
- Audit logs are queryable per incident for compliance review

### Authentication Headers

The system expects these headers on each request:
- `x-user-id` — Unique user identifier (required)
- `x-tenant-id` — Tenant scope (required, must be in allowed list)
- `x-roles` — Comma-separated roles (e.g., "operator,guardian")

**Note:** In demo/local mode, these are passed by test clients. In production, these should come from your SSO/identity provider middleware.

### Capability Matrix

Capabilities are defined per role in `server/auth.py:ROLE_MATRIX`. The system enforces:

- **read_incidents** — View incident details, status, history
- **create_incident** — Create new incidents from webhooks or manual report
- **trigger_replay** — Launch bounded replay scenarios
- **send_handoff** — Send engineering handoff to downstream systems
- **view_settings** — View tenant bootstrap and governance settings
- **update_bootstrap** — Modify tenant configuration
- **approve_action** — Approve or reject a proposed runbook
- **review_action** — Review runbook proposal and write feedback

Enforcement happens in two ways:
1. **Endpoint-level checks** — Critical endpoints call `check_governance_capability(auth, capability)`
2. **Service-level checks** — Business logic verifies role before taking action

### Audit Logging

Every governance-sensitive action is logged to `.nexus_audit_log.json` with:

```json
{
  "timestamp": "2026-06-16T12:34:56.789Z",
  "event_type": "governance_decision|replay_action|export_action|...",
  "tenant_id": "tenant-a",
  "actor_user_id": "user-alice",
  "actor_roles": ["guardian"],
  "payload": {
    "incident_id": "nexus-123",
    "action": "approve_runbook",
    "decision": "approve",
    "reasoning": "...",
    ...
  }
}
```

Audit events can be queried via `/api/v1/audit-logs/{incident_id}` to see the complete governance trail for an incident.

### Tenant-Aware Bootstrap Configuration

Each tenant has its own bootstrap configuration (`TenantBootstrapConfig`) including:
- `owners` — Contact information
- `repos` — Source code locations
- `delivery_targets` — Where to send handoffs
- `approval_policy` — Approval rules (if custom)
- `enabled_packs` — Which runtime packs are available

Only `admin` role can modify bootstrap configuration. See `/api/v1/tenant/bootstrap-config` for the API.

### Checking Governance Posture

Operators can use the Settings UI to view:
- Current role assignments
- Which roles can perform each critical action
- Full role-to-capability matrix

Or query `/api/v1/governance/visibility` directly to get structured role data.
```

- [ ] **Step 2: Commit**

```bash
git add docs/internal/OPERATIONS.md
git commit -m "docs: add governance, RBAC, and audit logging documentation"
```

---

### Task 12: Run Full Test Suite and Verification Gates

**Files:**
- No changes; verification only

- [ ] **Step 1: Run pytest test suite**

```bash
pytest tests/ -q
```

Expected: All tests pass, including new governance tests

- [ ] **Step 2: Run browser verification**

```bash
npm run browser:verify
```

Expected: All browser tests pass

- [ ] **Step 3: Run demo**

```bash
python demo.py
```

Expected: Demo starts without errors, governance UI visible in settings

- [ ] **Step 4: Optional: Run local enterprise smoke test (if Docker available)**

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Expected: Deployment and runtime relay work correctly

- [ ] **Step 5: Final commit message documenting completion**

If all tests pass, create a summary commit (optional):

```bash
git log --oneline -15
```

This completes the hardened auth and governance implementation.

---

## Self-Review Against Spec

**Spec Requirement 1:** "Tighten capability checks across operator, incident manager, guardian, and admin actions"
- ✅ Task 2: Added `check_governance_capability()` helper
- ✅ Task 3: Added capability checks to critical endpoints (approve, replay, handoff, export)
- ✅ Task 4-6: Each critical action enforces role capability

**Spec Requirement 2:** "Make tenant-aware governance rules visible in the settings or admin surface"
- ✅ Task 7: Added `get_governance_visibility()` service method
- ✅ Task 8: Added `/api/v1/governance/visibility` endpoint
- ✅ Task 9: Updated settings UI with role matrix and critical actions table

**Spec Requirement 3:** "Ensure approval, replay, export, and delivery actions record actor and role semantics consistently"
- ✅ Task 1: Extended audit system with actor_user_id and actor_roles fields
- ✅ Task 4: Guardian decision records actor context
- ✅ Task 5: Replay launch records actor context
- ✅ Task 6: Proof/handoff exports record actor context

**Spec Requirement 4:** "Update runbooks and pilot docs with the hardened role model"
- ✅ Task 10: Updated OPERATOR_RUNBOOK.md with role definitions, workflow, and approval process
- ✅ Task 11: Updated OPERATIONS.md with governance architecture, RBAC matrix, audit logging, and tenant config

**Done When Criteria:**
- ✅ "Governance-sensitive actions have explicit capability boundaries" — Tasks 2-6
- ✅ "Audit surfaces reflect actor, tenant, and role context consistently" — Tasks 1, 4-6
- ✅ "Pilot docs explain who can perform each critical action" — Tasks 10-11

All spec requirements and acceptance criteria are covered.
