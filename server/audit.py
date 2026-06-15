from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from server.artifacts import record_audit_event


_AUDIT_LOCK = asyncio.Lock()
_AUDIT_CACHE: list[dict[str, object]] | None = None


logger = logging.getLogger(__name__)


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


def get_audit_logs(incident_id: str | None = None) -> list[dict[str, object]]:
    logs = _load_audit_logs()
    if incident_id is None:
        return list(logs)

    matching: list[dict[str, object]] = []
    for entry in logs:
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            continue
        payload_incident_id = payload.get("incident_id") or payload.get("nexus_incident_id")
        if payload_incident_id == incident_id:
            matching.append(entry)
    return matching


def _audit_log_path() -> Path:
    return Path.cwd() / ".nexus_audit_log.json"


def _load_audit_logs() -> list[dict[str, object]]:
    global _AUDIT_CACHE
    path = _audit_log_path()
    if _AUDIT_CACHE is not None and not path.exists():
        return list(_AUDIT_CACHE)

    if not path.exists():
        _AUDIT_CACHE = []
        return []

    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        logger.exception("invalid audit log payload at %s", path)
        _AUDIT_CACHE = []
        return []

    if not isinstance(payload, list):
        logger.error("audit log payload at %s must be a JSON array", path)
        _AUDIT_CACHE = []
        return []

    entries: list[dict[str, object]] = []
    for item in payload:
        if isinstance(item, dict):
            entries.append(item)
    _AUDIT_CACHE = entries
    return list(entries)


def _persist_audit_logs(entries: list[dict[str, object]]) -> None:
    global _AUDIT_CACHE
    path = _audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(entries, indent=2, sort_keys=True))
    temp_path.replace(path)
    _AUDIT_CACHE = list(entries)
