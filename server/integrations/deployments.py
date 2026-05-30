from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class DeploymentLookupService:
    def __init__(self, deployments_path: Path | None = None) -> None:
        self._deployments_path = deployments_path or Path(
            os.environ.get("NEXUS_DEPLOYMENTS_PATH", "artifacts/deployments.json")
        )
        self._catalog: list[dict[str, object]] | None = None

    async def get_recent_deployments(self, service_name: str) -> list[dict[str, object]]:
        if not service_name:
            return []
        deployments = [record for record in self._load_catalog() if self._matches_service(record, service_name)]
        deployments.sort(key=self._deployment_sort_key, reverse=True)
        return deployments[:3]

    def _load_catalog(self) -> list[dict[str, object]]:
        if self._catalog is not None:
            return list(self._catalog)
        path = self._deployments_path
        if not path.exists():
            self._catalog = []
            return []
        try:
            payload = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self._catalog = []
            return []

        records: list[dict[str, object]] = []
        if isinstance(payload, dict):
            if isinstance(payload.get("deployments"), list):
                for record in payload["deployments"]:
                    if isinstance(record, dict):
                        records.append(dict(record))
            else:
                for service_name, service_records in payload.items():
                    if not isinstance(service_records, list):
                        continue
                    for record in service_records:
                        if isinstance(record, dict):
                            records.append({"service": service_name, **record})
        elif isinstance(payload, list):
            for record in payload:
                if isinstance(record, dict):
                    records.append(dict(record))

        self._catalog = records
        return list(records)

    def _matches_service(self, record: dict[str, object], service_name: str) -> bool:
        candidate = str(record.get("service", "")).strip()
        if not candidate:
            return False
        return candidate == service_name

    def _deployment_sort_key(self, record: dict[str, object]) -> datetime:
        raw_time = str(record.get("time") or record.get("deployed_at") or record.get("timestamp") or "").strip()
        if not raw_time:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
