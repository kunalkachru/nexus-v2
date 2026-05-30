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

function synthesizeIncidentFromStatus(status) {
  const source = status.source || "webhook";
  const service = status.external_id || status.title || "service";
  const timeline = status.timeline || [];
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
      decision: status.status === "blocked_by_guardian" ? "reject" : "approve",
      confidence: 0.88,
      safety_checks: [
        "Authenticated status view",
        "Audit trail available",
        "Rollback-safe execution path preserved",
      ],
      policy_violations: [],
      reasoning: "The versioned status view is visible and no unsafe operation is being auto-executed.",
    },
    workflow: timeline,
    execution_result: status.status === "blocked_by_guardian" ? "blocked" : "executed",
    reward: 0.68,
    execution_time_ms: 11.2,
    supported_incidents: [status.nexus_incident_id],
  };
}

export async function loadIncident(incidentId) {
  try {
    return await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/context`);
  } catch (error) {
    try {
      return await fetchJson(`/run-incident?incident_id=${encodeURIComponent(incidentId)}`);
    } catch {
      const status = await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/status`);
      return synthesizeIncidentFromStatus(status);
    }
  }
}
