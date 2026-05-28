from __future__ import annotations

from fastapi import Request


class TenancyService:
    def resolve_webhook_tenant(self, request: Request) -> str:
        return request.headers.get("x-tenant-id", "tenant-system").strip() or "tenant-system"
