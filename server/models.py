from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


STRICT_INCIDENT_SEVERITIES = {"P0", "P1", "P2", "P3", "P4"}


class SystemContext(BaseModel):
    service: str
    language: str
    infra: str
    dependencies: list[str] = Field(default_factory=list)


class IncidentDefinition(BaseModel):
    id: str
    name: str
    severity: str
    difficulty: str
    symptoms: list[str]
    system_context: SystemContext
    root_cause: str
    fix: str


class AgentStubInfo(BaseModel):
    name: str
    implemented: bool = False


class IncidentRecord(BaseModel):
    nexus_incident_id: str
    external_id: str
    title: str
    severity: str
    status: Literal["investigating", "resolved", "blocked_by_guardian", "needs_modification"]
    tenant_id: str = "tenant-system"
    source: Literal[
        "datadog",
        "prometheus",
        "webhook",
        "raw_text",
        "manual_form",
        "slack_command",
        "stream_anomaly",
        "batch_import",
    ] | None = None
    service: str = ""
    raw_input_text: str = ""
    normalized_evidence: dict[str, object] = Field(default_factory=dict)
    guardian_decision: Literal["pending", "approve", "reject", "request_modification"] = "pending"
    guardian_reasoning: str = ""
    guardian_reviewed_at: str = ""
    guardian_policy_id: str = ""
    guardian_policy_name: str = ""
    guardian_policy_basis: str = ""
    created_at: str = ""
    updated_at: str = ""

    @model_validator(mode="after")
    def validate_severity_by_source(self) -> "IncidentRecord":
        strict_sources = {None, "datadog", "prometheus", "webhook"}
        if self.source in strict_sources and self.severity not in STRICT_INCIDENT_SEVERITIES:
            raise ValueError("severity must be one of P0-P4 for persisted monitoring/webhook incidents")
        return self


class NormalizedAlertEnvelope(BaseModel):
    source: Literal["datadog", "prometheus"]
    external_id: str
    title: str
    severity: str
    service: str
    detected_at: str
    observed_values: dict[str, object] = Field(default_factory=dict)


class IncidentLifecycleResponse(BaseModel):
    nexus_incident_id: str
    external_id: str
    title: str
    severity: str
    status: Literal["investigating", "resolved", "blocked_by_guardian", "needs_modification"]
    source: Literal[
        "datadog",
        "prometheus",
        "webhook",
        "raw_text",
        "manual_form",
        "slack_command",
        "stream_anomaly",
        "batch_import",
    ] | None = None
    recent_deployments: list[dict[str, object]] = Field(default_factory=list)
    queue_position: int | None = None
    eta_sec: int | None = None
    guardian_decision: Literal["pending", "approve", "reject", "request_modification"] = "pending"
    guardian_reasoning: str = ""
    guardian_reviewed_at: str = ""
    guardian_policy_id: str = ""
    guardian_policy_name: str = ""
    guardian_policy_basis: str = ""


class IncidentWorkflowStage(str, Enum):
    INCIDENT_RECEIVED = "incident_received"
    VALIDATED_AUTHENTICATED = "validated_authenticated"
    ENRICHED_WITH_SERVICE_CONTEXT = "enriched_with_service_context"
    EVIDENCE_RETRIEVED = "evidence_retrieved"
    SENTINEL_CLASSIFIED = "sentinel_classified"
    PRISM_DIAGNOSED = "prism_diagnosed"
    FORGE_PROPOSED_RUNBOOK = "forge_proposed_runbook"
    GUARDIAN_REVIEWED_SAFETY = "guardian_reviewed_safety"
    EXECUTED_VERIFIED_LEARNED = "executed_verified_learned"


class QueueIncidentSummary(BaseModel):
    nexus_incident_id: str
    title: str
    severity: str
    status: Literal["investigating", "resolved", "blocked_by_guardian", "needs_modification"]
    source_channel: Literal["webhook", "raw_text", "manual_form", "slack_command", "stream_anomaly", "batch_import"]
    current_stage: IncidentWorkflowStage
    updated_at: str


class QueueResponse(BaseModel):
    items: list[QueueIncidentSummary] = Field(default_factory=list)


class IncidentStatusResponse(BaseModel):
    nexus_incident_id: str
    external_id: str
    title: str
    severity: str
    status: Literal["investigating", "resolved", "blocked_by_guardian", "needs_modification"]
    source: Literal[
        "datadog",
        "prometheus",
        "webhook",
        "raw_text",
        "manual_form",
        "slack_command",
        "stream_anomaly",
        "batch_import",
    ] | None = None
    current_stage: IncidentWorkflowStage
    queue_position: int
    eta_sec: int
    timeline: list[dict[str, object]] = Field(default_factory=list)
    audit_logs: list[dict[str, object]] = Field(default_factory=list)
    guardian_decision: Literal["pending", "approve", "reject", "request_modification"] = "pending"
    guardian_reasoning: str = ""
    guardian_reviewed_at: str = ""
    guardian_policy_id: str = ""
    guardian_policy_name: str = ""
    guardian_policy_basis: str = ""


class SentinelClassification(BaseModel):
    """Structured output returned by the SENTINEL classifier."""

    incident_id: str
    incident_name: str
    severity: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class PrismDiagnosis(BaseModel):
    """Structured output returned by the PRISM diagnosis step."""

    incident_id: str
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    queried_sources: list[str] = Field(default_factory=list)
    reasoning: str


class HistoricalRunbook(BaseModel):
    incident_id: str
    root_cause: str
    runbook_summary: str
    success_rate: float = Field(ge=0.0, le=1.0)
    similarity_score: float = Field(ge=0.0, le=1.0)


class RunbookScript(BaseModel):
    """Executable script generated by FORGE."""

    language: Literal["bash", "python", "kubectl"]
    code: str
    summary: str


class ForgeRunbookResult(BaseModel):
    """Structured output returned by FORGE runbook generation."""

    model_config = ConfigDict(protected_namespaces=())

    incident_id: str
    runbook: RunbookScript
    syntax_valid: bool
    model_name: str
    estimated_cost_usd: float = Field(ge=0.0)
    reasoning: str


class GuardianReviewResult(BaseModel):
    """Structured output returned by GUARDIAN safety review."""

    decision: Literal["approve", "reject", "request_modification"]
    safety_score: float = Field(ge=0.0, le=1.0)
    blocked_patterns: list[str] = Field(default_factory=list)
    reasoning: str
    policy_id: str = ""
    policy_name: str = ""
    policy_basis: str = ""
    risk_class: str = ""
    required_approval_level: str = ""
    blocked_controls: list[str] = Field(default_factory=list)
    rollback_readiness: str = ""
    simulation_readiness: str = ""


class ReplicaMitigationCheck(BaseModel):
    action: str
    result: str
    confidence_delta: float = 0.0
    status_code: int | None = None
    duration_ms: int | None = None
    delta_ms: int | None = None
    outcome_class: str = ""
    won: bool = False


class RuntimeHostCapability(BaseModel):
    state: str = "no_pack"
    label: str = ""
    host_label: str = ""
    can_execute_replay: bool = False
    bounded_pack_available: bool = False
    docker_available: bool = False
    compose_config_valid: bool = False
    message: str = ""


class RuntimeHostReplayRequest(BaseModel):
    incident_id: str = ""
    issue_family: str
    service: str
    recent_logs: list[object] = Field(default_factory=list)
    recent_deployments: list[object] = Field(default_factory=list)
    execute_runtime: bool = True
    mitigation_limit: int | None = None


class RuntimeHostReplayResponse(BaseModel):
    status: str
    message: str
    runtime_capability: dict[str, object] = Field(default_factory=dict)
    execution_plan: dict[str, object] = Field(default_factory=dict)
    execution_result: dict[str, object] = Field(default_factory=dict)


class ReplicaInvestigationResult(BaseModel):
    incident_id: str
    environment_pack_id: str
    reproduction_status: Literal["reproduced", "not_reproduced", "not_run", "pending"]
    reproduced_symptoms: list[str] = Field(default_factory=list)
    hypothesis_supported: bool = False
    confidence_delta: float = 0.0
    scaffold_ready: bool = False
    runtime_mode: str = "inferred"
    runtime_executed: bool = False
    services_seen: list[str] = Field(default_factory=list)
    replay_output: str = ""
    replay_status_code: int | None = None
    replay_duration_ms: int | None = None
    mitigation_outputs: list[str] = Field(default_factory=list)
    mitigation_status_codes: list[int | None] = Field(default_factory=list)
    mitigation_duration_ms: list[int | None] = Field(default_factory=list)
    runtime_comparison_summary: str = ""
    baseline_outcome_class: str = ""
    best_mitigation_action: str = ""
    best_mitigation_outcome_class: str = ""
    best_mitigation_status_code: int | None = None
    best_mitigation_duration_ms: int | None = None
    best_mitigation_summary: str = ""
    mitigation_comparison: dict[str, object] = Field(default_factory=dict)
    runtime_enablement_hint: str = ""
    runtime_capability: RuntimeHostCapability = Field(default_factory=RuntimeHostCapability)
    tested_mitigations: list[ReplicaMitigationCheck] = Field(default_factory=list)
    reasoning: str = ""


class TraceInvestigationResult(BaseModel):
    incident_id: str
    service: str
    suspected_service: str = ""
    trace_status: Literal["narrowed", "not_run", "pending"]
    suspected_modules: list[str] = Field(default_factory=list)
    suspected_functions: list[str] = Field(default_factory=list)
    expected_flow: str = ""
    observed_divergence: str = ""
    state_anomalies: list[str] = Field(default_factory=list)
    inspection_point: str = ""
    replay_evidence_summary: str = ""
    code_owner_team: str = ""
    code_owner_slug: str = ""
    suspected_files: list[str] = Field(default_factory=list)
    developer_handoff_summary: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""


class SandboxValidationResult(BaseModel):
    syntax_valid: bool
    execution_allowed: bool
    issues: list[str] = Field(default_factory=list)


class IncidentContext(BaseModel):
    incident: IncidentDefinition
    incident_id: str
    raw_symptoms: list[str] = Field(default_factory=list)
    system_context: SystemContext
    signals: dict[str, list[str]] = Field(default_factory=dict)
    signal_provenance: dict[str, list[str]] = Field(default_factory=dict)
    evidence_sources: list[dict[str, object]] = Field(default_factory=list)


class EpisodeReward(BaseModel):
    """Deterministic reward breakdown for a completed episode."""

    mttr: float = Field(ge=0.0, le=1.0)
    diagnosis: float = Field(ge=0.0, le=1.0)
    customer: float = Field(ge=0.0, le=1.0)
    coordination: float = Field(ge=0.0, le=1.0)
    oversight: float = Field(ge=0.0, le=1.0)
    severity_penalty: float = Field(ge=0.0, le=1.0)
    composite: float = Field(ge=0.0, le=1.0)


class EpisodeObservationState(BaseModel):
    """Structured observation passed into the RL training loop."""

    incident_id: str
    service: str
    severity: str
    difficulty: str
    source_channel: str
    raw_priority_label: str = ""
    normalized_priority_rank: int = Field(ge=0)
    live_reasoning: bool = False
    symptom_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    workflow_state: str


class EpisodeLearningContract(BaseModel):
    """RL-ready snapshot of a completed incident episode."""

    observation: EpisodeObservationState
    agent_trace: list[dict[str, object]] = Field(default_factory=list)
    reward_breakdown: dict[str, float] = Field(default_factory=dict)
    solution_proposal: str = ""
    raw_priority_label: str = ""
    normalized_priority_rank: int = Field(ge=0)
    live_reasoning: bool = False
    guardian_decision: str
    execution_result: str
    reward: float = Field(ge=0.0, le=1.0)
    advantage: float
    cost_usd: float = Field(ge=0.0)


class Episode(BaseModel):
    """Synchronous Day 5 episode state used by the deterministic runner and grader."""

    incident: IncidentDefinition
    sentinel_output: SentinelClassification
    prism_output: PrismDiagnosis
    forge_output: ForgeRunbookResult
    guardian_output: GuardianReviewResult
    duration_minutes: float = Field(ge=0.0)
    verification_passed: bool
    executed: bool
    status: str
    communication_events: int = Field(ge=0)
    customer_impact_minutes: float = Field(ge=0.0)
    steps: list[str] = Field(default_factory=list)
    reward: EpisodeReward | None = None
    learning_contract: EpisodeLearningContract | None = None
    enterprise_state: dict[str, object] = Field(default_factory=dict)
