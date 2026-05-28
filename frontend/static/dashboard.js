import { loadIncident, loadMetrics } from "/static/api.js";

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function metricValue(metric) {
  return `${metric.current}${metric.unit}`;
}

function normalizeBars(series) {
  const max = Math.max(...series, 1);
  return series.map((value) => Math.max(10, Math.round((value / max) * 100)));
}

function renderList(elementId, items, renderer) {
  const element = document.getElementById(elementId);
  element.innerHTML = items.map(renderer).join("");
}

function activateCards() {
  ["sentinelCard", "prismCard", "forgeCard", "guardianCard"].forEach((id) => {
    document.getElementById(id).classList.add("active");
  });
}

function renderIncident(data) {
  const incident = data.incident;
  const observability = data.observability;
  const classification = data.classification;
  const diagnosis = data.diagnosis;
  const runbook = data.runbook;
  const guardian = data.guardian;

  document.getElementById("heroStatus").textContent = data.execution_result.toUpperCase();
  document.getElementById("heroSeverity").textContent = incident.severity;
  document.getElementById("heroGuardian").textContent = guardian.decision.toUpperCase();

  document.getElementById("incidentSummary").innerHTML = [
    ["Incident", `${incident.id} · ${incident.name}`],
    ["Detected", incident.detected_at],
    ["Duration", `${incident.duration_minutes} min`],
    ["Runbook", runbook.recommended_runbook],
  ].map(([label, value]) => `
    <div class="summary-card">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
    </div>
  `).join("");

  document.getElementById("incidentNarrative").innerHTML = `
    <div class="badge">${incident.summary}</div>
    <p class="hero-copy">Affected services include ${incident.related_services.join(", ")}. The dashboard below shows the current evidence window NEXUS uses to classify, diagnose, generate a runbook, and enforce production safety checks.</p>
  `;

  document.getElementById("servicePills").innerHTML = incident.related_services
    .map((service) => `<div class="pill">${service}</div>`)
    .join("");

  document.getElementById("metricsGrid").innerHTML = observability.metrics.map((metric) => `
    <div class="metric-card">
      <div class="metric-top">
        <div class="metric-name">${metric.name}</div>
        <div class="metric-current">${metricValue(metric)}</div>
      </div>
      <div class="sparkline">
        ${normalizeBars(metric.series).map((height) => `<div style="height:${height}%"></div>`).join("")}
      </div>
    </div>
  `).join("");

  renderList("recentLogs", observability.recent_logs, (line) => `<li>${line}</li>`);
  renderList("alertTimeline", observability.alert_timeline, (item) => `<li><strong>${item.time}</strong> · ${item.event}</li>`);
  renderList("similarIncidents", incident.similar_past_incidents, (item) => `
    <li>
      <button class="link-btn" data-similar="${item.id}">${item.id}</button><br>
      ${item.summary}<br>
      <span class="section-note">Historical success rate ${Math.round(item.success_rate * 100)}%</span>
    </li>
  `);
  renderList("recommendedRunbooks", observability.recommended_runbooks, (item) => `
    <li>
      <strong>${item.name}</strong><br>
      <span class="section-note">Historical success rate ${Math.round(item.success_rate * 100)}%</span>
    </li>
  `);
  renderList("recentDeployments", incident.recent_deployments, (item) => `
    <li>
      <strong>${item.time} · ${item.service}</strong><br>
      ${item.version} · ${item.change}
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

  document.getElementById("resultBanner").innerHTML = `
    <strong>${incident.id} resolved in simulation.</strong><br>
    Reward ${Math.round(data.reward * 100)}%, execution time ${data.execution_time_ms}ms, estimated runbook cost $${runbook.cost_usd.toFixed(2)}.
  `;

  activateCards();
}

async function renderMetrics() {
  const data = await loadMetrics();
  document.getElementById("trainingSummary").innerHTML = [
    ["Baseline Accuracy", `${Math.round(data.summary.baseline_reward * 100)}%`],
    ["Trained Accuracy", `${Math.round(data.summary.trained_reward * 100)}%`],
    ["Episodes", data.summary.episode_count],
    ["Improvement", `+${Math.round((data.summary.trained_reward - data.summary.baseline_reward) * 100)}%`],
  ].map(([label, value]) => `
    <div class="summary-card">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
    </div>
  `).join("");

  document.getElementById("rewardCurve").innerHTML = data.reward_curve
    .map((value) => `<div style="height:${Math.max(8, Math.round(value * 100))}%"></div>`)
    .join("");

  document.getElementById("agentStats").innerHTML = [
    ["SENTINEL", data.agent_accuracy.sentinel],
    ["PRISM", data.agent_accuracy.prism],
    ["FORGE", data.agent_accuracy.forge],
    ["GUARDIAN", data.agent_accuracy.guardian],
  ].map(([name, value]) => `
    <div class="summary-card">
      <div class="label">${name}</div>
      <div class="value">${Math.round(value * 100)}%</div>
    </div>
  `).join("");
}

async function runSelectedIncident(incidentId, button) {
  document.querySelectorAll(".incident-btn").forEach((node) => node.classList.remove("active"));
  button.classList.add("active");

  const status = document.getElementById("demoStatus");
  status.textContent = `Loading ${incidentId} with production-style logs, metrics, deployments, and runbook history...`;
  status.className = "status loading";

  try {
    const data = await loadIncident(incidentId);
    renderIncident(data);
    status.textContent = `${incidentId} loaded. Agent reasoning and observability context are now visible.`;
    status.className = "status success";
  } catch (error) {
    status.textContent = `Failed to load ${incidentId}: ${error.message}`;
    status.className = "status";
  }
}

window.addEventListener("load", async () => {
  try {
    await renderMetrics();
  } catch (error) {
    document.getElementById("trainingSummary").innerHTML = `
      <div class="summary-card">
        <div class="label">Metrics Error</div>
        <div class="value">${error.message}</div>
      </div>
    `;
  }

  document.querySelectorAll(".incident-btn").forEach((button) => {
    button.addEventListener("click", () => runSelectedIncident(button.dataset.incident, button));
  });

  document.getElementById("similarIncidents").addEventListener("click", (event) => {
    if (event.target.matches("[data-similar]")) {
      document.getElementById("demoStatus").textContent = `Historical reference ${event.target.dataset.similar} selected for review context.`;
      document.getElementById("demoStatus").className = "status success";
    }
  });

  const defaultButton = document.querySelector('[data-incident="INC001"]');
  if (defaultButton) {
    await runSelectedIncident("INC001", defaultButton);
  }
});
