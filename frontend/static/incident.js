import { fetchAuthedJson, loadIncident, postAuthedJson } from "./api.js";

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeBars(series) {
  const max = Math.max(...series, 1);
  return series.map((value) => Math.max(10, Math.round((value / max) * 100)));
}

function renderList(elementId, items, renderer) {
  const element = document.getElementById(elementId);
  element.innerHTML = items.map(renderer).join("");
}

function renderAgentFlow(data) {
  document.getElementById("sentinelFlowMeta").textContent = `${Math.round(data.classification.confidence * 100)}% confidence · ${data.classification.evidence.length} evidence items`;
  document.getElementById("prismFlowMeta").textContent = `${Math.round(data.diagnosis.confidence * 100)}% confidence · ${data.diagnosis.root_cause}`;
  document.getElementById("forgeFlowMeta").textContent = data.runbook.recommended_runbook;
  document.getElementById("guardianFlowMeta").textContent = `${data.guardian.decision.toUpperCase()} · ${Math.round(data.guardian.confidence * 100)}% safety confidence`;
}

function animateAgentFlow() {
  const stages = [
    { flowId: "sentinelFlowNode", cardId: "sentinelCard" },
    { flowId: "prismFlowNode", cardId: "prismCard" },
    { flowId: "forgeFlowNode", cardId: "forgeCard" },
    { flowId: "guardianFlowNode", cardId: "guardianCard" },
  ];

  stages.forEach((stage, index) => {
    setTimeout(() => {
      stages.forEach((otherStage, otherIndex) => {
        const flowNode = document.getElementById(otherStage.flowId);
        const card = document.getElementById(otherStage.cardId);
        if (!flowNode || !card) {
          return;
        }
        flowNode.classList.remove("active");
        card.classList.remove("active");
        if (otherIndex < index) {
          flowNode.classList.add("complete");
          card.classList.add("complete");
        } else {
          flowNode.classList.remove("complete");
          card.classList.remove("complete");
        }
      });

      document.getElementById(stage.flowId)?.classList.add("active");
      document.getElementById(stage.cardId)?.classList.add("active");
    }, index * 900);
  });
}

function renderWorkflowTimeline(workflow, incident) {
  const element = document.getElementById("workflowTimeline");
  element.innerHTML = workflow
    .map((step, index) => `
      <article class="workflow-step ${index === workflow.length - 1 ? "final" : ""}">
        <div class="workflow-step-index">${String(index + 1).padStart(2, "0")}</div>
        <div class="workflow-step-body">
          <div class="workflow-step-top">
            <div>
              <div class="workflow-step-label">${step.label}</div>
              <div class="workflow-step-meta">${step.actor} · ${step.timestamp}</div>
            </div>
            <div class="badge workflow-status">${step.status}</div>
          </div>
          <p class="hero-copy">${step.summary}</p>
          <div class="workflow-payload">
            ${(step.payload ? Object.entries(step.payload) : [])
              .map(([key, value]) => `<span>${key}: ${typeof value === "object" ? JSON.stringify(value) : value}</span>`)
              .join("")}
          </div>
        </div>
      </article>
    `)
    .join("");

  element.querySelectorAll(".workflow-step").forEach((node, index) => {
    setTimeout(() => node.classList.add("active"), 100 + index * 180);
  });

  document.getElementById("workflowSummary").textContent = `${incident.id} flowing from ${incident.source_channel || "webhook"} to verified outcome`;
  document.getElementById("workflowSummaryCopy").textContent = `A single incident moves through the same nine workflow states the product exposes to users.`;
}

function renderStatusTimeline(timeline) {
  const element = document.getElementById("statusTimeline");
  element.innerHTML = timeline
    .map(
      (step) => `
        <li>
          <strong>${step.label}</strong><br>
          <span class="section-note">${step.actor} · ${step.status} · ${step.timestamp}</span><br>
          ${step.summary}
        </li>
      `
    )
    .join("");
}

function formatAuditEventLabel(eventType) {
  return String(eventType || "audit")
    .replace(/^incident\./, "")
    .replace(/\./g, " ")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function auditSummaryChips(logs) {
  const counts = logs.reduce(
    (acc, entry) => {
      const eventType = String(entry.event_type || "audit");
      const category = eventType.includes("accept")
        ? "accepted"
        : eventType.includes("read")
          ? "read"
          : eventType.includes("execute")
            ? "execute"
            : eventType.includes("launched")
              ? "launch"
              : "other";
      acc[category] = (acc[category] || 0) + 1;
      return acc;
    },
    { accepted: 0, read: 0, execute: 0, launch: 0, other: 0 }
  );

  return [
    ["Accepted", counts.accepted],
    ["Reads", counts.read],
    ["Execute", counts.execute],
    ["Launches", counts.launch],
    ["Other", counts.other],
  ];
}

function renderAuditSummary(logs) {
  const latest = logs.at(-1);
  document.getElementById("auditEntryCount").textContent = String(logs.length);
  document.getElementById("auditLatestEvent").textContent = latest ? formatAuditEventLabel(latest.event_type) : "No events yet";
  document.getElementById("auditLatestActor").textContent = latest?.payload?.user_id || latest?.tenant_id || "System";
  document.getElementById("auditLatestState").textContent = latest?.payload?.status || latest?.payload?.current_stage || latest?.event_type || "-";
  document.getElementById("auditSummaryChips").innerHTML = auditSummaryChips(logs)
    .map(([label, value]) => `<span class="audit-chip">${label}: ${value}</span>`)
    .join("");
  const preview = logs.slice(-3).reverse();
  document.getElementById("auditSummaryPreview").innerHTML = preview.length
    ? preview
        .map(
          (entry) => `
            <article class="audit-preview-entry">
              <div class="audit-preview-top">
                <strong>${formatAuditEventLabel(entry.event_type)}</strong>
                <span>${entry.payload?.status || entry.payload?.current_stage || "recorded"}</span>
              </div>
              <div class="audit-preview-meta">${entry.timestamp || "-"} · ${entry.payload?.user_id || entry.tenant_id || "System"}</div>
            </article>
          `
        )
        .join("")
    : `<div class="audit-preview-empty">No audit entries yet.</div>`;
}

function renderStatusPanel(status) {
  document.getElementById("statusStage").textContent = status.current_stage;
  document.getElementById("statusQueuePosition").textContent = `#${status.queue_position}`;
  document.getElementById("statusEta").textContent = `${status.eta_sec}s`;
  document.getElementById("statusSource").textContent = status.source || "webhook";
  renderStatusTimeline(status.timeline || []);
}

function renderAuditTrail(logs) {
  const element = document.getElementById("incidentAuditLogs");
  const orderedLogs = logs.length ? [...logs].reverse() : [{ event_type: "audit", timestamp: "-", payload: { note: "No audit entries yet." } }];
  element.innerHTML = orderedLogs
    .map(
      (entry, index) => `
        <article class="audit-entry ${index === 0 ? "latest" : ""}">
          <div class="audit-entry-top">
            <div>
              <div class="audit-entry-title">${formatAuditEventLabel(entry.event_type)}</div>
              <div class="audit-entry-meta">${entry.timestamp || "-"} · ${entry.tenant_id || "tenant-system"}</div>
            </div>
            <div class="audit-entry-badge">${entry.payload?.status || entry.payload?.current_stage || "recorded"}</div>
          </div>
          <div class="audit-entry-body">
            ${entry.payload ? Object.entries(entry.payload).map(([key, value]) => `
              <span>${key}: ${typeof value === "object" ? JSON.stringify(value) : value}</span>
            `).join("") : "<span>No payload</span>"}
          </div>
        </article>
      `
    )
    .join("");
}

async function refreshLiveSections(incidentId) {
  const [status, auditLogs] = await Promise.all([
    fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/status`),
    fetchAuthedJson(`/api/v1/audit-logs/${encodeURIComponent(incidentId)}`),
  ]);
  renderStatusPanel(status);
  renderAuditSummary(auditLogs);
  renderAuditTrail(auditLogs);
  return status;
}

function renderIncident(data) {
  const incident = data.incident;
  const observability = data.observability;
  const classification = data.classification;
  const diagnosis = data.diagnosis;
  const runbook = data.runbook;
  const guardian = data.guardian;
  const workflow = data.workflow || [];

  document.title = `NEXUS v2 - ${incident.id}`;
  document.getElementById("incidentTitle").textContent = `${incident.id} · ${incident.name}`;
  document.getElementById("incidentSubtitle").textContent = incident.summary;
  document.getElementById("incidentHeroId").textContent = incident.id;
  document.getElementById("incidentHeroSeverity").textContent = incident.severity;
  document.getElementById("incidentHeroGuardian").textContent = guardian.decision.toUpperCase();
  document.getElementById("incidentHeroExecution").textContent = data.execution_result.toUpperCase();
  document.getElementById("incidentOverviewNote").textContent = `Detected ${incident.detected_at} via ${incident.source_channel || "webhook"} and active for ${incident.duration_minutes} minutes.`;

  document.getElementById("incidentSummary").innerHTML = [
    ["Detected", incident.detected_at],
    ["Duration", `${incident.duration_minutes} min`],
    ["Source", incident.source_channel || "webhook"],
    ["Runbook", runbook.recommended_runbook],
    ["Reward", `${Math.round(data.reward * 100)}%`],
  ].map(([label, value]) => `
    <div class="summary-card">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
    </div>
  `).join("");

  document.getElementById("incidentNarrative").innerHTML = `
    <div class="badge">${incident.summary}</div>
    <p class="hero-copy">Affected services include ${incident.related_services.join(", ")}. The console shows evidence, agent reasoning, and safety review as a single workflow.</p>
  `;

  document.getElementById("servicePills").innerHTML = incident.related_services
    .map((service) => `<div class="pill">${service}</div>`)
    .join("");

  document.getElementById("metricsGrid").innerHTML = observability.metrics.map((metric) => `
    <div class="metric-card">
      <div class="metric-top">
        <div class="metric-name">${metric.name}</div>
        <div class="metric-current">${metric.current}${metric.unit}</div>
      </div>
      <div class="sparkline">
        ${normalizeBars(metric.series).map((height) => `<div style="height:${height}%"></div>`).join("")}
      </div>
    </div>
  `).join("");

  renderList("recentLogs", observability.recent_logs, (line) => `<li>${line}</li>`);
  renderList("alertTimeline", observability.alert_timeline, (item) => `<li><strong>${item.time}</strong> · ${item.event}</li>`);
  renderList("recentDeployments", incident.recent_deployments, (item) => `
    <li>
      <strong>${item.time} · ${item.service}</strong><br>
      ${item.version} · ${item.change}
    </li>
  `);
  renderList("similarIncidents", incident.similar_past_incidents, (item) => `
    <li>
      <a class="inline-link" href="incident?nexus_incident_id=${encodeURIComponent(item.id)}"><strong>${item.id}</strong></a><br>
      ${item.summary}<br>
      <span class="section-note">Historical success rate ${Math.round(item.success_rate * 100)}%</span>
    </li>
  `);
  renderList("evidenceProvenance", observability.evidence_sources || [], (item) => `
    <li>
      <strong>${item.source} · ${item.signal}</strong><br>
      ${item.summary}<br>
      <span class="section-note">${item.detail} · ${item.count} item(s)</span>
    </li>
  `);

  document.getElementById("sentinelConfidence").textContent = percent(classification.confidence);
  document.getElementById("sentinelProgress").style.width = percent(classification.confidence);
  document.getElementById("sentinelReasoning").textContent = classification.reasoning;
  document.getElementById("sentinelBreakdown").innerHTML = Object.entries(classification.confidence_breakdown)
    .map(([key, value]) => `<span>${key}: ${percent(value)}</span>`)
    .join("");
  renderList("sentinelEvidence", classification.evidence, (item) => `<li>${item}</li>`);

  document.getElementById("prismConfidence").textContent = percent(diagnosis.confidence);
  document.getElementById("prismProgress").style.width = percent(diagnosis.confidence);
  document.getElementById("prismReasoning").textContent = diagnosis.reasoning;
  document.getElementById("prismCorrelation").textContent = diagnosis.correlation_analysis;
  renderList("prismLogs", diagnosis.supporting_logs, (item) => `<li>${item}</li>`);

  const forgeConfidence = runbook.candidate_fixes.length
    ? Math.max(...runbook.candidate_fixes.map((item) => item.success_rate))
    : 0;
  document.getElementById("forgeConfidence").textContent = percent(forgeConfidence);
  document.getElementById("forgeProgress").style.width = percent(forgeConfidence);
  document.getElementById("forgeReasoning").textContent = runbook.reasoning;
  document.getElementById("forgeLogic").textContent = runbook.selection_logic;
  renderList("forgeFixes", runbook.candidate_fixes, (item) => `
    <li>
      <strong>${item.action}</strong><br>
      <span class="section-note">Historical success rate ${Math.round(item.success_rate * 100)}%</span>
    </li>
  `);

  document.getElementById("guardianConfidence").textContent = percent(guardian.confidence);
  document.getElementById("guardianProgress").style.width = percent(guardian.confidence);
  document.getElementById("guardianReasoning").textContent = guardian.reasoning;
  renderList("guardianChecks", guardian.safety_checks, (item) => `<li>${item}</li>`);
  renderList(
    "guardianViolations",
    guardian.policy_violations.length ? guardian.policy_violations : ["No policy violations detected."],
    (item) => `<li>${item}</li>`
  );

  renderWorkflowTimeline(workflow, incident);
  renderAgentFlow(data);

  document.getElementById("resultBanner").innerHTML = `
    <strong>${incident.id} resolved in simulation.</strong><br>
    Guardian decision ${guardian.decision.toUpperCase()} with ${Math.round(guardian.confidence * 100)}% confidence. Execution time ${data.execution_time_ms}ms.
  `;

  animateAgentFlow();
}

function getIncidentId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("incident_id") || params.get("nexus_incident_id") || "INC001";
}

window.addEventListener("load", async () => {
  const incidentId = getIncidentId();
  document.querySelectorAll(".agent-card").forEach((card) => card.classList.add("working"));
  await sleep(120);

  try {
    const [data, status, auditLogs] = await Promise.all([
      loadIncident(incidentId),
      fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/status`),
      fetchAuthedJson(`/api/v1/audit-logs/${encodeURIComponent(incidentId)}`),
    ]);
    renderIncident(data);
    renderStatusPanel(status);
    renderAuditSummary(auditLogs);
    renderAuditTrail(auditLogs);

    const executeButton = document.getElementById("executeIncidentBtn");
    executeButton.addEventListener("click", async () => {
      const resultBanner = document.getElementById("executionResult");
      resultBanner.textContent = "Submitting execution request...";
      try {
        const response = await postAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/execute`, {});
        const status = await refreshLiveSections(incidentId);
        resultBanner.textContent = `Execution ${response.status} for ${response.incident_id}. Incident status is now ${status.status}.`;
      } catch (error) {
        resultBanner.textContent = `Execution request failed: ${error.message}`;
      }
    });
  } catch (error) {
    document.getElementById("incidentTitle").textContent = "Incident unavailable";
    document.getElementById("resultBanner").textContent = `Failed to load ${incidentId}: ${error.message}`;
  }
});
