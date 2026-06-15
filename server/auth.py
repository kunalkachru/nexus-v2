from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field


class AuthenticatedContext(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)


ROLE_MATRIX = {
    "operator": {
        "description": "Support operator: triage, replay, and handoff",
        "capabilities": {
            "read_incidents": True,
            "create_incident": True,
            "trigger_replay": True,
            "send_handoff": True,
            "view_settings": True,
            "update_bootstrap": False,
            "approve_action": False,
            "review_action": False,
        },
    },
    "incident_manager": {
        "description": "Incident manager: operator + incident management controls",
        "capabilities": {
            "read_incidents": True,
            "create_incident": True,
            "trigger_replay": True,
            "send_handoff": True,
            "view_settings": True,
            "update_bootstrap": False,
            "approve_action": False,
            "review_action": True,
        },
    },
    "guardian": {
        "description": "Guardian reviewer: approves and executes suggested actions",
        "capabilities": {
            "read_incidents": True,
            "create_incident": False,
            "trigger_replay": False,
            "send_handoff": False,
            "view_settings": True,
            "update_bootstrap": False,
            "approve_action": True,
            "review_action": True,
        },
    },
    "admin": {
        "description": "Administrator: full system access including bootstrap configuration",
        "capabilities": {
            "read_incidents": True,
            "create_incident": True,
            "trigger_replay": True,
            "send_handoff": True,
            "view_settings": True,
            "update_bootstrap": True,
            "approve_action": True,
            "review_action": True,
        },
    },
}


def get_user_capabilities(roles: list[str]) -> dict[str, bool]:
    capabilities = {
        "read_incidents": False,
        "create_incident": False,
        "trigger_replay": False,
        "send_handoff": False,
        "view_settings": False,
        "update_bootstrap": False,
        "approve_action": False,
        "review_action": False,
    }

    for role in roles:
        role_data = ROLE_MATRIX.get(role, {})
        for capability, allowed in role_data.get("capabilities", {}).items():
            if allowed:
                capabilities[capability] = True

    return capabilities


def require_role(auth: AuthenticatedContext, *allowed_roles: str) -> None:
    if not allowed_roles:
        return
    if not auth.roles:
        raise HTTPException(status_code=403, detail="role required")
    allowed = {role.strip() for role in allowed_roles if role.strip()}
    if not allowed.intersection(set(auth.roles)):
        raise HTTPException(status_code=403, detail="role not allowed")


async def require_auth(request: Request) -> AuthenticatedContext:
    user_id = request.headers.get("x-user-id", "").strip()
    tenant_id = request.headers.get("x-tenant-id", "").strip()
    roles_header = request.headers.get("x-roles", "")
    roles = [role.strip() for role in roles_header.split(",") if role.strip()]

    if not user_id or not tenant_id:
        raise HTTPException(status_code=401, detail="authentication required")

    allowed_tenants = getattr(getattr(request.app.state, "config", None), "allowed_tenant_ids", ["tenant-a", "tenant-system"])
    if tenant_id not in allowed_tenants:
        raise HTTPException(status_code=403, detail="tenant not allowed")

    return AuthenticatedContext(user_id=user_id, tenant_id=tenant_id, roles=roles)


async def verify_webhook_signature(request: Request) -> None:
    provided = request.headers.get("x-signature", "").strip()
    if not provided.startswith("sha256="):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    raw_body = await request.body()
    secret = getattr(getattr(request.app.state, "config", None), "webhook_signing_secret", "")
    expected_digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    expected = f"sha256={expected_digest}"
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid webhook signature")


async def require_runtime_host_auth(request: Request) -> None:
    configured = getattr(getattr(request.app.state, "config", None), "runtime_host_shared_token", "").strip()
    if not configured:
        raise HTTPException(status_code=503, detail="runtime host token not configured")
    provided = request.headers.get("x-runtime-host-token", "").strip()
    if not provided or not hmac.compare_digest(provided, configured):
        raise HTTPException(status_code=401, detail="invalid runtime host token")
