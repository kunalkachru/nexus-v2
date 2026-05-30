from typing import Any, Literal

from pydantic import BaseModel, Field


class IncomingIncidentWebhook(BaseModel):
    incident_id: str
    title: str
    severity: Literal["P1", "P2", "P3"]
    detected_at: str
    monitoring_source: Literal["datadog", "prometheus"]
    metrics: dict[str, Any] = Field(default_factory=dict)


class ManualIncidentReport(BaseModel):
    affected_service: str
    symptoms: list[str] = Field(default_factory=list)
    severity: Literal["P0", "P1", "P2", "P3"]
    reported_by: str
    team: str
    root_cause_suspected: str | None = None
    additional_context: str | None = None
    symptom_start_time: str | None = None
    affected_regions: list[str] = Field(default_factory=list)
    affected_hosts: list[str] = Field(default_factory=list)


class BatchImportRequest(BaseModel):
    batch_name: str
    source_uri: str | None = None
    record_count: int
    severity: Literal["P0", "P1", "P2", "P3"]


class SlackIncidentCommand(BaseModel):
    command_id: str
    workspace: str
    channel: str
    user_id: str
    service: str
    severity: Literal["P0", "P1", "P2", "P3"]
    text: str
    detected_at: str
    symptoms: list[str] = Field(default_factory=list)


class StreamAnomalyReport(BaseModel):
    detector_id: str
    service: str
    severity: Literal["P0", "P1", "P2", "P3"]
    detected_at: str
    signal_name: str
    signal_value: str
    symptoms: list[str] = Field(default_factory=list)
    observed_values: dict[str, Any] = Field(default_factory=dict)
