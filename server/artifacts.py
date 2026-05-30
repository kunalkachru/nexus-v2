from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path


_ARTIFACT_LOCK = asyncio.Lock()
_ARTIFACT_CACHE: dict[str, list[dict[str, object]]] | None = None


def _artifact_path() -> Path:
    return Path.cwd() / "artifacts" / "platform_artifacts.json"


def _default_payload() -> dict[str, list[dict[str, object]]]:
    return {
        "replay_launches": [],
        "training_snapshots": [],
        "learning_contracts": [],
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
    result = {
        "replay_launches": [item for item in replay_launches if isinstance(item, dict)],
        "training_snapshots": [item for item in training_snapshots if isinstance(item, dict)],
        "learning_contracts": [item for item in learning_contracts if isinstance(item, dict)],
    }
    _ARTIFACT_CACHE = result
    return {key: list(value) for key, value in result.items()}


def _persist_artifacts(payload: dict[str, list[dict[str, object]]]) -> None:
    global _ARTIFACT_CACHE
    path = _artifact_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    temp_path.replace(path)
    _ARTIFACT_CACHE = {key: list(value) for key, value in payload.items()}


async def record_replay_launch(record: dict[str, object]) -> None:
    async with _ARTIFACT_LOCK:
        payload = _load_artifacts()
        payload["replay_launches"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **record,
            }
        )
        _persist_artifacts(payload)


async def record_training_snapshot(record: dict[str, object]) -> None:
    async with _ARTIFACT_LOCK:
        payload = _load_artifacts()
        payload["training_snapshots"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **record,
            }
        )
        _persist_artifacts(payload)


async def record_learning_contract(record: dict[str, object]) -> None:
    async with _ARTIFACT_LOCK:
        payload = _load_artifacts()
        payload["learning_contracts"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **record,
            }
        )
        _persist_artifacts(payload)


def get_artifact_summary() -> dict[str, int]:
    payload = _load_artifacts()
    return {
        "replay_launches": len(payload["replay_launches"]),
        "training_snapshots": len(payload["training_snapshots"]),
        "learning_contracts": len(payload["learning_contracts"]),
    }
