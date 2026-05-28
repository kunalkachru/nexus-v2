from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


async def write_audit_log(event_type: str, tenant_id: str, payload: dict[str, object]) -> None:
    logger.info("audit event=%s tenant=%s payload=%s", event_type, tenant_id, payload)
