import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from server.config import AppConfig
from server.db import create_session_factory
from server.integrations.models import IncomingIncidentWebhook
from server.repositories import IncidentRepository


def test_incoming_webhook_model_normalizes_provider_payload() -> None:
    payload = IncomingIncidentWebhook.model_validate(
        {
            "incident_id": "inc_xyz",
            "title": "Payment API timeout",
            "severity": "P1",
            "detected_at": "2026-05-25T14:32:00Z",
            "monitoring_source": "datadog",
            "metrics": {"service": "payment-svc", "error_rate": 0.45},
        }
    )

    assert payload.monitoring_source == "datadog"
    assert payload.metrics["service"] == "payment-svc"


def test_incoming_webhook_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        IncomingIncidentWebhook.model_validate(
            {
                "incident_id": "inc_xyz",
                "title": "Payment API timeout",
                "severity": "P9",
                "detected_at": "2026-05-25T14:32:00Z",
                "monitoring_source": "datadog",
                "metrics": {"service": "payment-svc"},
            }
        )


def test_incident_repository_persists_and_reads_status(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        try:
            incident = await session.incidents.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
            )
            persisted = json.loads(path.read_text())
            persisted["incidents"][incident.nexus_incident_id]["status"] = "resolved"
            path.write_text(json.dumps(persisted))
        finally:
            await session.close()

        reloaded_session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await reloaded_session.incidents.get_incident(incident.nexus_incident_id)

            assert loaded is not None
            assert loaded.status == "resolved"
        finally:
            await reloaded_session.close()

    asyncio.run(scenario())


def test_incident_repository_does_not_mutate_store_if_flush_fails() -> None:
    async def failing_flush() -> None:
        raise OSError("disk full")

    async def scenario() -> None:
        store = {}
        repository = IncidentRepository(store, failing_flush)

        with pytest.raises(OSError, match="disk full"):
            await repository.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
            )

        assert store == {}

    asyncio.run(scenario())


def test_incident_repository_persists_normalized_evidence_updates(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        try:
            incident = await session.incidents.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
                normalized_evidence={"signature": "timeout"},
            )
            updated = await session.incidents.update_incident_normalized_evidence(
                incident.nexus_incident_id,
                normalized_evidence={
                    "signature": "timeout",
                    "latest_replay": {
                        "status": "relay_executed",
                        "runtime_provenance": {"mode": "delegated_relay"},
                    },
                },
            )

            assert updated is not None
            persisted = json.loads(path.read_text())
            assert persisted["incidents"][incident.nexus_incident_id]["normalized_evidence"]["latest_replay"]["status"] == "relay_executed"
        finally:
            await session.close()

        reloaded_session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await reloaded_session.incidents.get_incident(incident.nexus_incident_id)
            assert loaded is not None
            assert loaded.normalized_evidence["latest_replay"]["runtime_provenance"]["mode"] == "delegated_relay"
        finally:
            await reloaded_session.close()

    asyncio.run(scenario())


def test_incident_repository_appends_bounded_replay_history(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        try:
            incident = await session.incidents.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
                normalized_evidence={"signature": "timeout"},
            )

            await session.incidents.append_incident_replay_evidence(
                incident.nexus_incident_id,
                latest_replay={
                    "status": "replay_executed",
                    "recorded_at": "2026-06-12T10:00:00+00:00",
                    "runtime_provenance": {"mode": "direct_runtime"},
                    "replay_lifecycle": {
                        "current_state": "completed",
                        "events": [
                            {"state": "requested"},
                            {"state": "running"},
                            {"state": "completed"},
                        ],
                    },
                },
                replay_entry={
                    "status": "replay_executed",
                    "recorded_at": "2026-06-12T10:00:00+00:00",
                    "runtime_provenance": {"mode": "direct_runtime"},
                    "replay_lifecycle": {
                        "current_state": "completed",
                        "events": [
                            {"state": "requested"},
                            {"state": "running"},
                            {"state": "completed"},
                        ],
                    },
                },
                replay_limit=2,
            )
            await session.incidents.append_incident_replay_evidence(
                incident.nexus_incident_id,
                latest_replay={
                    "status": "relay_executed",
                    "recorded_at": "2026-06-12T10:05:00+00:00",
                    "runtime_provenance": {"mode": "delegated_relay"},
                    "replay_lifecycle": {
                        "current_state": "completed",
                        "events": [
                            {"state": "requested"},
                            {"state": "running"},
                            {"state": "completed"},
                        ],
                    },
                },
                replay_entry={
                    "status": "relay_executed",
                    "recorded_at": "2026-06-12T10:05:00+00:00",
                    "runtime_provenance": {"mode": "delegated_relay"},
                    "replay_lifecycle": {
                        "current_state": "completed",
                        "events": [
                            {"state": "requested"},
                            {"state": "running"},
                            {"state": "completed"},
                        ],
                    },
                },
                replay_limit=2,
            )
            updated = await session.incidents.append_incident_replay_evidence(
                incident.nexus_incident_id,
                latest_replay={
                    "status": "replay_executed",
                    "recorded_at": "2026-06-12T10:10:00+00:00",
                    "runtime_provenance": {"mode": "direct_runtime"},
                    "replay_lifecycle": {
                        "current_state": "completed",
                        "events": [
                            {"state": "requested"},
                            {"state": "running"},
                            {"state": "completed"},
                        ],
                    },
                },
                replay_entry={
                    "status": "replay_executed",
                    "recorded_at": "2026-06-12T10:10:00+00:00",
                    "runtime_provenance": {"mode": "direct_runtime"},
                    "replay_lifecycle": {
                        "current_state": "completed",
                        "events": [
                            {"state": "requested"},
                            {"state": "running"},
                            {"state": "completed"},
                        ],
                    },
                },
                replay_limit=2,
            )

            assert updated is not None
            history = updated.normalized_evidence["replay_history"]
            assert len(history) == 2
            assert history[0]["recorded_at"] == "2026-06-12T10:10:00+00:00"
            assert history[1]["recorded_at"] == "2026-06-12T10:05:00+00:00"
            assert history[0]["runtime_provenance"]["mode"] == "direct_runtime"
            assert history[1]["runtime_provenance"]["mode"] == "delegated_relay"
            assert history[0]["replay_lifecycle"]["current_state"] == "completed"

            persisted = json.loads(path.read_text())
            persisted_history = persisted["incidents"][incident.nexus_incident_id]["normalized_evidence"]["replay_history"]
            assert len(persisted_history) == 2
        finally:
            await session.close()

        reloaded_session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await reloaded_session.incidents.get_incident(incident.nexus_incident_id)
            assert loaded is not None
            history = loaded.normalized_evidence["replay_history"]
            assert [entry["runtime_provenance"]["mode"] for entry in history] == [
                "direct_runtime",
                "delegated_relay",
            ]
        finally:
            await reloaded_session.close()

    asyncio.run(scenario())


def test_database_load_recovers_from_corrupted_json(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        path.write_text("{not-valid-json")

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("missing")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_recovers_from_invalid_persisted_record(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        path.write_text(
            json.dumps(
                {
                    "incidents": {
                        "nxs_bad": {
                            "nexus_incident_id": "nxs_bad",
                            "external_id": "inc_bad",
                            "title": "Broken incident",
                            "severity": "P9",
                            "status": "investigating",
                        }
                    }
                }
            )
        )

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("nxs_bad")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_recovers_from_wrong_root_shape(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        path.write_text("[]")

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("missing")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_recovers_from_non_mapping_incidents_value(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        path.write_text(json.dumps({"incidents": []}))

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("missing")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_keeps_valid_records_when_one_record_is_invalid(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.json"
        path.write_text(
            json.dumps(
                {
                    "incidents": {
                        "nxs_good": {
                            "nexus_incident_id": "nxs_good",
                            "external_id": "inc_good",
                            "title": "Healthy incident",
                            "severity": "P1",
                            "status": "investigating",
                        },
                        "nxs_bad": {
                            "nexus_incident_id": "nxs_bad",
                            "external_id": "inc_bad",
                            "title": "Broken incident",
                            "severity": "P9",
                            "status": "investigating",
                        },
                    }
                }
            )
        )

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            good = await session.incidents.get_incident("nxs_good")
            bad = await session.incidents.get_incident("nxs_bad")
            assert good is not None
            assert good.external_id == "inc_good"
            assert bad is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_recovers_when_path_is_a_directory(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents-dir"
        path.mkdir()

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("missing")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())
