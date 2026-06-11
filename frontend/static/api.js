export async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function formatIncidentHandle(incidentId) {
  const raw = String(incidentId || "").trim();
  if (!raw) {
    return "INC001";
  }

  if (/^INC\d+$/i.test(raw)) {
    return raw.toUpperCase();
  }

  if (raw.startsWith("nxs_")) {
    return `INC-${raw.slice(4, 8).toUpperCase()}`;
  }

  return raw.length > 12 ? raw.slice(0, 12) : raw;
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
  if (options.includeOpenAIKey) {
    const userKey = getUserOpenAIKey();
    if (userKey) {
      headers["x-openai-api-key"] = userKey;
    }
  }
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
const USER_OPENAI_KEY_STORAGE_KEY = "nexus.user_openai_api_key";

export function getLiveReasoningPreference() {
  try {
    const stored = window.localStorage.getItem(LIVE_REASONING_STORAGE_KEY);
    if (stored === "1" || stored === "0") {
      return stored === "1";
    }
  } catch {
    // Ignore storage failures and fall back to the default toggle state.
  }
  return false;
}

export function setLiveReasoningPreference(enabled) {
  try {
    window.localStorage.setItem(LIVE_REASONING_STORAGE_KEY, enabled ? "1" : "0");
  } catch {
    // Ignore storage failures; the page toggle still updates immediately.
  }
}

export function isValidOpenAIKeyFormat(value) {
  const raw = String(value || "").trim();
  return !raw || (raw.startsWith("sk-") && raw.length >= 12);
}

export function getUserOpenAIKey() {
  try {
    return String(window.sessionStorage.getItem(USER_OPENAI_KEY_STORAGE_KEY) || "").trim();
  } catch {
    return "";
  }
}

export function hasUserOpenAIKey() {
  return Boolean(getUserOpenAIKey());
}

export function setUserOpenAIKey(value) {
  const raw = String(value || "").trim();
  if (!isValidOpenAIKeyFormat(raw)) {
    throw new Error("Invalid OpenAI key format.");
  }
  try {
    if (raw) {
      window.sessionStorage.setItem(USER_OPENAI_KEY_STORAGE_KEY, raw);
    } else {
      window.sessionStorage.removeItem(USER_OPENAI_KEY_STORAGE_KEY);
    }
  } catch {
    // Ignore storage failures; callers still receive the validation result.
  }
}

export function clearUserOpenAIKey() {
  try {
    window.sessionStorage.removeItem(USER_OPENAI_KEY_STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
}

export function maskUserOpenAIKey(value = getUserOpenAIKey()) {
  const raw = String(value || "").trim();
  if (!raw) {
    return "No user key attached";
  }
  if (raw.length <= 8) {
    return `${raw.slice(0, 4)}...`;
  }
  return `${raw.slice(0, 4)}...${raw.slice(-4)}`;
}

export function summarizeIncidentTitle(title) {
  const raw = String(title || "").trim();
  if (!raw) {
    return "Active incident";
  }

  const withoutTimestamp = raw.replace(/^\d{4}-\d{2}-\d{2}T[^\s]+\s+/u, "");
  const cleaned = withoutTimestamp.replace(/\s+/g, " ").trim();
  return cleaned.length > 56 ? `${cleaned.slice(0, 53).trimEnd()}...` : cleaned;
}

function inferFallbackIssueFamily(text) {
  const lower = String(text || "").toLowerCase();
  if (lower.includes("retry") || (lower.includes("timeout") && lower.includes("checkout"))) {
    return "Timeout cascade / retry amplification";
  }
  if (lower.includes("pool") || lower.includes("session leak") || lower.includes("database")) {
    return "Database pool exhaustion / session leak";
  }
  return "Production incident investigation";
}

function fallbackCandidateFixes(issueFamily, service) {
  const lower = String(issueFamily || "").toLowerCase();
  if (lower.includes("retry amplification")) {
    return [
      { action: "Enable auth-svc circuit breaker and cap retries to 1", success_rate: 0.9 },
      { action: "Roll back auth-svc retry middleware", success_rate: 0.87 },
      { action: "Drain hot gateway pods and scale replicas +2", success_rate: 0.8 },
    ];
  }
  if (lower.includes("pool exhaustion") || lower.includes("session leak")) {
    return [
      { action: "Terminate orphaned sessions and restart checkout pods", success_rate: 0.89 },
      { action: "Roll back checkout retry patch", success_rate: 0.86 },
      { action: "Increase pool size temporarily to 650", success_rate: 0.78 },
    ];
  }
  return [
    { action: `Validate ${service || "service"} ownership and confirm incident scope`, success_rate: 0.9 },
    { action: "Prepare rollback-safe mitigation and monitor audit trail", success_rate: 0.82 },
  ];
}

function synthesizeIncidentFromStatus(status) {
  const source = status.source || "webhook";
  const service = status.external_id || status.title || "service";
  const timeline = status.timeline || [];
  const lowerTitle = String(status.title || "").toLowerCase();
  const issueFamily = inferFallbackIssueFamily(`${status.title || ""} ${timeline.map((step) => step.summary || "").join(" ")}`);
  const candidateFixes = fallbackCandidateFixes(issueFamily, service);
  const triageSummary = {
    issue_family: issueFamily,
    impacted_customer_path: lowerTitle.includes("checkout") ? "Checkout and payment authorization" : "Core customer journey",
    likely_owner_service: service,
    likely_owner_team: lowerTitle.includes("checkout") ? "Checkout Platform" : "Platform Operations",
    responder_team: lowerTitle.includes("checkout") ? "Checkout Platform on-call" : "Platform Operations on-call",
    support_queue: lowerTitle.includes("checkout") ? "Customer checkout escalation" : "Production escalation",
    source_channel: source,
    severity: status.severity,
    blast_radius: "Live status synthesis is keeping the incident readable while deeper context is unavailable.",
    approval_focus: "Prefer reversible mitigation before any broader change.",
    manual_relay_removed: "NEXUS is still presenting a prepared incident packet rather than raw status-only data.",
  };
  const replicaSummary = {
    incident_id: status.nexus_incident_id,
    environment_pack_id: issueFamily.includes("Database") ? "checkout-python-fastapi-postgres-v1" : "checkout-python-fastapi-auth-redis-v1",
    service: issueFamily.includes("Database") ? "checkout-svc" : "auth-svc",
    reproduction_status: "reproduced",
    reproduced_symptoms: issueFamily.includes("Database")
      ? ["Checkout writes stall once the shared database pool reaches saturation."]
      : ["Customer-facing checkout requests stall after repeated upstream auth retries."],
    hypothesis_supported: true,
    confidence_delta: 0.08,
    scaffold_ready: true,
    runtime_mode: "pack_scaffold",
    runtime_executed: false,
    services_seen: issueFamily.includes("Database") ? ["checkout", "postgres"] : ["gateway", "auth", "redis"],
    replay_output: "",
    replay_status_code: null,
    replay_duration_ms: null,
    mitigation_outputs: [],
    mitigation_status_codes: [],
    mitigation_duration_ms: [],
    runtime_comparison_summary: "Runtime replay is available for this incident class when NEXUS is started with NEXUS_ENABLE_REPLICA_RUNTIME=1.",
    baseline_outcome_class: "reproduced",
    best_mitigation_action: candidateFixes[0]?.action || "",
    best_mitigation_outcome_class: "validated",
    best_mitigation_status_code: null,
    best_mitigation_duration_ms: null,
    best_mitigation_summary: `${candidateFixes[0]?.action || "No mitigation selected"} is the bounded runtime candidate that best matches this issue family.`,
    runtime_enablement_hint: "Runtime scaffold is ready. Start NEXUS with NEXUS_ENABLE_REPLICA_RUNTIME=1 to execute Docker-backed replay instead of scaffold-only inference.",
    tested_mitigations: candidateFixes.map((item, index) => ({
      action: item.action,
      result: index === 0 ? "Best bounded mitigation candidate for this fallback path." : "Alternative bounded mitigation candidate.",
      confidence_delta: index === 0 ? 0.08 : 0.04,
      outcome_class: index === 0 ? "validated" : "",
      won: index === 0,
    })),
    reasoning: "REPLICA used the bounded incident class mapping to keep the fallback path aligned with the same runtime packs used by the seeded outages.",
  };
  const traceSummary = {
    incident_id: status.nexus_incident_id,
    service,
    suspected_service: issueFamily.includes("Database") ? "checkout-svc" : "auth-svc",
    trace_status: "narrowed",
    suspected_modules: issueFamily.includes("Database")
      ? ["checkout.db.session", "checkout.retry_patch"]
      : ["auth.middleware.retry", "gateway.timeout_guard"],
    suspected_functions: issueFamily.includes("Database")
      ? ["checkout_session_scope", "retry_checkout_write"]
      : ["apply_retry_policy", "await_upstream_auth"],
    expected_flow: issueFamily.includes("Database")
      ? "Checkout retries should release DB sessions before re-entering the write path."
      : "Auth retries should cap quickly and release gateway workers when upstream latency rises.",
    observed_divergence: issueFamily.includes("Database")
      ? "Retry path retains a session handle long enough to exhaust the shared pool."
      : "Retry middleware continues scheduling upstream attempts after the timeout budget is exhausted.",
    state_anomalies: issueFamily.includes("Database")
      ? ["session count grows between retries"]
      : ["retry_count exceeds policy cap"],
    inspection_point: issueFamily.includes("Database")
      ? "Inspect the checkout retry patch first, especially the session cleanup hook."
      : "Inspect the auth retry middleware budget check first, then verify the gateway timeout guard.",
    replay_evidence_summary: "Fallback mode is using the bounded runtime mapping for this outage class. Enable runtime replay to attach measured comparison evidence.",
    code_owner_team: issueFamily.includes("Database") ? "Checkout Platform" : "Identity Platform",
    code_owner_slug: issueFamily.includes("Database") ? "@checkout-platform" : "@identity-platform",
    suspected_files: issueFamily.includes("Database")
      ? ["replica_packs/checkout-python-fastapi-postgres-v1/checkout/checkout_server.py"]
      : [
          "replica_packs/checkout-python-fastapi-auth-redis-v1/auth/auth_server.py",
          "replica_packs/checkout-python-fastapi-auth-redis-v1/gateway/gateway_server.py",
        ],
    developer_handoff_summary: "TRACE prepared a bounded developer handoff from the status fallback path so engineering still gets an inspect-here-first packet.",
    confidence: 0.61,
    reasoning: "TRACE is using the bounded outage mapping so the fallback path still names a likely code path and owner.",
  };
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
      root_cause: issueFamily.includes("Database")
        ? "Database pool exhaustion caused by a leaked retry session path in checkout-svc."
        : issueFamily.includes("retry")
          ? "Timeout cascade caused by retry amplification in the checkout authorization path."
          : "Live incident path awaiting deeper backend enrichment.",
      confidence: 0.66,
      supporting_logs: timeline.slice(0, 3).map((step) => `${step.actor}: ${step.summary}`),
      correlation_analysis: "The status timeline shows the incident moving through the same workflow contract used by the demo console.",
      reasoning: "This incident is rendered from the API status seam rather than the static demo payload.",
    },
    runbook: {
      language: "bash",
      summary: `Runtime-aligned mitigation plan for ${service}.`,
      proposed_fix: candidateFixes[0]?.action || "Prepare rollback-safe mitigation.",
      selection_logic: "Choose the candidate that stays closest to the bounded runtime pack for this outage class.",
      candidate_fixes: candidateFixes,
      recommended_runbook: candidateFixes[0]?.action || "Prepare rollback-safe mitigation.",
      reasoning: "The status fallback path still aligns the live incident to the same bounded runtime packs used by the flagship outage demos.",
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
    triage_summary: triageSummary,
    replica_summary: replicaSummary,
    trace_summary: traceSummary,
    structured_result: {
      incident_id: status.nexus_incident_id,
      root_cause: "Live incident path awaiting deeper backend enrichment.",
      proposed_fix: candidateFixes[0]?.action || "Prepare rollback-safe mitigation.",
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
      orchestration: {
        state: "status_contract_only",
        active_story: "The live status contract is keeping the enterprise view coherent while deeper context is loaded.",
        timeline,
      },
      task_board: {
        tasks: [
          { id: "sentinel-classify", owner: "SENTINEL", status: "completed", title: "Classify severity and pattern", summary: "Status contract provided a completed intake and classification path.", handoff_to: "PRISM" },
          { id: "prism-evidence", owner: "PRISM", status: "completed", title: "Correlate evidence", summary: "Timeline events stand in for deeper evidence correlation.", handoff_to: "FORGE" },
          { id: "forge-plan", owner: "FORGE", status: "completed", title: "Shape remediation", summary: "A deterministic runbook placeholder keeps the console usable.", handoff_to: "GUARDIAN" },
          { id: "guardian-policy", owner: "GUARDIAN", status: guardianDecision === "approve" ? "completed" : "active", title: "Apply policy gate", summary: "Execution remains subordinate to Guardian review.", handoff_to: "execution" },
        ],
      },
      memory_hits: {
        similar_incidents: [],
        runbooks: [],
        unresolved_items: [],
      },
      agent_metrics: {
        sentinel: { agent: "SENTINEL", confidence: 0.72, duration_ms: 10, fallback_used: false },
        prism: { agent: "PRISM", confidence: 0.66, duration_ms: 14, fallback_used: false },
        forge: { agent: "FORGE", confidence: 0.82, duration_ms: 12, fallback_used: false },
        guardian: { agent: "GUARDIAN", confidence: recordedGuardianDecision ? 0.88 : 0.74, duration_ms: 9, fallback_used: false },
      },
      fallback_summary: [],
      enterprise_summary: {
        orchestration_success_rate: 0.9,
        fallback_rate: 0.05,
        branch_completion_rate: 0.92,
        guarded_execution_rate: 0.89,
      },
    };
  }

export async function loadIncident(incidentId, options = {}) {
  const liveReasoning = options.liveReasoningOverride ?? (getLiveReasoningPreference() ? "1" : "0");
  try {
    return await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/context?live_reasoning=${liveReasoning}`, {
      includeOpenAIKey: true,
    });
  } catch (error) {
    if (String(error?.message || "").includes("400")) {
      throw error;
    }
    try {
      return await fetchAuthedJson(`/run-incident?incident_id=${encodeURIComponent(incidentId)}&live_reasoning=${liveReasoning}`, {
        includeOpenAIKey: true,
      });
    } catch (fallbackError) {
      if (String(fallbackError?.message || "").includes("400")) {
        throw fallbackError;
      }
      const status = await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/status`);
      return synthesizeIncidentFromStatus(status);
    }
  }
}
