import asyncio
import json
import os
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Coroutine
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def _safe_background_task(coro: Coroutine[Any, Any, Any]) -> None:
    """Safely execute a background task with error logging."""
    try:
        await coro
    except Exception as e:
        logger.exception(f"Background task failed: {e}")


def _create_background_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[None]:
    """Create a background task with automatic error handling."""
    return asyncio.create_task(_safe_background_task(coro))


from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server.audit import write_audit_log
from server.auth import AuthenticatedContext, require_auth, require_role, require_runtime_host_auth, check_governance_capability
from server.auth import verify_webhook_signature, get_user_capabilities, ROLE_MATRIX
from server.artifacts import record_execution_event, _load_artifacts
from server.artifacts import get_artifact_summary
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
from server.services.deployment_readiness import DeploymentReadiness
from server.services.governance import GovernanceService
from server.services.incidents import IncidentService
from server.services.enterprise_runtime import build_pilot_safe_subsystem, summarize_pilot_surface
from server.services.health_service import HealthService
from server.services.live_demo import build_demo_payload
from server.services.metrics_service import PilotMetricsService
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
            _create_background_task(record_execution_event(event))

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
    db_session_factory, database = create_session_factory(config)
    app.state.db_session_factory = db_session_factory
    app.state.database = database
    app.state.rate_limiter = RateLimiter(database=database)
    app.state.tenancy_service = TenancyService()
    app.state.runtime_execution_state = RuntimeExecutionState()
    yield


app = FastAPI(
    title="NEXUS Incident Investigation API",
    description="AI-powered incident triage and investigation with human governance gate",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS from environment
_allowed_origins = os.environ.get("NEXUS_ALLOWED_ORIGINS")
if _allowed_origins:
    allowed_origins_list = [item.strip() for item in _allowed_origins.split(",") if item.strip()]
else:
    allowed_origins_list = [
        "https://nexus-triage.duckdns.org",
        "https://nexus-uny5.onrender.com",
        "http://localhost:7860",
        "http://127.0.0.1:7860",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-User-ID", "X-Tenant-ID", "X-Roles", "X-Signature", "X-Runtime-Host-Token"],
)


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    max_size = int(os.environ.get("NEXUS_MAX_REQUEST_SIZE_BYTES", 1048576))
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body too large. Maximum size is {max_size} bytes."},
        )
    return await call_next(request)


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

@app.get("/", tags=["UI"], summary="Dashboard root")
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


@app.get("/api/v1/observability/health", tags=["Observability"], summary="Check platform health")
async def get_product_health(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="health_check")

    try:
        from server.services.runtime_queue import RuntimeQueueManager

        execution_state = getattr(request.app.state, "runtime_execution_state", RuntimeExecutionState())
        service = get_incident_service(
            session=request.app.state.db_session_factory(),
        )

        queue = await service.list_queue_items(tenant_id=auth.tenant_id)
        queue_items = queue.items if hasattr(queue, "items") else queue.get("items", [])

        health_service = HealthService()
        queue_subsystem = health_service.check_queue_health(queue_items)
        queue_health = queue_subsystem.status
        queue_guidance = queue_subsystem.guidance
        queue_next_checks = queue_subsystem.next_checks

        execution_health = "idle" if execution_state.current_state == "idle" else "running"
        runtime_recovery = RuntimeQueueManager.get_runtime_recovery_posture()
        deployment_readiness = DeploymentReadiness.get_deployment_readiness()

        # Memory service health (knowledge base availability)
        memory_subsystem = health_service.check_memory_health(service)
        memory_health = memory_subsystem.status
        memory_guidance = memory_subsystem.guidance
        memory_next_checks = memory_subsystem.next_checks

        # Delivery service health (downstream integrations)
        delivery_subsystem = health_service.check_delivery_health(deployment_readiness)
        delivery_health = delivery_subsystem.status
        delivery_guidance = delivery_subsystem.guidance
        delivery_next_checks = delivery_subsystem.next_checks

        # Replay health with guidance
        replay_subsystem = health_service.check_replay_health(execution_state, deployment_readiness)
        replay_health = replay_subsystem.status
        replay_guidance = replay_subsystem.guidance
        replay_next_checks = replay_subsystem.next_checks

        runtime_queue_subsystem = health_service.check_runtime_queue_health(runtime_recovery)
        runtime_queue_status = runtime_queue_subsystem.status
        runtime_queue_guidance = runtime_queue_subsystem.guidance
        runtime_queue_next_checks = runtime_queue_subsystem.next_checks

        pilot_subsystems = [
            build_pilot_safe_subsystem(
                service="replay",
                raw_status=replay_health,
                healthy_states=("idle", "running", "healthy"),
                unavailable_states=("unavailable", "unhealthy", "failed"),
                guidance=replay_guidance,
                next_checks=replay_next_checks,
            ),
            build_pilot_safe_subsystem(
                service="delivery",
                raw_status=delivery_health,
                healthy_states=("healthy",),
                partial_states=("degraded",),
                unavailable_states=("unhealthy", "unavailable"),
                guidance=delivery_guidance,
                next_checks=delivery_next_checks,
            ),
            build_pilot_safe_subsystem(
                service="runtime queue",
                raw_status=runtime_queue_status,
                healthy_states=("healthy",),
                partial_states=("recovering", "degraded"),
                unavailable_states=("unavailable", "failed", "abandoned"),
                guidance=runtime_queue_guidance,
                next_checks=runtime_queue_next_checks,
            ),
            build_pilot_safe_subsystem(
                service="memory",
                raw_status=memory_health,
                healthy_states=("available", "healthy"),
                unavailable_states=("unavailable", "missing"),
                guidance=memory_guidance,
                next_checks=memory_next_checks,
            ),
        ]
        pilot_surface = summarize_pilot_surface(pilot_subsystems)

        degraded_services = []
        if queue_health != "healthy":
            degraded_services.append(
                {
                    "service": "queue",
                    "status": queue_health,
                    "posture": "partial" if queue_health == "degraded" else "unavailable",
                    "guidance": queue_guidance,
                    "next_checks": queue_next_checks,
                    "summary": "Incident queue is outside the normal operating range.",
                }
            )
        if memory_health != "available":
            degraded_services.append(
                {
                    "service": "memory",
                    "status": memory_health,
                    "posture": "unavailable",
                    "guidance": memory_guidance,
                    "next_checks": memory_next_checks,
                    "summary": "Historical memory is unavailable, so triage should stay inference-first.",
                }
            )
        if delivery_health != "healthy":
            degraded_services.append(
                {
                    "service": "delivery",
                    "status": delivery_health,
                    "posture": "partial" if delivery_health == "degraded" else "unavailable",
                    "guidance": delivery_guidance,
                    "next_checks": delivery_next_checks,
                    "summary": "Downstream handoff destinations need operator review before promising delivery completion.",
                }
            )
        if replay_health not in ["idle", "running"]:
            degraded_services.append(
                {
                    "service": "replay",
                    "status": replay_health,
                    "posture": "unavailable",
                    "guidance": replay_guidance,
                    "next_checks": replay_next_checks,
                    "summary": "Replay is not currently available for runtime-backed validation.",
                }
            )

        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "app": {
                "status": "healthy",
                "response_time_ms": 0,
            },
            "replay": {
                "status": replay_health,
                "guidance": replay_guidance,
                "next_checks": replay_next_checks,
                "current_execution": execution_state.to_dict(),
                "recent_executions": execution_state.to_dict().get("execution_history", [])[:5],
            },
            "queue": {
                "status": queue_health,
                "guidance": queue_guidance,
                "next_checks": queue_next_checks,
                "items_pending": len(queue_items),
                "threshold_warning": 100,
                "threshold_critical": 500,
            },
            "memory": {
                "status": memory_health,
                "guidance": memory_guidance,
                "next_checks": memory_next_checks,
                "description": "Knowledge base of historical incidents and runbooks",
            },
            "delivery": {
                "status": delivery_health,
                "guidance": delivery_guidance,
                "next_checks": delivery_next_checks,
                "github": "github" not in (deployment_readiness.get("degraded_features") or []),
                "slack": "slack" not in (deployment_readiness.get("degraded_features") or []),
            },
            "runtime_queue": {
                "recovery_status": runtime_recovery.get("recovery_status"),
                "active_jobs": runtime_recovery.get("active_jobs"),
                "recovered_jobs": runtime_recovery.get("recovered_jobs"),
                "failed_jobs": runtime_recovery.get("failed_jobs"),
                "total_jobs": runtime_recovery.get("total_jobs"),
                "message": runtime_recovery.get("message"),
                "guidance": runtime_queue_guidance,
                "next_checks": runtime_queue_next_checks,
            },
            "deployment_readiness": {
                "readiness": deployment_readiness.get("readiness"),
                "fully_available": deployment_readiness.get("fully_available"),
                "partially_available": deployment_readiness.get("partially_available"),
                "docker": deployment_readiness.get("docker"),
                "runtime_host_relay": {k: v for k, v in deployment_readiness.get("runtime_host_relay", {}).items() if k != "base_url"},
                "pack_root": {k: v for k, v in deployment_readiness.get("pack_root", {}).items() if k != "path"},
                "degraded_features": deployment_readiness.get("degraded_features"),
                "message": deployment_readiness.get("message"),
            },
            "downstream_integrations": {
                "status": delivery_health,
                "github": {"available": "github" not in (deployment_readiness.get("degraded_features") or []), "last_delivery": None},
                "slack": {"available": "slack" not in (deployment_readiness.get("degraded_features") or []), "last_delivery": None},
            },
            "pilot_surface": pilot_surface,
            "degraded_services": degraded_services,
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_message": str(e),
            "app": {"status": "unhealthy"},
            "replay": {"status": "unknown"},
            "queue": {"status": "unknown"},
            "downstream_integrations": {"status": "unknown"},
            "degraded_services": [{"service": "platform", "status": "error", "guidance": ["An error occurred while checking platform health. Check server logs."]}],
        }


@app.get("/api/v1/incidents/queue", tags=["Incidents"], summary="List incident queue")
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
    check_governance_capability(auth, "trigger_replay")
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


@app.get("/api/v1/tenant/bootstrap-status")
async def get_tenant_bootstrap_status(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="tenant_bootstrap")
    tenancy_service = request.app.state.tenancy_service
    status = tenancy_service.get_bootstrap_status(auth.tenant_id)
    await write_audit_log(
        "tenant.bootstrap_status.read",
        auth.tenant_id,
        {"user_id": auth.user_id},
    )
    return status


@app.get("/api/v1/tenant/bootstrap-config")
async def get_tenant_bootstrap_config(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="tenant_bootstrap")
    require_role(auth, "admin")
    tenancy_service = request.app.state.tenancy_service
    config = tenancy_service.get_bootstrap_config(auth.tenant_id)
    await write_audit_log(
        "tenant.bootstrap_config.read",
        auth.tenant_id,
        {"user_id": auth.user_id},
    )
    return config


@app.get("/api/v1/tenant/pilot-scorecard", tags=["Tenant"], summary="Get pilot program scorecard")
async def get_pilot_scorecard(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    from server.services.enterprise_runtime import build_pilot_scorecard

    await request.app.state.rate_limiter.check(auth=auth, route_key="tenant_bootstrap")

    metrics_service = PilotMetricsService()
    metrics = await metrics_service.compute_pilot_metrics(auth.tenant_id, request.app.state.database)

    scorecard = build_pilot_scorecard(
        incidents_handled=metrics["incidents_handled"],
        incidents_runtime_backed=metrics["incidents_runtime_backed"],
        incidents_inferred=metrics["incidents_inferred"],
        total_triage_time_saved_minutes=metrics["total_triage_time_saved_minutes"],
        handoff_completion_count=metrics["handoff_completion_count"],
        repeat_incident_reuse_count=0,
        tenant_id=auth.tenant_id,
    )
    scorecard["computed_at"] = metrics["computed_at"]

    await write_audit_log(
        "tenant.pilot_scorecard.read",
        auth.tenant_id,
        {"user_id": auth.user_id},
    )
    return scorecard


@app.get("/api/v1/tenant/weekly-review-package")
async def get_weekly_review_package(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    from server.services.enterprise_runtime import build_pilot_scorecard, build_weekly_pilot_review_package

    await request.app.state.rate_limiter.check(auth=auth, route_key="tenant_bootstrap")

    metrics_service = PilotMetricsService()
    metrics = await metrics_service.compute_pilot_metrics(auth.tenant_id, request.app.state.database)

    scorecard = build_pilot_scorecard(
        incidents_handled=metrics["incidents_handled"],
        incidents_runtime_backed=metrics["incidents_runtime_backed"],
        incidents_inferred=metrics["incidents_inferred"],
        total_triage_time_saved_minutes=metrics["total_triage_time_saved_minutes"],
        handoff_completion_count=metrics["handoff_completion_count"],
        repeat_incident_reuse_count=0,
        tenant_id=auth.tenant_id,
    )
    scorecard["computed_at"] = metrics["computed_at"]

    packet = build_weekly_pilot_review_package(
        tenant_id=auth.tenant_id,
        scorecard=scorecard,
        artifact_summary=get_artifact_summary(),
    )
    await write_audit_log(
        "tenant.weekly_review_package.read",
        auth.tenant_id,
        {"user_id": auth.user_id},
    )
    return packet


@app.get("/api/v1/tenant/pilot-closeout-package")
async def get_pilot_closeout_package(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    from server.services.enterprise_runtime import build_pilot_closeout_package, build_pilot_scorecard

    await request.app.state.rate_limiter.check(auth=auth, route_key="tenant_bootstrap")

    metrics_service = PilotMetricsService()
    metrics = await metrics_service.compute_pilot_metrics(auth.tenant_id, request.app.state.database)

    scorecard = build_pilot_scorecard(
        incidents_handled=metrics["incidents_handled"],
        incidents_runtime_backed=metrics["incidents_runtime_backed"],
        incidents_inferred=metrics["incidents_inferred"],
        total_triage_time_saved_minutes=metrics["total_triage_time_saved_minutes"],
        handoff_completion_count=metrics["handoff_completion_count"],
        repeat_incident_reuse_count=0,
        tenant_id=auth.tenant_id,
    )
    scorecard["computed_at"] = metrics["computed_at"]

    packet = build_pilot_closeout_package(
        tenant_id=auth.tenant_id,
        scorecard=scorecard,
        artifact_summary=get_artifact_summary(),
    )
    await write_audit_log(
        "tenant.pilot_closeout_package.read",
        auth.tenant_id,
        {"user_id": auth.user_id},
    )
    return packet


@app.put("/api/v1/tenant/bootstrap-config")
async def update_tenant_bootstrap_config(
    request: Request,
    payload: dict[str, object],
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="tenant_bootstrap")
    require_role(auth, "admin")
    tenancy_service = request.app.state.tenancy_service
    updated = tenancy_service.update_bootstrap_config(auth.tenant_id, payload)
    await write_audit_log(
        "tenant.bootstrap_config.updated",
        auth.tenant_id,
        {"user_id": auth.user_id, "updates": list(payload.keys())},
    )
    return updated


@app.get("/api/v1/auth/user-context")
async def get_user_context(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="user_context")
    capabilities = get_user_capabilities(auth.roles)
    role_descriptions = []
    for role in auth.roles:
        role_data = ROLE_MATRIX.get(role, {})
        role_descriptions.append({
            "role": role,
            "description": role_data.get("description", ""),
        })

    await write_audit_log(
        "auth.user_context.read",
        auth.tenant_id,
        {"user_id": auth.user_id, "roles": auth.roles},
    )
    return {
        "user_id": auth.user_id,
        "tenant_id": auth.tenant_id,
        "roles": auth.roles,
        "role_descriptions": role_descriptions,
        "capabilities": capabilities,
    }


@app.get("/api/v1/governance/visibility")
async def get_governance_visibility(
    request: Request,
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="governance_visibility")
    governance_service = GovernanceService()
    return governance_service.get_governance_visibility(auth.tenant_id)


@app.post("/api/v1/internal/runtime-host/replica-replay")
async def runtime_host_replica_replay(
    payload: RuntimeHostReplayRequest,
    _: None = Depends(require_runtime_host_auth),
) -> dict[str, object]:
    response = await asyncio.to_thread(execute_runtime_host_replay, payload)
    return response.model_dump(mode="json")


@app.post("/api/v1/incidents/manual-report", tags=["Incidents"], summary="Create manual incident report", status_code=202)
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


@app.post("/api/v1/incidents/raw-text", tags=["Incidents"], summary="Submit raw incident text", status_code=202)
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


@app.post("/api/v1/incidents/batch-import", tags=["Incidents"], summary="Batch import incidents", status_code=202)
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


@app.get("/api/v1/incidents/{nexus_incident_id}/proof-export")
async def get_incident_proof_export(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_context_v1")
    context = await service.get_incident_context_v1(
        nexus_incident_id,
        tenant_id=auth.tenant_id,
    )

    incident = context.get("incident", {})
    triage = context.get("triage_summary", {})
    replica = context.get("replica_summary", {})
    diagnosis = context.get("diagnosis", {})
    runbook = context.get("runbook", {})
    execution = context.get("execution_outcome")
    quality = context.get("quality_evaluation")
    tenant_support = context.get("tenant_support", {})

    proof = service.build_case_proof_export(
        incident_id=nexus_incident_id,
        incident_title=incident.get("name", "incident"),
        severity=incident.get("severity", "unknown"),
        issue_family=incident.get("issue_family"),
        support_state=tenant_support.get("support_state"),
        triage_summary=triage,
        replica_summary=replica,
        diagnosis=diagnosis,
        runbook=runbook,
        execution_outcome=execution,
        quality_evaluation=quality,
    )

    await write_audit_log(
        "incident.proof_export.read",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id},
    )
    return proof


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
    check_governance_capability(auth, "read_incidents")
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
    check_governance_capability(auth, "send_handoff")
    body = await request.json()
    target = body.get("target", "github")

    response = await service.send_engineering_handoff(
        nexus_incident_id,
        target=target,
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
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
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )
    return response


@app.post("/api/v1/incidents/{nexus_incident_id}/handoff-retry")
async def retry_engineering_handoff_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_handoff_send")
    require_role(auth, "operator", "incident_manager")
    body = await request.json()
    target = body.get("target", "github")

    response = await service.retry_delivery_handoff(
        nexus_incident_id,
        target=target,
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )

    await write_audit_log(
        "incident.handoff_retry.attempted",
        auth.tenant_id,
        {
            "nexus_incident_id": nexus_incident_id,
            "target": target,
            "status": response.get("status"),
            "user_id": auth.user_id,
        },
    )
    return response


@app.post("/api/v1/incidents/{nexus_incident_id}/engineering-feedback")
async def submit_engineering_feedback_v1(
    nexus_incident_id: str,
    request: Request,
    service: IncidentService = Depends(get_incident_service),
    auth: AuthenticatedContext = Depends(require_auth),
) -> dict[str, object]:
    await request.app.state.rate_limiter.check(auth=auth, route_key="incident_feedback")
    body = await request.json()
    feedback_status = body.get("status", "accepted")
    feedback_reason = body.get("reason", "")

    response = await service.submit_engineering_feedback(
        nexus_incident_id,
        feedback_status=feedback_status,
        feedback_reason=feedback_reason,
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )

    await write_audit_log(
        "incident.engineering_feedback.submitted",
        auth.tenant_id,
        {
            "nexus_incident_id": nexus_incident_id,
            "feedback_status": feedback_status,
            "user_id": auth.user_id,
        },
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
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
    response = await service.execute_incident(
        nexus_incident_id,
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )
    await write_audit_log(
        "incident.execute_v1.requested",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id, **response},
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
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
        response = await service.trigger_replica_replay(
            nexus_incident_id,
            tenant_id=auth.tenant_id,
            actor_user_id=auth.user_id,
            actor_roles=auth.roles,
        )
        status = response.get("status", "unknown")
        execution_state.finish_execution("completed" if status in {"replay_executed", "relay_executed"} else "failed")
    except Exception as e:
        execution_state.finish_execution("failed")
        raise

    await write_audit_log(
        "incident.replica_replay_v1.requested",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id, **response},
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
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
    response = await service.record_guardian_decision(
        nexus_incident_id,
        payload=payload,
        tenant_id=auth.tenant_id,
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
    )
    await write_audit_log(
        "incident.guardian_review_v1.requested",
        auth.tenant_id,
        {"nexus_incident_id": nexus_incident_id, "user_id": auth.user_id, **response},
        actor_user_id=auth.user_id,
        actor_roles=auth.roles,
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


@app.post("/webhooks/datadog", status_code=202)
async def receive_datadog_webhook(
    request: Request,
    incident_service: IncidentService = Depends(get_incident_service),
) -> dict[str, object]:
    import hmac
    import hashlib

    raw_body = await request.body()
    config = getattr(request.app.state, "config", None)
    webhook_secret = getattr(config, "webhook_signing_secret", "")

    dd_signature = request.headers.get("x-datadog-signature", "").strip()
    if dd_signature:
        timestamp = request.headers.get("dd-timestamp", "")
        if not timestamp:
            raise HTTPException(status_code=401, detail="Missing dd-timestamp header")
        message = f"{timestamp}.{raw_body.decode('utf-8')}"
        expected_signature = "v1," + hmac.new(
            webhook_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(dd_signature, expected_signature):
            logger.warning("datadog_webhook_signature_mismatch", extra={"path": request.url.path})
            raise HTTPException(status_code=401, detail="invalid webhook signature")

    try:
        payload_data = await request.json()

        title = payload_data.get("title", "Datadog Alert")
        priority = payload_data.get("priority", "P3")
        severity_map = {"P1": "P1", "P2": "P2", "P3": "P3", "P4": "P4", "P5": "P4"}
        severity = severity_map.get(priority, "P3")

        tags = payload_data.get("tags", [])
        service_name = next((t.split(":")[-1] for t in tags if t.startswith("service:")), "datadog-alert")

        detected_at = payload_data.get("date", datetime.now(timezone.utc).isoformat())

        incident_id = payload_data.get("id", f"dd_{hashlib.sha256(raw_body).hexdigest()[:8]}")

        webhook_payload = IncomingIncidentWebhook(
            incident_id=incident_id,
            title=title,
            severity=severity,
            detected_at=detected_at,
            monitoring_source="datadog",
            metrics={"tags": tags, "url": payload_data.get("url", "")}
        )

        tenant_id = request.app.state.tenancy_service.resolve_webhook_tenant(request)
        response = await incident_service.create_incident_from_webhook(webhook_payload, tenant_id=tenant_id)
        await write_audit_log("incident.datadog_webhook.accepted", tenant_id, response)
        return response
    except Exception as e:
        logger.exception("Failed to process Datadog webhook")
        raise HTTPException(status_code=400, detail=f"Failed to process webhook: {str(e)}")


@app.post("/webhooks/pagerduty", status_code=202)
async def receive_pagerduty_webhook(
    request: Request,
    incident_service: IncidentService = Depends(get_incident_service),
) -> dict[str, object]:
    import hmac
    import hashlib

    raw_body = await request.body()
    config = getattr(request.app.state, "config", None)
    webhook_secret = getattr(config, "webhook_signing_secret", "")

    pd_signature = request.headers.get("x-webhook-signature", "").strip()
    if pd_signature:
        expected_signature = "v1=" + hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(pd_signature, expected_signature):
            logger.warning("pagerduty_webhook_signature_mismatch", extra={"path": request.url.path})
            raise HTTPException(status_code=401, detail="invalid webhook signature")

    try:
        payload_data = await request.json()

        if "event" not in payload_data or "incident" not in payload_data:
            raise ValueError("Invalid PagerDuty webhook payload format")

        incident = payload_data.get("incident", {})
        title = incident.get("title", "PagerDuty Incident")
        urgency = incident.get("urgency", "high")
        severity_map = {"high": "P1", "low": "P2"}
        severity = severity_map.get(urgency, "P2")

        service_name = incident.get("service", {}).get("summary", "pagerduty-incident")
        detected_at = incident.get("created_at", datetime.now(timezone.utc).isoformat())
        incident_id = incident.get("incident_number", f"pd_{hashlib.sha256(raw_body).hexdigest()[:8]}")

        body = incident.get("body", {})
        details = body.get("details", "") if isinstance(body, dict) else str(body)

        webhook_payload = IncomingIncidentWebhook(
            incident_id=str(incident_id),
            title=title,
            severity=severity,
            detected_at=detected_at,
            monitoring_source="datadog",
            metrics={"urgency": urgency, "service": service_name, "details": details}
        )

        tenant_id = request.app.state.tenancy_service.resolve_webhook_tenant(request)
        response = await incident_service.create_incident_from_webhook(webhook_payload, tenant_id=tenant_id)
        await write_audit_log("incident.pagerduty_webhook.accepted", tenant_id, response)
        return response
    except Exception as e:
        logger.exception("Failed to process PagerDuty webhook")
        raise HTTPException(status_code=400, detail=f"Failed to process webhook: {str(e)}")


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
