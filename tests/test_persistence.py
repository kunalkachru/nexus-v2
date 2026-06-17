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
        path = tmp_path / "incidents.db"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        incident_id = None
        try:
            incident = await session.incidents.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
            )
            incident_id = incident.nexus_incident_id
            assert incident.status == "investigating"
        finally:
            await session.close()

        reloaded_session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await reloaded_session.incidents.get_incident(incident_id)
            assert loaded is not None
            assert loaded.status == "investigating"
            assert loaded.external_id == "inc_xyz"
        finally:
            await reloaded_session.close()

    asyncio.run(scenario())


def test_incident_repository_does_not_mutate_store_if_flush_fails(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.db"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        try:
            incident = await session.incidents.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
            )
            assert incident is not None
            assert incident.status == "investigating"
        finally:
            await session.close()

    asyncio.run(scenario())


def test_incident_repository_persists_normalized_evidence_updates(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.db"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        incident_id = None
        try:
            incident = await session.incidents.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
                normalized_evidence={"signature": "timeout"},
            )
            incident_id = incident.nexus_incident_id
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
            assert updated.normalized_evidence["latest_replay"]["status"] == "relay_executed"
        finally:
            await session.close()

        reloaded_session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await reloaded_session.incidents.get_incident(incident_id)
            assert loaded is not None
            assert loaded.normalized_evidence["latest_replay"]["runtime_provenance"]["mode"] == "delegated_relay"
        finally:
            await reloaded_session.close()

    asyncio.run(scenario())


def test_incident_repository_appends_bounded_replay_history(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.db"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        incident_id = None
        try:
            incident = await session.incidents.create_incident(
                external_id="inc_xyz",
                title="Payment API timeout",
                severity="P1",
                normalized_evidence={"signature": "timeout"},
            )
            incident_id = incident.nexus_incident_id

            await session.incidents.append_incident_replay_evidence(
                incident_id,
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
                incident_id,
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
                incident_id,
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
        finally:
            await session.close()

        reloaded_session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await reloaded_session.incidents.get_incident(incident_id)
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
        path = tmp_path / "incidents.db"
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
        path = tmp_path / "incidents.db"

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("nxs_bad")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_recovers_from_wrong_root_shape(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.db"

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("missing")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_recovers_from_non_mapping_incidents_value(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.db"

        session = create_session_factory(AppConfig(database_path=path))()
        try:
            loaded = await session.incidents.get_incident("missing")
            assert loaded is None
        finally:
            await session.close()

    asyncio.run(scenario())


def test_database_load_keeps_valid_records_when_one_record_is_invalid(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "incidents.db"
        session_factory = create_session_factory(AppConfig(database_path=path))
        session = session_factory()
        try:
            good = await session.incidents.create_incident(
                external_id="inc_good",
                title="Healthy incident",
                severity="P1",
            )
            assert good is not None
            assert good.external_id == "inc_good"
        finally:
            await session.close()

        reloaded_session = session_factory()
        try:
            loaded = await reloaded_session.incidents.get_incident(good.nexus_incident_id)
            assert loaded is not None
            assert loaded.external_id == "inc_good"
        finally:
            await reloaded_session.close()

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
