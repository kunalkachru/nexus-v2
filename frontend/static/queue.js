import { fetchAuthedJson, loadMetrics } from "./api.js";

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = String(value);
  }
}

async function renderQueueSummary() {
  const [metrics, queue] = await Promise.all([
    loadMetrics(),
    fetchAuthedJson("/api/v1/incidents/queue"),
  ]);
  const data = metrics;
  const snapshot = data.queue_snapshot || {};
  const items = queue.items || [];

  setText("queueOpenIncidents", items.length || snapshot.open_incidents);
  setText("queueSlaAtRisk", snapshot.sla_at_risk);
  setText("queuePrimarySource", items[0]?.source_channel || snapshot.primary_source);
  setText("queueLastUpdate", items[0]?.updated_at || snapshot.last_update);
  setText("queueCurrentStage", items[0]?.current_stage || snapshot.current_stage);
  setText("queueLatestActivity", items[0]?.title || snapshot.latest_agent_activity);
  setText("queueSlaTimer", snapshot.sla_timer);
  setText("queueHighestSeverity", items[0]?.severity || snapshot.highest_severity);
  setText("queueMostRecentSource", items[0]?.source_channel || snapshot.primary_source);
  setText("queueCurrentBottleneck", snapshot.current_bottleneck);

  const openConsole = document.getElementById("queueOpenConsole");
  if (openConsole && items[0]?.nexus_incident_id) {
    openConsole.href = `incident?nexus_incident_id=${encodeURIComponent(items[0].nexus_incident_id)}`;
    openConsole.textContent = items[0].nexus_incident_id;
  }

  const queueList = document.querySelector(".queue-list");
  if (queueList && items.length) {
    queueList.innerHTML = items
      .map(
        (item) => `
          <a class="incident-btn" href="incident?nexus_incident_id=${encodeURIComponent(item.nexus_incident_id)}">
            <div class="queue-row">
              <strong>${item.nexus_incident_id} · ${item.title}</strong>
              <span class="badge">${item.severity}</span>
            </div>
            <div class="queue-meta">Stage: ${item.current_stage} · Source: ${item.source_channel} · Updated: ${item.updated_at}</div>
          </a>
        `
      )
      .join("");
  }
}

window.addEventListener("load", () => {
  renderQueueSummary().catch((error) => {
    const status = document.getElementById("queueStatus");
    if (status) {
      status.innerHTML = `<div class="badge">Live status unavailable</div><p class="hero-copy">${error.message}</p>`;
    }
  });
});
