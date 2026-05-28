from __future__ import annotations

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

    return AuthenticatedContext(user_id=user_id, tenant_id=tenant_id, roles=roles)
