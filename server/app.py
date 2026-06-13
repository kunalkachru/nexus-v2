import asyncio
import json
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server.audit import write_audit_log
from server.auth import AuthenticatedContext, require_auth, require_role, require_runtime_host_auth
from server.auth import verify_webhook_signature
from server.artifacts import record_execution_event, _load_artifacts
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
from server.models import RuntimeHostReplayRequest
from server.openai_keys import extract_request_openai_api_key
from server.rate_limit import RateLimiter
from server.services.incidents import IncidentService
from server.services.live_demo import build_demo_payload
from server.services.observability import ObservabilityService
from server.services.replica_runtime import execute_runtime_host_replay, runtime_host_supported_packs, build_runtime_host_relay_status, probe_runtime_host
from server.services.surface_payloads import build_platform_status, load_metrics_payload
from server.services.tenancy import TenancyService

logger = logging.getLogger(__name__)


class RuntimeExecutionState:
    def __init__(self):
        self.current_state = "idle"
        self.current_pack_id = None
        self.current_incident_id = None
        self.started_at = None
        self.max_concurrent_replays = 1
        self.current_concurrency = 0
        self.guardrails = {
            "max_replay_duration_ms": 30000,
            "max_concurrent_replays": 1,
            "pack_specific_limits": {
                "checkout-python-fastapi-auth-redis-v1": {"max_duration_ms": 25000, "max_retries": 3},
                "checkout-python-fastapi-postgres-v1": {"max_duration_ms": 30000, "max_retries": 3},
            },
            "replay_eligibility_checks": ["pack_present", "docker_available", "relay_capable"],
        }

    def start_execution(self, pack_id: str, incident_id: str):
        self.current_state = "running"
        self.current_pack_id = pack_id
        self.current_incident_id = incident_id
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.current_concurrency = 1

    def finish_execution(self, status: str = "completed"):
        if self.current_state == "running":
            duration_ms = None
            if self.started_at:
                start = datetime.fromisoformat(self.started_at)
                duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

            event = {
                "incident_id": self.current_incident_id,
                "pack_id": self.current_pack_id,
                "status": status,
                "started_at": self.started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": duration_ms,
            }
            asyncio.create_task(record_execution_event(event))

            self.current_state = "idle"
            self.current_pack_id = None
            self.current_incident_id = None
            self.started_at = None
            self.current_concurrency = 0

    def to_dict(self):
        artifacts = _load_artifacts()
        execution_events = artifacts.get("execution_events", [])
        recent_events = execution_events[-20:] if execution_events else []

        return {
            "current_state": self.current_state,
            "current_pack_id": self.current_pack_id,
            "current_incident_id": self.current_incident_id,
            "started_at": self.started_at,
            "current_concurrency": self.current_concurrency,
            "max_concurrent_replays": self.max_concurrent_replays,
            "execution_history": recent_events,
            "guardrails": self.guardrails,
        }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = AppConfig()
    app.state.config = config
    app.state.db_session_factory = create_session_factory(config)
    app.state.rate_limiter = RateLimiter()
    app.state.tenancy_service = TenancyService()
    app.state.runtime_execution_state = RuntimeExecutionState()
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
    payload = await asyncio.to_thread(load_metrics_payload, request.app.state.config)
    response = build_platform_status(payload, config=request.app.state.config)
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
        "/api/v1/incidents/{incident_id}/replica-replay",
        "/api/v1/internal/runtime-host/replica-replay",
    ]
    await write_audit_log(
        "platform.status.read",
        auth.tenant_id,
        {"user_id": auth.user_id},
    )
    return response


@app.get("/api/v1/runtime/capabilities")
async def get_runtime_capabilities(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="platform_status")
    config = request.app.state.config
    supported_packs = runtime_host_supported_packs()
    relay_status = build_runtime_host_relay_status(config)

    return {
        "supported_packs": supported_packs,
        "pack_count": len(supported_packs),
        "runtime_host_relay": relay_status,
        "coverage_summary": {
            "timeout_retry_amplification": any("timeout_retry_amplification" in p.get("incident_classes", []) for p in supported_packs),
            "db_pool_exhaustion": any("db_pool_exhaustion" in p.get("incident_classes", []) for p in supported_packs),
        },
    }


@app.get("/api/v1/runtime/execution-state")
async def get_runtime_execution_state(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="platform_status")
    execution_state = getattr(request.app.state, "runtime_execution_state", RuntimeExecutionState())
    return execution_state.to_dict()


@app.post("/api/v1/internal/runtime-host/replica-replay")
async def runtime_host_replica_replay(
    payload: RuntimeHostReplayRequest,
    _: None = Depends(require_runtime_host_auth),
) -> dict[str, object]:
    response = await asyncio.to_thread(execute_runtime_host_replay, payload)
    return response.model_dump(mode="json")


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


@app.get("/api/v1/incidents/{nexus_incident_id}/handoff-export")
async def get_engineering_handoff_v1(
    nexus_incident_id: str,
    request: Request,
    format: str = "markdown",
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    if format not in ["markdown", "github", "jira", "slack"]:
        format = "markdown"
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_handoff_export")
    handoff = await service.build_engineering_handoff(
        nexus_incident_id,
        export_format=format,
        tenant_id=auth.tenant_id,
    )
    await write_audit_log(
        "incident.handoff_export.generated",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "format": format, "user_id": auth.user_id},
    )
    return handoff


@app.get("/api/v1/incidents/{nexus_incident_id}/governance-packet")
async def get_governance_packet_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_governance_export")
    packet = await service.build_governance_packet(
        nexus_incident_id,
        tenant_id=auth.tenant_id,
    )
    await write_audit_log(
        "incident.governance_packet.exported",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id},
    )
    return packet


@app.post("/api/v1/incidents/{nexus_incident_id}/handoff-send")
async def send_engineering_handoff_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_handoff_send")
    body = await request.json()
    target = body.get("target", "github")

    response = await service.send_engineering_handoff(
        nexus_incident_id,
        target=target,
        tenant_id=auth.tenant_id,
    )

    await write_audit_log(
        "incident.handoff_send.attempted",
        auth.tenant_id,
        {
            "nexus_incident_id": nexus_incident_id,
            "target": target,
            "status": response.get("status"),
            "user_id": auth.user_id,
        },
    )
    return response


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


@app.post("/api/v1/incidents/{nexus_incident_id}/replica-replay")
async def replay_incident_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_replica_replay")
    require_role(auth, "operator", "guardian", "incident_manager")

    execution_state = getattr(request.app.state, "runtime_execution_state", RuntimeExecutionState())
    context = await service.get_incident_context_v1(
        nexus_incident_id,
        tenant_id=auth.tenant_id,
        live_reasoning=False,
        openai_api_key=None,
    )
    replica_summary = context.get("replica_summary", {})
    pack_id = str(replica_summary.get("environment_pack_id", "unknown"))

    execution_state.start_execution(pack_id, nexus_incident_id)
    try:
        response = await service.trigger_replica_replay(nexus_incident_id, tenant_id=auth.tenant_id)
        status = response.get("status", "unknown")
        execution_state.finish_execution("completed" if status in {"replay_executed", "relay_executed"} else "failed")
    except Exception as e:
        execution_state.finish_execution("failed")
        raise

    await write_audit_log(
        "incident.replica_replay_v1.requested",
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
        config = getattr(app.state, "config", AppConfig())
        return await asyncio.to_thread(load_metrics_payload, config)
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
