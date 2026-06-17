"""
Metrics endpoint for Prometheus scraping.

Exposes /metrics endpoint with Prometheus-format metrics.
"""

from fastapi import APIRouter, Response

from server.metrics import get_metrics_text

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", response_class=Response)
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus text format metrics
    """
    return Response(
        content=get_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
