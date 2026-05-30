from __future__ import annotations

from fastapi import HTTPException, Request


class TenancyService:
    def resolve_webhook_tenant(self, request: Request) -> str:
        tenant_id = request.headers.get("x-tenant-id", "tenant-system").strip() or "tenant-system"
        allowed_tenants = getattr(getattr(request.app.state, "config", None), "allowed_tenant_ids", ["tenant-a", "tenant-system"])
        if tenant_id not in allowed_tenants:
            raise HTTPException(status_code=403, detail="tenant not allowed")
        return tenant_id
