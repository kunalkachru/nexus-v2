import { fetchAuthedJson, formatIncidentHandle, loadMetrics, summarizeIncidentTitle } from "./api.js";

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = String(value);
  }
}

function setHref(id, value) {
  const element = document.getElementById(id);
  if (element && value) {
    element.href = value;
  }
}

function updateCrew(snapshot, item) {
  const incidentTitle = summarizeIncidentTitle(item?.title || "the active incident");
  setText("crewSentinelState", "Analyzing");
  setText(
    "crewSentinelTask",
    `Classifying ${incidentTitle} with evidence from ${item?.source_channel || snapshot.primary_source || "webhook"}.`
  );
  setText("crewSentinelHandoff", "Next: PRISM receives the evidence bundle.");

  setText("crewPrismState", item?.current_stage === "sentinel_classified" ? "Working" : "Waiting");
  setText(
    "crewPrismTask",
    `Tracing likely root cause from ${item?.current_stage || snapshot.current_stage || "live evidence"}.`
  );
  setText("crewPrismHandoff", "Next: FORGE receives the diagnosis packet.");

  setText("crewForgeState", "Preparing");
  setText(
    "crewForgeTask",
    snapshot.latest_agent_activity || "Preparing a rollback-safe remediation path."
  );
  setText("crewForgeHandoff", "Next: GUARDIAN reviews the runbook.");

  setText("crewGuardianState", "Governance hold");
  setText(
    "crewGuardianTask",
    `Holding execution while ${snapshot.current_bottleneck || "policy validation"} clears.`
  );
  setText("crewGuardianHandoff", "Outcome: execution or block decision.");
}

function displayIncidentHandle(item) {
  return formatIncidentHandle(item?.nexus_incident_id);
}

async function renderQueueSummary() {
  const [metrics, queue] = await Promise.all([
    loadMetrics(),
    fetchAuthedJson("/api/v1/incidents/queue"),
  ]);
  const snapshot = metrics.queue_snapshot || {};
  const items = queue.items || [];
  const lead = items[0] || null;

  setText("queueOpenIncidents", items.length || snapshot.open_incidents);
  setText("queueSlaAtRisk", snapshot.sla_at_risk);
  setText("queuePrimarySource", lead?.source_channel || snapshot.primary_source);
  setText("queueLastUpdate", lead?.updated_at || snapshot.last_update);
  setText("queueCurrentStage", lead?.current_stage || snapshot.current_stage);
  setText("queueLatestActivity", lead?.title || snapshot.latest_agent_activity);
  setText("queueSlaTimer", snapshot.sla_timer);
  setText("queueHighestSeverity", lead?.severity || snapshot.highest_severity);
  setText("queueMostRecentSource", lead?.source_channel || snapshot.primary_source);
  setText("queueCurrentBottleneck", snapshot.current_bottleneck);
  setText("queueOpenConsole", displayIncidentHandle(lead));

  const incidentHref = `incident?nexus_incident_id=${encodeURIComponent(lead?.nexus_incident_id || "INC001")}`;
  setHref("queueOpenConsoleLink", window.NexusNavigation?.withReturnTo(incidentHref) || incidentHref);
  setHref("queueOpenConsole", incidentHref);

  updateCrew(snapshot, lead);

  const queueList = document.querySelector(".queue-list");
  if (queueList && items.length) {
    queueList.innerHTML = items
      .slice(0, 5)
      .map(
        (item) => {
          const incidentUrl = `incident?nexus_incident_id=${encodeURIComponent(item.nexus_incident_id)}`;
          return `
          <a class="incident-btn" href="${window.NexusNavigation?.withReturnTo(incidentUrl) || incidentUrl}">
            <div class="queue-row">
              <strong>${displayIncidentHandle(item)} · ${summarizeIncidentTitle(item.title)}</strong>
              <span class="badge">${item.severity}</span>
            </div>
            <div class="queue-meta">Stage: ${item.current_stage} · Source: ${item.source_channel} · Updated: ${item.updated_at}</div>
          </a>
        `;
        }
      )
      .join("");
  }
}

window.addEventListener("load", () => {
  renderQueueSummary().catch((error) => {
    const status = document.getElementById("queueStatus");
    if (status) {
      status.innerHTML = `<div class="label">Live collaboration unavailable</div><div class="value">${error.message}</div>`;
    }
  });
});
