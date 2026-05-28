import json

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server.incident_payloads import (
    get_incident_definition,
    get_incident_details,
    list_supported_incident_ids,
)

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend"), name="static")


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


@app.get("/api/metrics")
async def get_metrics():
    try:
        with open("frontend/metrics.json") as file_handle:
            return json.load(file_handle)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/run-incident")
async def run_incident(incident_id: str = "INC001"):
    try:
        return _build_incident_response(incident_id)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
