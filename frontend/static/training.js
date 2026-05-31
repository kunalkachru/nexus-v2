import { fetchAuthedJson, loadMetrics } from "./api.js";

function percent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function currency(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function barHeight(value, max) {
  return `${Math.max(10, Math.round((value / Math.max(max, 1)) * 100))}%`;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = String(value);
  }
}

function renderSummary(data) {
  setText("baselineReward", percent(data.summary.baseline_reward));
  setText("trainedReward", percent(data.summary.trained_reward));
  setText("episodeCount", String(data.summary.episode_count));
  setText("rewardImprovement", `+${Math.round((data.summary.trained_reward - data.summary.baseline_reward) * 100)}%`);
  setText("totalCost", currency(data.summary.total_cost_usd));
  setText("finalDifficulty", data.final_difficulty || "-");
  setText("avgCostPerEpisode", currency(data.summary.average_cost_per_episode));
  setText("executionTarget", `${data.summary.execution_target_seconds}s`);

  const stats = document.getElementById("agentStats");
  if (stats) {
    stats.innerHTML = [
      ["SENTINEL", data.agent_accuracy.sentinel],
      ["PRISM", data.agent_accuracy.prism],
      ["FORGE", data.agent_accuracy.forge],
      ["GUARDIAN", data.agent_accuracy.guardian],
    ]
      .map(
        ([name, value]) => `
          <div class="summary-card">
            <div class="label">${name}</div>
            <div class="value">${percent(value)}</div>
          </div>
        `
      )
      .join("");
  }
}

function renderCurves(data) {
  const rewardMax = Math.max(...data.reward_curve, 1);
  const rewardCurve = document.getElementById("rewardCurve");
  if (rewardCurve) {
    rewardCurve.innerHTML = data.reward_curve
      .map((value, index) => `<div title="Episode ${index + 1}: ${Math.round(value * 100)}%" style="height:${barHeight(value, rewardMax)}"></div>`)
      .join("");
  }
}

function renderGovernance(platform) {
  setText("platformPolicies", platform.policy_status);
  setText("platformPolicyStatus", platform.policy_status);
  setText("platformAuth", platform.webhook_auth);
  setText("platformReplayReadiness", platform.replay_readiness);
  setText("guardianReviews", platform.guardian_reviews);
  setText("artifactSnapshots", platform.training_snapshots);
  setText("learningContracts", platform.learning_contracts);
  setText("liveAuditEvents", platform.audit_events);
  setText("platformIntegrations", platform.integrations);
}

function renderAdvanced(data) {
  const latestEpisode = data.latest_episode || (data.episode_records && data.episode_records[data.episode_records.length - 1]);
  if (!latestEpisode) {
    return;
  }

  const latest = document.getElementById("latestEpisodeSummary");
  if (latest) {
    latest.innerHTML = `
      <div class="badge">Latest episode</div>
      <div class="summary-card"><div class="label">Incident</div><div class="value">${latestEpisode.incident_id}</div></div>
      <div class="summary-card"><div class="label">Difficulty</div><div class="value">${latestEpisode.difficulty}</div></div>
      <div class="summary-card"><div class="label">Reward</div><div class="value">${percent(latestEpisode.reward)}</div></div>
      <div class="summary-card"><div class="label">Cost</div><div class="value">${currency(latestEpisode.cost_usd)}</div></div>
    `;
  }

  const breakdown = document.getElementById("rewardBreakdown");
  if (breakdown) {
    breakdown.innerHTML = latestEpisode.steps
      .map((step) => `<div class="episode-step"><strong>${step.agent_name.toUpperCase()}</strong><br>${step.action}<br><span class="section-note">${percent(step.reward_contribution)}</span></div>`)
      .join("");
  }

  const episodeTable = document.getElementById("episodeTable");
  if (episodeTable) {
    episodeTable.innerHTML = `
      <thead><tr><th>Episode</th><th>Incident</th><th>Difficulty</th><th>Reward</th><th>Cost</th></tr></thead>
      <tbody>
        ${(data.episode_records || [])
          .slice(0, 8)
          .map((episode) => `<tr><td>#${episode.episode_index + 1}</td><td>${episode.incident_id}</td><td>${episode.difficulty}</td><td>${percent(episode.reward)}</td><td>${currency(episode.cost_usd)}</td></tr>`)
          .join("")}
      </tbody>
    `;
  }

  const contract = data.rl_episode_contract || latestEpisode || {};
  const evaluation = data.reward_evaluation || {};
  const episodeContract = document.getElementById("episodeContract");
  if (episodeContract) {
    episodeContract.innerHTML = `
      <div class="badge">RL-ready episode</div>
      <div class="summary-card"><div class="label">Incident</div><div class="value">${contract.observation?.incident_id || latestEpisode.incident_id}</div></div>
      <div class="summary-card"><div class="label">Priority</div><div class="value">${contract.raw_priority_label || contract.observation?.raw_priority_label || "-"}</div></div>
      <div class="summary-card"><div class="label">Workflow state</div><div class="value">${contract.observation?.workflow_state || "-"}</div></div>
    `;
  }

  const rewardEvaluation = document.getElementById("rewardEvaluation");
  if (rewardEvaluation) {
    rewardEvaluation.innerHTML = `
      <div class="badge">Reward evaluation</div>
      <div class="summary-card"><div class="label">Final reward</div><div class="value">${percent(contract.reward || latestEpisode.reward || 0)}</div></div>
      <div class="summary-card"><div class="label">Advantage</div><div class="value">${Number(contract.advantage || 0).toFixed(2)}</div></div>
      <div class="summary-card"><div class="label">Reward peak</div><div class="value">${percent(evaluation.reward_curve_peak || 0)}</div></div>
      <div class="summary-card"><div class="label">Reward delta</div><div class="value">${percent(evaluation.reward_curve_delta || 0)}</div></div>
    `;
  }

  const trajectory = document.getElementById("trajectoryTable");
  if (trajectory) {
    trajectory.innerHTML = `
      <thead><tr><th>Step</th><th>Agent</th><th>Observation digest</th><th>Reward</th><th>Log prob</th></tr></thead>
      <tbody>
        ${(latestEpisode.steps || [])
          .map((step, index) => `<tr><td>#${index + 1}</td><td>${step.agent_name.toUpperCase()}</td><td>${step.action}</td><td>${percent(step.reward_contribution)}</td><td>${Number(step.log_prob).toFixed(2)}</td></tr>`)
          .join("")}
      </tbody>
    `;
  }

  const stateMap = document.getElementById("stateMap");
  if (stateMap) {
    stateMap.innerHTML = (data.workflow_observation_states || [])
      .map((state, index) => `<article class="state-map-item"><div class="state">${String(index + 1).padStart(2, "0")} · ${state.label}</div><div class="signal">${state.state}</div><div class="signal">${state.training_signal}</div></article>`)
      .join("");
  }
}

window.addEventListener("load", async () => {
  const [trainingData, platformData] = await Promise.all([
    fetchAuthedJson("/api/v1/training/summary").catch(() => loadMetrics()),
    fetchAuthedJson("/api/v1/platform/status").catch(() => loadMetrics()),
  ]);

  renderSummary(trainingData);
  renderCurves(trainingData);
  renderGovernance(platformData.platform_status || platformData);
  renderAdvanced(trainingData);
});
