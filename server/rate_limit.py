from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from server.auth import AuthenticatedContext


class RateLimiter:
    def __init__(self, *, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests_by_key: dict[str, deque[float]] = defaultdict(deque)

    async def check(self, *, auth: AuthenticatedContext, route_key: str) -> None:
        key = f"{auth.tenant_id}:{auth.user_id}:{route_key}"
        now = monotonic()
        requests = self._requests_by_key[key]

        while requests and now - requests[0] > self._window_seconds:
            requests.popleft()

        requests.append(now)
        if len(requests) > self._max_requests:
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="rate limit exceeded")
