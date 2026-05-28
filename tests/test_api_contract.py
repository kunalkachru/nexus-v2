import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from server.app import app
from server.config import AppConfig
from server.db import create_session_factory
from server.db import DatabaseSession, get_db


def test_app_startup_wires_persistence_factory() -> None:
    with TestClient(app):
        assert hasattr(app.state, "config")
        assert hasattr(app.state, "db_session_factory")
        session = app.state.db_session_factory()
        assert isinstance(session, DatabaseSession)
        asyncio.run(session.close())


def test_get_db_uses_app_scoped_factory(tmp_path: Path) -> None:
    async def scenario() -> None:
        custom_app = FastAPI()
        custom_app.state.config = AppConfig(database_path=tmp_path / "app-scoped-incidents.json")
        custom_app.state.db_session_factory = create_session_factory(custom_app.state.config)
        scope = {"type": "http", "app": custom_app, "headers": [], "query_string": b""}
        generator = get_db(Request(scope))
        session = await anext(generator)

        assert isinstance(session, DatabaseSession)
        assert hasattr(session, "incidents")

        incident = await session.incidents.create_incident(
            external_id="inc_xyz",
            title="Payment API timeout",
            severity="P1",
        )
        await generator.aclose()

        assert custom_app.state.config.database_path.exists()

        verification_session = custom_app.state.db_session_factory()
        try:
            loaded = await verification_session.incidents.get_incident(incident.nexus_incident_id)
            assert loaded is not None
            assert loaded.external_id == "inc_xyz"
        finally:
            await verification_session.close()

    asyncio.run(scenario())
