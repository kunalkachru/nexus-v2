from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path


logger = logging.getLogger(__name__)
_ARTIFACT_LOCK = asyncio.Lock()
_ARTIFACT_CACHE: dict[str, list[dict[str, object]]] | None = None


def _artifact_path() -> Path:
    return Path.cwd() / "artifacts" / "platform_artifacts.json"


def _default_payload() -> dict[str, list[dict[str, object]]]:
    return {
        "replay_launches": [],
        "training_snapshots": [],
        "learning_contracts": [],
        "audit_events": [],
        "guardian_reviews": [],
        "execution_events": [],
        "runtime_queue_jobs": [],
    }


def _load_artifacts() -> dict[str, list[dict[str, object]]]:
    global _ARTIFACT_CACHE
    path = _artifact_path()
    if _ARTIFACT_CACHE is not None and not path.exists():
        return {key: list(value) for key, value in _ARTIFACT_CACHE.items()}

    if not path.exists():
        _ARTIFACT_CACHE = _default_payload()
        return _default_payload()

    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _ARTIFACT_CACHE = _default_payload()
        return _default_payload()

    if not isinstance(payload, dict):
        _ARTIFACT_CACHE = _default_payload()
        return _default_payload()

    replay_launches = payload.get("replay_launches", [])
    training_snapshots = payload.get("training_snapshots", [])
    learning_contracts = payload.get("learning_contracts", [])
    audit_events = payload.get("audit_events", [])
    guardian_reviews = payload.get("guardian_reviews", [])
    execution_events = payload.get("execution_events", [])
    runtime_queue_jobs = payload.get("runtime_queue_jobs", [])
    result = {
        "replay_launches": [item for item in replay_launches if isinstance(item, dict)],
        "training_snapshots": [item for item in training_snapshots if isinstance(item, dict)],
        "learning_contracts": [item for item in learning_contracts if isinstance(item, dict)],
        "audit_events": [item for item in audit_events if isinstance(item, dict)],
        "guardian_reviews": [item for item in guardian_reviews if isinstance(item, dict)],
        "execution_events": [item for item in execution_events if isinstance(item, dict)],
        "runtime_queue_jobs": [item for item in runtime_queue_jobs if isinstance(item, dict)],
    }
    _ARTIFACT_CACHE = result
    return {key: list(value) for key, value in result.items()}


def _validate_artifacts_payload(payload: dict[str, list[dict[str, object]]]) -> None:
    required_keys = {
        "replay_launches",
        "training_snapshots",
        "learning_contracts",
        "audit_events",
        "guardian_reviews",
        "execution_events",
        "runtime_queue_jobs",
    }
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dict")
    for key in required_keys:
        if key not in payload:
            raise ValueError(f"Missing required key: {key}")
        if not isinstance(payload[key], list):
            raise ValueError(f"Key {key} must be a list, got {type(payload[key])}")


def _persist_artifacts(payload: dict[str, list[dict[str, object]]]) -> None:
    global _ARTIFACT_CACHE
    path = _artifact_path()

    try:
        _validate_artifacts_payload(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        temp_path.write_text(serialized)
        temp_path.replace(path)
        _ARTIFACT_CACHE = {key: list(value) for key, value in payload.items()}
    except (OSError, json.JSONDecodeError, ValueError) as e:
        logger.exception("Failed to persist artifacts to %s", path)
        raise


async def record_replay_launch(record: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            payload["replay_launches"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **record,
                }
            )
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to record replay launch (non-fatal): %s", e)


async def record_training_snapshot(record: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            payload["training_snapshots"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **record,
                }
            )
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to record training snapshot (non-fatal): %s", e)


async def record_learning_contract(record: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            payload["learning_contracts"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **record,
                }
            )
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to record learning contract (non-fatal): %s", e)


async def record_audit_event(record: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            payload["audit_events"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **record,
                }
            )
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to record audit event (non-fatal): %s", e)


async def record_guardian_review(record: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            payload["guardian_reviews"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **record,
                }
            )
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to record guardian review (non-fatal): %s", e)


async def record_execution_event(record: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            payload["execution_events"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **record,
                }
            )
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to record execution event (non-fatal): %s", e)


async def record_runtime_queue_job(record: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            payload["runtime_queue_jobs"].append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **record,
                }
            )
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to record runtime queue job (non-fatal): %s", e)


async def update_runtime_queue_job(job_id: str, updates: dict[str, object]) -> None:
    try:
        async with _ARTIFACT_LOCK:
            payload = _load_artifacts()
            jobs = payload.get("runtime_queue_jobs", [])
            for job in jobs:
                if isinstance(job, dict) and job.get("job_id") == job_id:
                    job.update(updates)
                    job["updated_at"] = datetime.now(timezone.utc).isoformat()
                    break
            _persist_artifacts(payload)
    except Exception as e:
        logger.warning("Failed to update runtime queue job (non-fatal): %s", e)


def get_runtime_queue_jobs() -> list[dict[str, object]]:
    payload = _load_artifacts()
    return [item for item in payload.get("runtime_queue_jobs", []) if isinstance(item, dict)]


def get_artifact_summary() -> dict[str, int]:
    payload = _load_artifacts()
    return {
        "replay_launches": len(payload["replay_launches"]),
        "training_snapshots": len(payload["training_snapshots"]),
        "learning_contracts": len(payload["learning_contracts"]),
        "audit_events": len(payload["audit_events"]),
        "guardian_reviews": len(payload["guardian_reviews"]),
        "execution_events": len(payload["execution_events"]),
        "runtime_queue_jobs": len(payload.get("runtime_queue_jobs", [])),
    }
