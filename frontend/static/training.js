import { fetchAuthedJson, loadMetrics } from "./api.js";

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function currency(value) {
  return `$${value.toFixed(2)}`;
}

function barHeight(value, max) {
  return `${Math.max(10, Math.round((value / Math.max(max, 1)) * 100))}%`;
}

function renderEpisodeTable(records) {
  const rows = records.slice(0, 8).map((episode) => `
    <tr data-episode="${episode.episode_index}">
      <td>#${episode.episode_index + 1}</td>
      <td><a class="inline-link" href="incident?nexus_incident_id=${encodeURIComponent(episode.incident_id)}">${episode.incident_id}</a></td>
      <td>${episode.difficulty}</td>
      <td>${percent(episode.reward)}</td>
      <td>${currency(episode.cost_usd)}</td>
    </tr>
  `).join("");

  document.getElementById("episodeTable").innerHTML = `
    <thead>
      <tr>
        <th>Episode</th>
        <th>Incident</th>
        <th>Difficulty</th>
        <th>Reward</th>
        <th>Cost</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  `;
}

function renderLatestEpisode(episode) {
  document.getElementById("latestEpisodeSummary").innerHTML = `
    <div class="badge">Episode #${episode.episode_index + 1}</div>
    <div class="summary-card">
      <div class="label">Incident</div>
      <div class="value">${episode.incident_id}</div>
    </div>
    <div class="summary-card">
      <div class="label">Difficulty</div>
      <div class="value">${episode.difficulty}</div>
    </div>
    <div class="summary-card">
      <div class="label">Reward</div>
      <div class="value">${percent(episode.reward)}</div>
    </div>
    <div class="summary-card">
      <div class="label">Cost</div>
      <div class="value">${currency(episode.cost_usd)}</div>
    </div>
    <div class="summary-card">
      <div class="label">Open console</div>
      <div class="value"><a class="inline-link" href="incident?nexus_incident_id=${encodeURIComponent(episode.incident_id)}">Open</a></div>
    </div>
  `;

  const rewardBreakdown = document.getElementById("rewardBreakdown");
  rewardBreakdown.innerHTML = episode.steps.map((step) => `
    <div class="episode-step">
      <strong>${step.agent_name.toUpperCase()}</strong><br>
      ${step.action}<br>
      <span class="section-note">Reward contribution ${percent(step.reward_contribution)}</span>
    </div>
  `).join("");
}

function renderTrajectoryTable(episode) {
  document.getElementById("trajectoryTable").innerHTML = `
    <thead>
      <tr>
        <th>Step</th>
        <th>Agent</th>
        <th>Observation digest</th>
        <th>Reward</th>
        <th>Log prob</th>
      </tr>
    </thead>
    <tbody>
      ${episode.steps.map((step, index) => `
        <tr>
          <td>#${index + 1}</td>
          <td>${step.agent_name.toUpperCase()}</td>
          <td class="trajectory-action">${step.action}</td>
          <td>${percent(step.reward_contribution)}</td>
          <td>${Number(step.log_prob).toFixed(2)}</td>
        </tr>
      `).join("")}
    </tbody>
  `;
}

function renderStateMap(states) {
  document.getElementById("stateMap").innerHTML = states.map((state, index) => `
    <article class="state-map-item">
      <div class="state">${String(index + 1).padStart(2, "0")} · ${state.label}</div>
      <div class="signal">${state.state}</div>
      <div class="signal">${state.training_signal}</div>
    </article>
  `).join("");
}

function renderCurves(data) {
  const rewardMax = Math.max(...data.reward_curve, 1);
  const costMax = Math.max(...data.cost_curve, 1);

  document.getElementById("rewardCurve").innerHTML = data.reward_curve
    .map((value, index) => `<div title="Episode ${index + 1}: ${Math.round(value * 100)}%" style="height:${barHeight(value, rewardMax)}"></div>`)
    .join("");

  document.getElementById("costCurve").innerHTML = data.cost_curve
    .map((value, index) => `<div title="Episode ${index + 1}: ${currency(value)}" style="height:${barHeight(value, costMax)}"></div>`)
    .join("");
}

function renderSummary(data) {
  document.getElementById("baselineReward").textContent = percent(data.summary.baseline_reward);
  document.getElementById("trainedReward").textContent = percent(data.summary.trained_reward);
  document.getElementById("episodeCount").textContent = String(data.summary.episode_count);
  document.getElementById("rewardImprovement").textContent = `+${Math.round((data.summary.trained_reward - data.summary.baseline_reward) * 100)}%`;
  document.getElementById("totalCost").textContent = currency(data.summary.total_cost_usd);
  document.getElementById("finalDifficulty").textContent = data.final_difficulty || "-";
  document.getElementById("avgCostPerEpisode").textContent = currency(data.summary.average_cost_per_episode);
  document.getElementById("executionTarget").textContent = `${data.summary.execution_target_seconds}s`;
  document.getElementById("liveIncidents").textContent = String(data.summary.live_incidents ?? data.live_incidents?.length ?? 0);
  document.getElementById("liveAuditEvents").textContent = String(data.summary.live_audit_events ?? 0);
  document.getElementById("artifactSnapshots").textContent = String(data.artifact_summary?.training_snapshots ?? 0);

  document.getElementById("agentStats").innerHTML = [
    ["SENTINEL", data.agent_accuracy.sentinel],
    ["PRISM", data.agent_accuracy.prism],
    ["FORGE", data.agent_accuracy.forge],
    ["GUARDIAN", data.agent_accuracy.guardian],
  ].map(([name, value]) => `
    <div class="summary-card">
      <div class="label">${name}</div>
      <div class="value">${percent(value)}</div>
    </div>
  `).join("");
}

window.addEventListener("load", async () => {
  const data = await fetchAuthedJson("/api/v1/training/summary").catch(() => loadMetrics());
  const latestEpisode = data.latest_episode || data.episode_records?.[0];

  renderSummary(data);
  renderCurves(data);
  renderEpisodeTable(data.episode_records || []);
  if (latestEpisode) {
    renderLatestEpisode(latestEpisode);
    renderTrajectoryTable(latestEpisode);
  }
  renderStateMap(data.workflow_observation_states || []);
});
