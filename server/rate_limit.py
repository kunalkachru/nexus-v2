from __future__ import annotations

from collections import defaultdict

from server.auth import AuthenticatedContext


class RateLimiter:
    def __init__(self, *, max_requests: int = 60) -> None:
        self._max_requests = max_requests
        self._requests_by_key: dict[str, int] = defaultdict(int)

    async def check(self, *, auth: AuthenticatedContext, route_key: str) -> None:
        key = f"{auth.tenant_id}:{auth.user_id}:{route_key}"
        self._requests_by_key[key] += 1
        if self._requests_by_key[key] > self._max_requests:
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="rate limit exceeded")
