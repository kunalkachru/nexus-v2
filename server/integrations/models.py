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
    affected_service: str = Field(min_length=1, max_length=255)
    symptoms: list[str] = Field(default_factory=list, max_length=50)
    severity: str
    reported_by: str = Field(min_length=1, max_length=255)
    team: str = Field(min_length=1, max_length=255)
    root_cause_suspected: str | None = Field(None, max_length=5000)
    additional_context: str | None = Field(None, max_length=5000)
    symptom_start_time: str | None = None
    affected_regions: list[str] = Field(default_factory=list, max_length=50)
    affected_hosts: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in STRICT_SEVERITIES:
            raise ValueError("severity must be one of P0-P4")
        return value


class BatchImportRequest(BaseModel):
    batch_name: str = Field(min_length=1, max_length=255)
    source_uri: str | None = Field(None, max_length=2000)
    record_count: int = Field(ge=1, le=10000)
    severity: str

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in STRICT_SEVERITIES:
            raise ValueError("severity must be one of P0-P4")
        return value


class RawIncidentTextRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=50000)
    source_hint: str | None = Field(None, max_length=255)
    reported_by: str | None = Field(None, max_length=255)
    team: str | None = Field(None, max_length=255)
    severity_hint: str | None = Field(None, max_length=255)


class GuardianDecisionRequest(BaseModel):
    decision: Literal["approve", "reject", "request_modification"]
    reasoning: str | None = None


class SlackIncidentCommand(BaseModel):
    command_id: str = Field(min_length=1, max_length=255)
    workspace: str = Field(min_length=1, max_length=255)
    channel: str = Field(min_length=1, max_length=255)
    user_id: str = Field(min_length=1, max_length=255)
    service: str = Field(min_length=1, max_length=255)
    severity: str
    text: str = Field(min_length=1, max_length=5000)
    detected_at: str
    symptoms: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in STRICT_SEVERITIES:
            raise ValueError("severity must be one of P0-P4")
        return value


class StreamAnomalyReport(BaseModel):
    detector_id: str = Field(min_length=1, max_length=255)
    service: str = Field(min_length=1, max_length=255)
    severity: str
    detected_at: str
    signal_name: str = Field(min_length=1, max_length=255)
    signal_value: str = Field(min_length=1, max_length=5000)
    symptoms: list[str] = Field(default_factory=list, max_length=50)
    observed_values: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in STRICT_SEVERITIES:
            raise ValueError("severity must be one of P0-P4")
        return value
