import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server.audit import write_audit_log
from server.auth import AuthenticatedContext, require_auth
from server.config import AppConfig
from server.db import DatabaseSession, create_session_factory, get_db
from server.incident_payloads import get_incident_definition, get_incident_details, list_supported_incident_ids
from server.integrations.alerts import AlertNormalizer
from server.integrations.deployments import DeploymentLookupService
from server.integrations.models import IncomingIncidentWebhook
from server.rate_limit import RateLimiter
from server.services.incidents import IncidentService
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

app.mount("/static", StaticFiles(directory="frontend"), name="static")


def get_incident_service(
    session: DatabaseSession = Depends(get_db),
) -> IncidentService:
    return IncidentService(
        session=session,
        alert_normalizer=AlertNormalizer(),
        deployment_lookup=DeploymentLookupService(),
    )


def _build_incident_response(incident_id: str) -> dict[str, object]:
    incident = get_incident_definition(incident_id)
    details = get_incident_details(incident_id)

    return {
        "incident": {
            "id": incident.id,
            "name": incident.name,
            "severity": "P1" if incident.severity == "P1" else "P2" if incident.severity == "P2" else "P3",
            "summary": details["summary"],
            "detected_at": details["detected_at"],
            "duration_minutes": details["duration_minutes"],
            "related_services": details["related_services"],
            "recent_deployments": details["recent_deployments"],
            "similar_past_incidents": details["similar_past_incidents"],
        },
        "observability": {
            "metrics": details["metrics"],
            "recent_logs": details["recent_logs"],
            "alert_timeline": details["alert_timeline"],
            "recommended_runbooks": details["recommended_runbooks"],
        },
        "classification": {
            "incident_id": incident.id,
            "incident_name": incident.name,
            "severity": "P1" if incident.severity == "P1" else "P2" if incident.severity == "P2" else "P3",
            "confidence": details["sentinel"]["confidence"],
            "confidence_breakdown": details["sentinel"]["confidence_breakdown"],
            "evidence": details["sentinel"]["evidence"],
            "reasoning": details["sentinel"]["reasoning"],
        },
        "diagnosis": {
            "root_cause": incident.root_cause,
            "confidence": details["prism"]["confidence"],
            "supporting_logs": details["prism"]["log_snippets"],
            "correlation_analysis": details["prism"]["correlation_analysis"],
            "reasoning": details["prism"]["reasoning"],
        },
        "runbook": {
            "language": "bash",
            "summary": details["forge"]["recommended_runbook"],
            "selection_logic": details["forge"]["selection_logic"],
            "candidate_fixes": details["forge"]["candidate_fixes"],
            "recommended_runbook": details["forge"]["recommended_runbook"],
            "reasoning": details["forge"]["reasoning"],
            "cost_usd": 0.12,
        },
        "guardian": {
            "decision": details["guardian"]["decision"],
            "confidence": details["guardian"]["confidence"],
            "safety_checks": details["guardian"]["safety_checks"],
            "policy_violations": details["guardian"]["policy_violations"],
            "reasoning": details["guardian"]["reasoning"],
        },
        "execution_result": "executed",
        "reward": 0.87,
        "execution_time_ms": 8.7,
        "supported_incidents": list_supported_incident_ids(),
    }


@app.get("/")
async def root() -> FileResponse:
    return FileResponse("frontend/dashboard.html", media_type="text/html")


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    return FileResponse("frontend/dashboard.html", media_type="text/html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/incident", status_code=202)
async def receive_incident_webhook(
    request: Request,
    payload: IncomingIncidentWebhook,
    service: IncidentService = Depends(get_incident_service),
) -> dict[str, object]:
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
        return await asyncio.to_thread(_load_metrics_payload)
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "metrics payload not found"})
    except json.JSONDecodeError:
        logger.exception("metrics payload is invalid json")
        return JSONResponse(status_code=500, content={"error": "metrics payload is invalid"})


@app.get("/run-incident")
async def run_incident(incident_id: str = "INC001"):
    try:
        return _build_incident_response(incident_id)
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except KeyError:
        logger.exception("incident payload is incomplete for %s", incident_id)
        return JSONResponse(status_code=500, content={"error": "incident payload is incomplete"})


def _load_metrics_payload() -> dict[str, object]:
    with open("frontend/metrics.json") as file_handle:
        return json.load(file_handle)
