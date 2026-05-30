from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field


class AuthenticatedContext(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)


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
