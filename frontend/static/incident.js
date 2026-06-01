import {
  clearUserOpenAIKey,
  fetchAuthedJson,
  formatIncidentHandle,
  hasUserOpenAIKey,
  getLiveReasoningPreference,
  isValidOpenAIKeyFormat,
  loadIncident,
  maskUserOpenAIKey,
  postAuthedJson,
  setUserOpenAIKey,
  setLiveReasoningPreference,
  summarizeIncidentTitle,
} from "./api.js";

function percent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function renderList(elementId, items, renderer) {
  const element = document.getElementById(elementId);
  if (!element) {
    return;
  }
  element.innerHTML = items.map(renderer).join("");
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = String(value);
  }
}

function syncLiveReasoningToggle() {
  const enabled = getLiveReasoningPreference();
  setText("liveReasoningState", `Live reasoning: ${enabled ? "ON" : "OFF"}`);
  const button = document.getElementById("liveReasoningToggle");
  if (button) {
    button.textContent = enabled ? "Turn live reasoning off" : "Turn live reasoning on";
  }
}

function syncOpenAIKeyUI(message) {
  const input = document.getElementById("openaiApiKeyInput");
  if (input) {
    input.value = "";
  }
  const status = hasUserOpenAIKey()
    ? `User key attached: ${maskUserOpenAIKey()}. ${message || "Live reasoning will use this key only for the current browser session."}`
    : `No user key attached. ${message || "The app is in deterministic demo mode."}`;
  setText("openaiKeyStatus", status);
}

function renderThread(data) {
  const memoryHits = data.memory_hits || {};
  const memoryCount = (memoryHits.similar_incidents || []).length + (memoryHits.unresolved_items || []).length;
  setText("threadSentinelCopy", data.classification.reasoning);
  setText(
    "threadPrismCopy",
    `${data.diagnosis.correlation_analysis || data.diagnosis.reasoning}${memoryCount ? ` PRISM also grounded the diagnosis with ${memoryCount} memory hit(s).` : ""}`
  );
  setText("threadForgeCopy", data.runbook.selection_logic || data.runbook.reasoning);
  setText(
    "threadGuardianCopy",
    `${data.guardian.reasoning}${data.guardian.risk_class ? ` Risk class: ${String(data.guardian.risk_class).toUpperCase()}.` : ""}`
  );
}

function renderCrew(data) {
  setText("sentinelFlowMeta", `${percent(data.classification.confidence)} confidence`);
  setText("sentinelReasoning", data.classification.reasoning);
  setText("sentinelFlowTransfer", "SENTINEL handed evidence to PRISM.");

  setText("prismFlowMeta", `${percent(data.diagnosis.confidence)} confidence`);
  setText("prismReasoning", data.diagnosis.correlation_analysis || data.diagnosis.reasoning);
  setText("prismFlowTransfer", "PRISM handed the diagnosis packet to FORGE.");

  const forgeConfidence = data.runbook.candidate_fixes?.length
    ? Math.max(...data.runbook.candidate_fixes.map((item) => item.success_rate))
    : 0;
  setText("forgeFlowMeta", `${percent(forgeConfidence)} confidence`);
  setText("forgeReasoning", data.runbook.selection_logic || data.runbook.reasoning);
  setText("forgeFlowTransfer", "FORGE handed the runbook proposal to GUARDIAN.");

  setText("guardianFlowMeta", String(data.guardian.decision || "pending").toUpperCase());
  setText("guardianReasoning", data.guardian.reasoning);
  setText(
    "guardianFlowTransfer",
    data.guardian.required_approval_level
      ? `GUARDIAN requires ${data.guardian.required_approval_level} approval before execution.`
      : "GUARDIAN is holding the execution gate."
  );
}

function renderSummary(data) {
  const incident = data.incident;
  setText("incidentTitle", `${formatIncidentHandle(incident.id)} · ${summarizeIncidentTitle(incident.name)}`);
  setText("incidentSubtitle", incident.summary);
  setText("incidentHeroId", formatIncidentHandle(incident.id));
  setText("incidentHeroSeverity", incident.severity);
  setText("incidentHeroGuardian", String(data.guardian.decision || "").toUpperCase());
  setText("incidentHeroExecution", String(data.execution_result || "").toUpperCase());
  setText(
    "incidentOverviewNote",
    `Detected ${incident.detected_at} via ${incident.source_channel || "webhook"} and active for ${incident.duration_minutes} minutes.`
  );
  setText(
    "liveReasoningDetail",
    data.llm_access?.message || (
      data.live_reasoning ? "Live LLM reasoning is active for this incident." : "Deterministic fallback is active for this incident."
    )
  );
  syncOpenAIKeyUI(data.llm_access?.message);

  const summary = document.getElementById("incidentSummary");
  if (summary) {
    summary.innerHTML = [
      ["Proposed fix", data.structured_result?.proposed_fix || data.runbook.recommended_runbook],
      ["Priority", data.structured_result?.raw_priority_label || incident.severity],
      ["Safety", data.guardian.decision.toUpperCase()],
      ["Policy", data.structured_result?.guardian_policy_id || data.guardian.policy_id || "-"],
    ]
      .map(
        ([label, value]) => `
          <div class="summary-card">
            <div class="label">${label}</div>
            <div class="value">${value}</div>
          </div>
        `
      )
      .join("");
  }
}

function renderEnterprise(data) {
  const orchestration = data.orchestration || {};
  const tasks = data.task_board?.tasks || [];
  const memoryHits = data.memory_hits || {};
  const metrics = data.agent_metrics || {};
  const fallbackSummary = data.fallback_summary || [];

  setText(
    "orchestrationState",
    orchestration.active_story || `State: ${String(orchestration.state || "waiting").replace(/_/g, " ")}`
  );
  setText(
    "memorySummary",
    `Loaded ${(memoryHits.similar_incidents || []).length} similar incidents, ${(memoryHits.runbooks || []).length} runbook memories, and ${(memoryHits.unresolved_items || []).length} unresolved follow-ups.`
  );
  setText(
    "fallbackSummaryNote",
    fallbackSummary.length
      ? "One branch used a bounded fallback, but the orchestrator kept the incident moving with partial evidence."
      : "All branches completed without fallback for this incident."
  );

  const taskBoard = document.getElementById("taskBoard");
  if (taskBoard) {
    taskBoard.innerHTML = tasks
      .map(
        (task, index) => `
          <article class="workflow-step ${index === tasks.length - 1 ? "final" : ""}">
            <div class="workflow-step-index">${String(index + 1).padStart(2, "0")}</div>
            <div class="workflow-step-body">
              <div class="workflow-step-top">
                <div>
                  <div class="workflow-step-label">${task.owner} · ${task.title}</div>
                  <div class="workflow-step-meta">${task.handoff_to ? `handoff -> ${task.handoff_to}` : "terminal stage"}</div>
                </div>
                <div class="badge workflow-status">${task.status}</div>
              </div>
              <p class="hero-copy">${task.summary}</p>
            </div>
          </article>
        `
      )
      .join("");
  }

  renderList(
    "memorySimilarIncidents",
    memoryHits.similar_incidents || [],
    (item) => `<li><strong>${item.incident_id}</strong><br>${item.summary}<br><span class="section-note">Similarity ${percent(item.similarity || 0)}</span></li>`
  );
  renderList(
    "memoryRunbooks",
    memoryHits.runbooks || [],
    (item) => `<li><strong>${item.runbook_summary}</strong><br><span class="section-note">${item.source || "memory"} · ${percent(item.success_rate || 0)}</span></li>`
  );
  renderList(
    "memoryUnresolvedItems",
    memoryHits.unresolved_items || [],
    (item) => `<li><strong>${item.incident_id}</strong><br>${item.title || item.summary}<br><span class="section-note">${item.status || "open"} · ${item.severity || "-"}</span></li>`
  );
  renderList(
    "fallbackSummary",
    fallbackSummary.length ? fallbackSummary : [{ stage: "none", reason: "No bounded fallback was required.", resolution: "All orchestration branches completed normally." }],
    (item) => `<li><strong>${item.stage}</strong><br>${item.reason}<br><span class="section-note">${item.resolution}</span></li>`
  );

  const agentMetrics = document.getElementById("agentMetrics");
  if (agentMetrics) {
    const metricItems = Object.values(metrics);
    agentMetrics.innerHTML = metricItems
      .map(
        (metric) => `
          <div class="summary-card">
            <div class="label">${metric.agent}</div>
            <div class="value">${percent(metric.confidence || 0)}</div>
            <div class="section-note">${metric.fallback_used ? "fallback used" : `${Math.round(Number(metric.duration_ms || 0))}ms`}</div>
          </div>
        `
      )
      .join("");
  }
}

function renderSourcePayload(incident) {
  const rawText = String(incident.raw_input_text || "").trim();
  setText("rawInputText", rawText || "No raw incident text captured yet.");

  const normalized = incident.normalized_evidence || {};
  setText("rawDetectedService", normalized.service || incident.related_services?.[0] || "-");
  setText("rawDetectedSeverity", normalized.severity || incident.severity || "-");
  setText("rawDetectedSignature", normalized.signature || "General incident");
  setText("rawDetectedAction", rawText ? "Open reasoning console" : "Waiting for raw input");

  const evidenceItems = [];
  if (normalized.source_hint) evidenceItems.push(["Source hint", normalized.source_hint]);
  if (normalized.reported_by) evidenceItems.push(["Reported by", normalized.reported_by]);
  if (normalized.team) evidenceItems.push(["Team", normalized.team]);
  if (Array.isArray(normalized.evidence)) {
    normalized.evidence.forEach((item, index) => evidenceItems.push([`Evidence ${index + 1}`, item]));
  }

  renderList(
    "normalizedEvidenceList",
    evidenceItems.length ? evidenceItems : [["Evidence", "No normalized evidence available yet."]],
    ([label, value]) => `<li><strong>${label}</strong><br><span>${typeof value === "object" ? JSON.stringify(value) : value}</span></li>`
  );
}

function renderEvidence(data) {
  renderList("recentLogs", data.observability.recent_logs || [], (line) => `<li>${line}</li>`);
  renderList("alertTimeline", data.observability.alert_timeline || [], (item) => `<li><strong>${item.time}</strong> · ${item.event}</li>`);
  renderList("recentDeployments", data.incident.recent_deployments || [], (item) => `<li><strong>${item.time} · ${item.service}</strong><br>${item.version} · ${item.change}</li>`);
  renderList(
    "similarIncidents",
    data.incident.similar_past_incidents || [],
    (item) => {
      const incidentUrl = `incident?nexus_incident_id=${encodeURIComponent(item.id)}`;
      return `<li><a class="inline-link" href="${window.NexusNavigation?.withReturnTo(incidentUrl) || incidentUrl}"><strong>${item.id}</strong></a><br>${item.summary}</li>`;
    }
  );
  renderList("evidenceProvenance", data.observability.evidence_sources || [], (item) => `<li><strong>${item.source} · ${item.signal}</strong><br>${item.summary}</li>`);

  const metricsGrid = document.getElementById("metricsGrid");
  if (metricsGrid) {
    metricsGrid.innerHTML = (data.observability.metrics || [])
      .map(
        (metric) => `
          <div class="metric-card">
            <div class="metric-top">
              <div class="metric-name">${metric.name}</div>
              <div class="metric-current">${metric.current}${metric.unit}</div>
            </div>
          </div>
        `
      )
      .join("");
  }
}

function formatAuditEventLabel(eventType) {
  return String(eventType || "audit")
    .replace(/^incident\./, "")
    .replace(/\./g, " ")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderAudit(status, auditLogs, data) {
  setText("workflowSummary", `${data.incident.id} flowing from ${data.incident.source_channel || "webhook"} to verified outcome`);
  setText("workflowSummaryCopy", "The detailed workflow remains available here when you need the system-level trace.");

  const workflow = document.getElementById("workflowTimeline");
  if (workflow) {
    workflow.innerHTML = (data.workflow || [])
      .map(
        (step, index) => `
          <article class="workflow-step ${index === data.workflow.length - 1 ? "final" : ""}">
            <div class="workflow-step-index">${String(index + 1).padStart(2, "0")}</div>
            <div class="workflow-step-body">
              <div class="workflow-step-top">
                <div><div class="workflow-step-label">${step.label}</div><div class="workflow-step-meta">${step.actor} · ${step.timestamp}</div></div>
                <div class="badge workflow-status">${step.status}</div>
              </div>
              <p class="hero-copy">${step.summary}</p>
            </div>
          </article>
        `
      )
      .join("");
  }

  setText("statusStage", status.current_stage);
  setText("statusQueuePosition", `#${status.queue_position}`);
  setText("statusEta", `${status.eta_sec}s`);
  setText("statusSource", status.source || "webhook");
  renderList("statusTimeline", status.timeline || [], (step) => `<li><strong>${step.label}</strong><br><span class="section-note">${step.actor} · ${step.status} · ${step.timestamp}</span><br>${step.summary}</li>`);

  const latest = auditLogs.at(-1);
  setText("auditEntryCount", String(auditLogs.length));
  setText("auditLatestEvent", latest ? formatAuditEventLabel(latest.event_type) : "No events yet");
  setText("auditLatestActor", latest?.payload?.user_id || latest?.tenant_id || "System");
  setText("auditLatestState", latest?.payload?.status || latest?.payload?.current_stage || "-");

  const chips = document.getElementById("auditSummaryChips");
  if (chips) {
    chips.innerHTML = auditLogs
      .slice(-3)
      .reverse()
      .map((entry) => `<span class="audit-chip">${formatAuditEventLabel(entry.event_type)}</span>`)
      .join("");
  }

  const preview = document.getElementById("auditSummaryPreview");
  if (preview) {
    preview.innerHTML = auditLogs
      .slice(-2)
      .reverse()
      .map((entry) => `<article class="audit-preview-entry"><div class="audit-preview-top"><strong>${formatAuditEventLabel(entry.event_type)}</strong><span>${entry.payload?.status || "recorded"}</span></div><div class="audit-preview-meta">${entry.timestamp || "-"}</div></article>`)
      .join("");
  }

  renderList(
    "incidentAuditLogs",
    auditLogs.length ? [...auditLogs].reverse() : [{ event_type: "audit", timestamp: "-", payload: { note: "No audit entries yet." } }],
    (entry) => `
      <article class="audit-entry">
        <div class="audit-entry-top">
          <div><div class="audit-entry-title">${formatAuditEventLabel(entry.event_type)}</div><div class="audit-entry-meta">${entry.timestamp || "-"} · ${entry.tenant_id || "tenant-system"}</div></div>
          <div class="audit-entry-badge">${entry.payload?.status || entry.payload?.current_stage || "recorded"}</div>
        </div>
      </article>
    `
  );
}

async function loadAndRenderIncident(incidentId) {
  const [data, status, auditLogs] = await Promise.all([
    loadIncident(incidentId),
    fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/status`),
    fetchAuthedJson(`/api/v1/audit-logs/${encodeURIComponent(incidentId)}`),
  ]);

  renderSummary(data);
  renderThread(data);
  renderCrew(data);
  renderEnterprise(data);
  renderSourcePayload(data.incident);
  renderEvidence(data);
  renderAudit(status, auditLogs, data);
  setText(
    "guardianGateState",
    `${data.guardian.reasoning}${data.guardian.required_approval_level ? ` Approval level: ${data.guardian.required_approval_level}.` : ""}${data.guardian.rollback_readiness ? ` Rollback: ${data.guardian.rollback_readiness}.` : ""}`
  );
  setText("executionResult", data.execution_result === "executed" ? "Execution completed after Guardian approval." : "Execution is waiting on a clear governance decision.");
  setText("resultBanner", `${formatIncidentHandle(data.incident.id)} · ${String(data.guardian.decision).toUpperCase()} · ${data.execution_time_ms}ms`);
  return data;
}

function getIncidentId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("incident_id") || params.get("nexus_incident_id") || "INC001";
}

function setGuardianButtonsDisabled(disabled) {
  ["guardianApproveBtn", "guardianBlockBtn", "guardianModifyBtn"].forEach((id) => {
    const button = document.getElementById(id);
    if (button) {
      button.disabled = disabled;
    }
  });
}

window.addEventListener("load", async () => {
  const incidentId = getIncidentId();
  syncLiveReasoningToggle();
  syncOpenAIKeyUI();

  async function applyGuardianDecision(decision) {
    setGuardianButtonsDisabled(true);
    try {
      await postAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/guardian-review`, {
        decision,
        reasoning: `Operator selected ${decision}.`,
      });
      if (decision === "approve") {
        await postAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/execute`, {});
      }
      await loadAndRenderIncident(incidentId);
    } finally {
      setGuardianButtonsDisabled(false);
    }
  }

  document.getElementById("liveReasoningToggle")?.addEventListener("click", async () => {
    setLiveReasoningPreference(!getLiveReasoningPreference());
    syncLiveReasoningToggle();
    await loadAndRenderIncident(incidentId);
  });

  document.getElementById("saveOpenAIKeyBtn")?.addEventListener("click", async () => {
    const value = document.getElementById("openaiApiKeyInput")?.value || "";
    if (!isValidOpenAIKeyFormat(value)) {
      syncOpenAIKeyUI("Invalid OpenAI key format. Expected a key that starts with sk-.");
      return;
    }
    setUserOpenAIKey(value);
    syncOpenAIKeyUI("Saved for this browser session only. It is never persisted server-side.");
    if (!getLiveReasoningPreference()) {
      setLiveReasoningPreference(true);
      syncLiveReasoningToggle();
    }
    await loadAndRenderIncident(incidentId);
  });

  document.getElementById("clearOpenAIKeyBtn")?.addEventListener("click", async () => {
    clearUserOpenAIKey();
    syncOpenAIKeyUI("User key cleared. The app is back in deterministic demo mode.");
    await loadAndRenderIncident(incidentId);
  });

  document.getElementById("guardianApproveBtn")?.addEventListener("click", async () => applyGuardianDecision("approve"));
  document.getElementById("guardianBlockBtn")?.addEventListener("click", async () => applyGuardianDecision("reject"));
  document.getElementById("guardianModifyBtn")?.addEventListener("click", async () => applyGuardianDecision("request_modification"));

  try {
    await loadAndRenderIncident(incidentId);
  } catch (error) {
    setText("incidentTitle", "Incident unavailable");
    setText("resultBanner", `Failed to load ${incidentId}: ${error.message}`);
  }
});
