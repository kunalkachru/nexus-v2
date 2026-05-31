import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server.audit import write_audit_log
from server.auth import AuthenticatedContext, require_auth, require_role
from server.auth import verify_webhook_signature
from server.config import AppConfig
from server.db import DatabaseSession, create_session_factory, get_db
from server.integrations.alerts import AlertNormalizer
from server.integrations.deployments import DeploymentLookupService
from server.integrations.models import (
    BatchImportRequest,
    GuardianDecisionRequest,
    IncomingIncidentWebhook,
    ManualIncidentReport,
    RawIncidentTextRequest,
    SlackIncidentCommand,
    StreamAnomalyReport,
)
from server.openai_keys import extract_request_openai_api_key
from server.rate_limit import RateLimiter
from server.services.incidents import IncidentService
from server.services.live_demo import build_demo_payload
from server.services.observability import ObservabilityService
from server.services.surface_payloads import build_platform_status, load_metrics_payload
from server.services.tenancy import TenancyService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = AppConfig()
    app.state.config = config
    app.state.db_session_factory = create_session_factory(config)
    app.state.rate_limiter = RateLimiter()
    app.state.tenancy_service = TenancyService()
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


def get_incident_service(
    session: DatabaseSession = Depends(get_db),
) -> IncidentService:
    deployment_lookup = DeploymentLookupService()
    return IncidentService(
        session=session,
        alert_normalizer=AlertNormalizer(),
        deployment_lookup=deployment_lookup,
        observability=ObservabilityService(deployment_lookup=deployment_lookup),
    )

@app.get("/")
async def root() -> FileResponse:
    return FileResponse("frontend/queue.html", media_type="text/html")


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    return FileResponse("frontend/queue.html", media_type="text/html")


@app.get("/queue")
async def queue() -> FileResponse:
    return FileResponse("frontend/queue.html", media_type="text/html")


@app.get("/incident")
async def incident() -> FileResponse:
    return FileResponse("frontend/incident.html", media_type="text/html")


@app.get("/inputs")
async def inputs() -> FileResponse:
    return FileResponse("frontend/inputs.html", media_type="text/html")


@app.get("/history")
async def history() -> FileResponse:
    return FileResponse("frontend/history.html", media_type="text/html")


@app.get("/replay")
async def replay() -> FileResponse:
    return FileResponse("frontend/replay.html", media_type="text/html")


@app.get("/training")
async def training() -> FileResponse:
    return FileResponse("frontend/training.html", media_type="text/html")


@app.get("/settings")
async def settings() -> FileResponse:
    return FileResponse("frontend/settings.html", media_type="text/html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/incidents/queue")
async def get_incident_queue(
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_queue")
    response = await service.list_queue_items(tenant_id=auth.tenant_id)
    await write_audit_log(
        "incident.queue.read",
        auth.tenant_id,
        {"user_id": auth.user_id, "items": len(response.items)},
    )
    return response.model_dump(mode="json")


@app.post("/api/v1/incidents/slack-command", status_code=202)
async def receive_slack_command(
    request: Request,
    payload: SlackIncidentCommand,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="slack_command")
    require_role(auth, "operator", "incident_manager")
    response = await service.create_incident_from_slack_command(payload, tenant_id=auth.tenant_id)
    await write_audit_log("incident.slack_command.accepted", auth.tenant_id, response)
    return response


@app.post("/api/v1/incidents/stream-anomaly", status_code=202)
async def receive_stream_anomaly(
    request: Request,
    payload: StreamAnomalyReport,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="stream_anomaly")
    require_role(auth, "operator", "incident_manager")
    response = await service.create_incident_from_stream_anomaly(payload, tenant_id=auth.tenant_id)
    await write_audit_log("incident.stream_anomaly.accepted", auth.tenant_id, response)
    return response


@app.get("/api/v1/incidents/history")
async def get_incident_history(
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_history")
    response = {"items": await service.list_history_archive(tenant_id=auth.tenant_id)}
    await write_audit_log(
        "incident.history.read",
        auth.tenant_id,
        {"user_id": auth.user_id, "items": len(response["items"])},
    )
    return response


@app.get("/api/v1/replay/scenarios")
async def get_replay_scenarios(
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="replay_scenarios")
    response = {"items": await service.list_replay_scenarios()}
    await write_audit_log(
        "replay.scenarios.read",
        auth.tenant_id,
        {"user_id": auth.user_id, "items": len(response["items"])},
    )
    return response


@app.post("/api/v1/replay/scenarios/{scenario_id}/launch", status_code=202)
async def launch_replay_scenario(
    scenario_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="replay_launch")
    require_role(auth, "operator", "incident_manager")
    response = await service.launch_replay_scenario(scenario_id, tenant_id=auth.tenant_id)
    await write_audit_log(
        "replay.scenario.launched",
        auth.tenant_id,
        {"user_id": auth.user_id, **response},
    )
    return response


@app.get("/api/v1/training/summary")
async def get_training_summary(
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="training_summary")
    payload = await asyncio.to_thread(load_metrics_payload)
    response = await service.build_training_summary(payload, tenant_id=auth.tenant_id)
    await write_audit_log(
        "training.summary.read",
        auth.tenant_id,
        {"user_id": auth.user_id, "episodes": len(response["episode_records"])},
    )
    return response


@app.get("/api/v1/platform/status")
async def get_platform_status(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="platform_status")
    payload = await asyncio.to_thread(load_metrics_payload)
    response = build_platform_status(payload)
    response["contract_surface"] = [
        "/webhooks/incident",
        "/api/v1/incidents/raw-text",
        "/api/v1/incidents/manual-report",
        "/api/v1/incidents/slack-command",
        "/api/v1/incidents/stream-anomaly",
        "/api/v1/incidents/batch-import",
        "/api/v1/incidents/{incident_id}/context",
        "/api/v1/incidents/{incident_id}/status",
        "/api/v1/audit-logs/{incident_id}",
        "/api/v1/incidents/{incident_id}/guardian-review",
        "/api/v1/incidents/{incident_id}/execute",
    ]
    await write_audit_log(
        "platform.status.read",
        auth.tenant_id,
        {"user_id": auth.user_id},
    )
    return response


@app.post("/api/v1/incidents/manual-report", status_code=202)
async def receive_manual_report(
    request: Request,
    payload: ManualIncidentReport,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="manual_report")
    require_role(auth, "operator", "incident_manager")
    response = await service.create_incident_from_manual_report(payload, tenant_id=auth.tenant_id)
    await write_audit_log("incident.manual_report.accepted", auth.tenant_id, response)
    return response


@app.post("/api/v1/incidents/raw-text", status_code=202)
async def receive_raw_text(
    request: Request,
    payload: RawIncidentTextRequest,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="raw_text")
    require_role(auth, "operator", "incident_manager")
    response = await service.create_incident_from_raw_text(payload, tenant_id=auth.tenant_id)
    await write_audit_log("incident.raw_text.accepted", auth.tenant_id, response)
    return response


@app.post("/api/v1/incidents/batch-import", status_code=202)
async def receive_batch_import(
    request: Request,
    payload: BatchImportRequest,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="batch_import")
    require_role(auth, "operator", "incident_manager")
    response = await service.create_incident_from_batch_import(payload, tenant_id=auth.tenant_id)
    await write_audit_log("incident.batch_import.accepted", auth.tenant_id, response)
    return response


@app.get("/api/v1/incidents/{nexus_incident_id}/status")
async def get_incident_status_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_status_v1")
    response = await service.get_incident_status_v1(nexus_incident_id, tenant_id=auth.tenant_id)
    await write_audit_log(
        "incident.status_v1.read",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id},
    )
    return response


@app.get("/api/v1/incidents/{nexus_incident_id}/context")
async def get_incident_context_v1(
    nexus_incident_id: str,
    request: Request,
    live_reasoning: bool | None = Query(default=None),
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_context_v1")
    openai_api_key = extract_request_openai_api_key(request)
    response = await service.get_incident_context_v1(
        nexus_incident_id,
        tenant_id=auth.tenant_id,
        live_reasoning=live_reasoning,
        openai_api_key=openai_api_key,
    )
    await write_audit_log(
        "incident.context_v1.read",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id},
    )
    return response


@app.get("/api/v1/audit-logs/{nexus_incident_id}")
async def get_audit_logs_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> list[dict[str, object]]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="audit_logs_v1")
    logs = await service.get_audit_logs(nexus_incident_id)
    await write_audit_log(
        "incident.audit_logs_v1.read",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id, "items": len(logs)},
    )
    return logs


@app.post("/api/v1/incidents/{nexus_incident_id}/execute")
async def execute_incident_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_execute")
    require_role(auth, "operator", "guardian")
    response = await service.execute_incident(nexus_incident_id, tenant_id=auth.tenant_id)
    await write_audit_log(
        "incident.execute_v1.requested",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id, **response},
    )
    return response


@app.post("/api/v1/incidents/{nexus_incident_id}/guardian-review")
async def guardian_review_incident_v1(
    nexus_incident_id: str,
    request: Request,
    payload: GuardianDecisionRequest,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_execute")
    require_role(auth, "operator", "guardian")
    response = await service.record_guardian_decision(nexus_incident_id, payload=payload, tenant_id=auth.tenant_id)
    await write_audit_log(
        "incident.guardian_review_v1.requested",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id, **response},
    )
    return response


@app.post("/webhooks/incident", status_code=202)
async def receive_incident_webhook(
    request: Request,
    payload: IncomingIncidentWebhook,
    service: IncidentService = Depends(get_incident_service),
) -> dict[str, object]:
    await verify_webhook_signature(request)
    tenant_id = request.app.state.tenancy_service.resolve_webhook_tenant(request)
    response = await service.create_incident_from_webhook(payload, tenant_id=tenant_id)
    await write_audit_log("incident.webhook.accepted", tenant_id, response)
    return response


@app.get("/incidents/{nexus_incident_id}")
async def get_incident_status(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_status")
    response = await service.get_incident_status(nexus_incident_id, tenant_id=auth.tenant_id)
    await write_audit_log(
        "incident.status.read",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id},
    )
    return response


@app.get("/api/metrics")
async def get_metrics():
    try:
        return await asyncio.to_thread(load_metrics_payload)
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "metrics payload not found"})
    except json.JSONDecodeError:
        logger.exception("metrics payload is invalid json")
        return JSONResponse(status_code=500, content={"error": "metrics payload is invalid"})


@app.get("/run-incident")
async def run_incident(
    request: Request,
    incident_id: str = "INC001",
    live_reasoning: bool | None = Query(default=None),
):
    try:
        return await build_demo_payload(
            incident_id,
            live_reasoning_override=live_reasoning,
            openai_api_key=extract_request_openai_api_key(request),
        )
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except KeyError:
        logger.exception("incident payload is incomplete for %s", incident_id)
        return JSONResponse(status_code=500, content={"error": "incident payload is incomplete"})
