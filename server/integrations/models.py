from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


STRICT_SEVERITIES = {"P0", "P1", "P2", "P3", "P4"}


class IncomingIncidentWebhook(BaseModel):
    incident_id: str
    title: str
    severity: str
    detected_at: str
    monitoring_source: Literal["datadog", "prometheus"]
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in STRICT_SEVERITIES:
            raise ValueError("severity must be one of P0-P4")
        return value


class ManualIncidentReport(BaseModel):
    affected_service: str
    symptoms: list[str] = Field(default_factory=list)
    severity: str
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
    severity: str


class RawIncidentTextRequest(BaseModel):
    raw_text: str
    source_hint: str | None = None
    reported_by: str | None = None
    team: str | None = None
    severity_hint: str | None = None


class GuardianDecisionRequest(BaseModel):
    decision: Literal["approve", "reject", "request_modification"]
    reasoning: str | None = None


class SlackIncidentCommand(BaseModel):
    command_id: str
    workspace: str
    channel: str
    user_id: str
    service: str
    severity: str
    text: str
    detected_at: str
    symptoms: list[str] = Field(default_factory=list)


class StreamAnomalyReport(BaseModel):
    detector_id: str
    service: str
    severity: str
    detected_at: str
    signal_name: str
    signal_value: str
    symptoms: list[str] = Field(default_factory=list)
    observed_values: dict[str, Any] = Field(default_factory=dict)
