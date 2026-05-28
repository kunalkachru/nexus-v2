from typing import Any, Literal

from pydantic import BaseModel, Field


class IncomingIncidentWebhook(BaseModel):
    incident_id: str
    title: str
    severity: Literal["P1", "P2", "P3"]
    detected_at: str
    monitoring_source: Literal["datadog", "prometheus"]
    metrics: dict[str, Any] = Field(default_factory=dict)
