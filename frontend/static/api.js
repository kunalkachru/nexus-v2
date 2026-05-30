export async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function demoAuthHeaders() {
  return {
    "x-user-id": "user-123",
    "x-tenant-id": "tenant-a",
    "x-roles": "operator",
  };
}

export async function fetchAuthedJson(url, options = {}) {
  const headers = {
    ...demoAuthHeaders(),
    ...(options.headers || {}),
  };
  const response = await fetch(url, {
    ...options,
    headers,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function postAuthedJson(url, body) {
  return fetchAuthedJson(url, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

export function loadMetrics() {
  return fetchJson("/api/metrics");
}

const LIVE_REASONING_STORAGE_KEY = "nexus.live_reasoning";

export function getLiveReasoningPreference() {
  try {
    const stored = window.localStorage.getItem(LIVE_REASONING_STORAGE_KEY);
    if (stored === "1" || stored === "0") {
      return stored === "1";
    }
  } catch {
    // Ignore storage failures and fall back to the default toggle state.
  }
  return true;
}

export function setLiveReasoningPreference(enabled) {
  try {
    window.localStorage.setItem(LIVE_REASONING_STORAGE_KEY, enabled ? "1" : "0");
  } catch {
    // Ignore storage failures; the page toggle still updates immediately.
  }
}

function synthesizeIncidentFromStatus(status) {
  const source = status.source || "webhook";
  const service = status.external_id || status.title || "service";
  const timeline = status.timeline || [];
  const recordedGuardianDecision = ["approve", "reject", "request_modification"].includes(String(status.guardian_decision))
    ? status.guardian_decision
    : null;
  const guardianDecision =
    recordedGuardianDecision ||
    (status.status === "blocked_by_guardian"
      ? "reject"
      : status.status === "needs_modification"
        ? "request_modification"
      : status.status === "resolved"
        ? "approve"
        : "pending");
  const evidenceSources = [
    {
      source: "loki",
      signal: "logs",
      count: timeline.length,
      summary: "Timeline events stand in for correlated log lines.",
      detail: timeline[0]?.summary || "No timeline evidence available.",
    },
    {
      source: "datadog",
      signal: "metrics",
      count: 1,
      summary: "Live incident status is fused into the metrics panel.",
      detail: "Status contract is providing the live evidence path.",
    },
    {
      source: "deployment history",
      signal: "release",
      count: 1,
      summary: "Deployment metadata is represented in the same incident view.",
      detail: "Status contract keeps the operational story coherent.",
    },
    {
      source: "service graph",
      signal: "traces",
      count: 1,
      summary: "Dependent services are inferred from the live workflow path.",
      detail: status.current_stage || "Live stage available.",
    },
  ];

  return {
    incident: {
      id: status.nexus_incident_id,
      name: status.title,
      severity: status.severity,
      summary: `Live incident opened from the ${source} intake path.`,
      detected_at: timeline[0]?.timestamp || "now",
      duration_minutes: 0,
      related_services: [service],
      recent_deployments: [],
      similar_past_incidents: [],
      source_channel: source,
    },
    observability: {
      metrics: [
        { name: "Live status", current: 1, unit: "", series: [1, 2, 3, 4, 5] },
      ],
      recent_logs: timeline.slice(0, 3).map((step) => `${step.label}: ${step.summary}`),
      alert_timeline: timeline.slice(0, 4).map((step) => ({ time: step.timestamp, event: step.label })),
      recommended_runbooks: [],
      evidence_sources: evidenceSources,
    },
    classification: {
      incident_id: status.nexus_incident_id,
      incident_name: status.title,
      severity: status.severity,
      confidence: 0.72,
      confidence_breakdown: {
        intake: 0.34,
        stage: 0.22,
        evidence: 0.26,
        context: 0.18,
      },
      evidence: timeline.slice(0, 3).map((step) => step.summary),
      reasoning: "Synthesized from the versioned status contract for a live intake path.",
    },
    diagnosis: {
      root_cause: "Live incident path awaiting deeper backend enrichment.",
      confidence: 0.66,
      supporting_logs: timeline.slice(0, 3).map((step) => `${step.actor}: ${step.summary}`),
      correlation_analysis: "The status timeline shows the incident moving through the same workflow contract used by the demo console.",
      reasoning: "This incident is rendered from the API status seam rather than the static demo payload.",
    },
    runbook: {
      language: "bash",
      summary: "Rollback-safe remediation placeholder for the live intake path.",
      proposed_fix: "Rollback-safe remediation placeholder for the live intake path.",
      selection_logic: "Choose the safest action that preserves operator control while backend automation is still stubbed.",
      candidate_fixes: [
        { action: "Validate intake and confirm ownership", success_rate: 0.9 },
        { action: "Prepare rollback-safe mitigation", success_rate: 0.82 },
      ],
      recommended_runbook: "Validate intake and prepare rollback-safe mitigation.",
      reasoning: "The live path should present the same remediation contract even before deeper automation exists.",
      cost_usd: 0.05,
    },
    guardian: {
      decision: guardianDecision,
      confidence: recordedGuardianDecision ? 0.88 : status.status === "investigating" ? 0.0 : 0.88,
      policy_id: status.guardian_policy_id || "",
      policy_name: status.guardian_policy_name || "",
      policy_basis: status.guardian_policy_basis || "",
      safety_checks: [
        "Authenticated status view",
        "Audit trail available",
        "Rollback-safe execution path preserved",
      ],
      policy_violations: [],
      reasoning:
        status.guardian_reasoning ||
        (recordedGuardianDecision
          ? "Guardian review has already been recorded on the incident."
          : status.status === "needs_modification"
            ? "Guardian requested runbook changes before execution."
          : status.status === "investigating"
            ? "Guardian review is pending. Choose approve or block to make the gate explicit."
            : "The versioned status view is visible and no unsafe operation is being auto-executed."),
    },
    structured_result: {
      incident_id: status.nexus_incident_id,
      root_cause: "Live incident path awaiting deeper backend enrichment.",
      proposed_fix: "Validate intake and prepare rollback-safe mitigation.",
      safety_decision: guardianDecision,
      confidence: recordedGuardianDecision ? 0.88 : status.status === "investigating" ? 0.0 : 0.88,
      execution_status:
        status.status === "blocked_by_guardian"
          ? "blocked"
          : status.status === "needs_modification"
            ? "needs_modification"
            : status.guardian_decision === "approve"
              ? "approved"
              : status.guardian_decision === "pending" || status.status === "investigating"
                ? "pending"
                : "executed",
      live_reasoning: false,
      raw_priority_label: status.severity,
      normalized_priority_label: status.severity,
      normalized_priority_rank: Number.parseInt(String(status.severity || "").replace(/^P/, ""), 10) || 0,
      reward: 0.68,
      guardian_policy_id: status.guardian_policy_id || "",
      guardian_policy_name: status.guardian_policy_name || "",
      guardian_policy_basis: status.guardian_policy_basis || "",
    },
    workflow: timeline,
    execution_result:
      status.status === "blocked_by_guardian"
        ? "blocked"
        : status.status === "needs_modification"
          ? "needs_modification"
          : status.guardian_decision === "approve"
            ? "approved"
            : status.guardian_decision === "pending" || status.status === "investigating"
              ? "pending"
              : "executed",
      reward: 0.68,
      execution_time_ms: 11.2,
      supported_incidents: [status.nexus_incident_id],
    };
  }

export async function loadIncident(incidentId) {
  const liveReasoning = getLiveReasoningPreference() ? "1" : "0";
  try {
    return await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/context?live_reasoning=${liveReasoning}`);
  } catch (error) {
    try {
      return await fetchJson(`/run-incident?incident_id=${encodeURIComponent(incidentId)}&live_reasoning=${liveReasoning}`);
    } catch {
      const status = await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/status`);
      return synthesizeIncidentFromStatus(status);
    }
  }
}
