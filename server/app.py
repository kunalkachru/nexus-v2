from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from training.reporting import FRONTEND_DIR, ensure_metrics_payload

app = FastAPI(title="NEXUS v3")

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/metrics")
async def metrics_redirect() -> RedirectResponse:
    return RedirectResponse(url="/api/metrics", status_code=307)


@app.get("/api/metrics")
async def metrics() -> dict[str, object]:
    return ensure_metrics_payload()
