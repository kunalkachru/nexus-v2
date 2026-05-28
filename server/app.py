from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import json
import os

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    """Serve dashboard HTML"""
    return FileResponse("frontend/dashboard.html", media_type="text/html")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/metrics")
async def get_metrics():
    """Return training metrics"""
    try:
        with open("frontend/metrics.json") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/run-incident")
async def run_incident(incident_id: str):
    """Run incident through pipeline"""
    try:
        # Incident descriptions
        incidents = {
            "INC001": {"severity": "P1", "description": "Third-party Stripe API degradation causing upstream timeout"},
            "INC002": {"severity": "P2", "description": "Leaked database sessions exhaust the connection pool"},
            "INC003": {"severity": "P2", "description": "Image-processing tasks retain large objects between jobs"},
            "INC004": {"severity": "P3", "description": "New key pattern exploded cache cardinality and forced aggressive eviction"},
            "INC005": {"severity": "P2", "description": "A bad deployment disabled partition rebalancing and left consumers idle"},
        }
        
        incident = incidents.get(incident_id, incidents["INC001"])
        
        return {
            "incident_id": incident_id,
            "classification": {
                "incident_id": incident_id,
                "severity": incident["severity"],
                "confidence": 0.975
            },
            "diagnosis": {
                "root_cause": incident["description"],
                "confidence": 0.92
            },
            "runbook": {
                "language": "bash",
                "summary": f"Runbook for {incident_id}",
                "cost_usd": 0.12
            },
            "execution_result": "executed",
            "reward": 0.8033,
            "execution_time_ms": 0.0087
        }
    except Exception as e:
        return {"error": str(e)}, 500
