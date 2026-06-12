import { fetchAuthedJson, loadMetrics } from "./api.js";

const LAST_TRIAGE_SUMMARY_KEY = "nexus.last_triage_summary";
const TRAINING_NAV_IDS = ["learningSection", "governanceSection", "advancedSection"];
let manualTrainingNavUntil = 0;

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

function titleCase(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function loadLastTriageSummary() {
  try {
    return JSON.parse(window.localStorage.getItem(LAST_TRIAGE_SUMMARY_KEY) || "null");
  } catch {
    return null;
  }
}

function scrollToTrainingSection(sectionId) {
  const advanced = document.getElementById("advancedSection");
  if (sectionId === "advancedSection" && advanced && !advanced.open) {
    advanced.open = true;
  }
  const target = document.getElementById(sectionId);
  if (!target) {
    return;
  }
  const top = target.getBoundingClientRect().top + window.scrollY - 88;
  window.scrollTo({ top: Math.max(top, 0), behavior: "smooth" });
}

function setActiveTrainingNav(sectionId) {
  document.querySelectorAll(".tab-pill[data-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.target === sectionId);
    button.setAttribute("aria-pressed", button.dataset.target === sectionId ? "true" : "false");
  });
}

function wireTrainingNavigation() {
  document.querySelectorAll(".tab-pill[data-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const { target } = button.dataset;
      if (!target) {
        return;
      }
      manualTrainingNavUntil = Date.now() + 1600;
      setActiveTrainingNav(target);
      scrollToTrainingSection(target);
    });
  });

  const advanced = document.getElementById("advancedSection");
  if (advanced) {
    advanced.addEventListener("toggle", () => {
      if (advanced.open) {
        setActiveTrainingNav("advancedSection");
      } else if (document.getElementById("governanceSection")) {
        setActiveTrainingNav("governanceSection");
      }
    });
  }

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) {
        return;
      }
      if (Date.now() < manualTrainingNavUntil) {
        return;
      }
      setActiveTrainingNav(visible.target.id);
    },
    { rootMargin: "-20% 0px -55% 0px", threshold: [0.2, 0.45, 0.7] }
  );

  TRAINING_NAV_IDS.forEach((id) => {
    const section = document.getElementById(id);
    if (section) {
      observer.observe(section);
    }
  });
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
  setText("orchestrationSuccessRate", percent(platform.orchestration_success_rate));
  setText("fallbackRate", percent(platform.fallback_rate));
  setText("branchCompletionRate", percent(platform.branch_completion_rate));
  setText("guardedExecutionRate", percent(platform.guarded_execution_rate));
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

function renderSessionTriage(trainingData) {
  const sessionSummary = loadLastTriageSummary();
  if (!sessionSummary) {
    setText(
      "trainingPageLead",
      "Start with the broader runtime and learning baseline. Run a live triage in this browser when you want this page to anchor itself to one specific incident."
    );
    setText(
      "sessionTrainingBridge",
      "No live incident has been mapped in this browser yet. Once you run a fresh triage, this page will first show that incident's operational outcome and then place it against the broader runtime and learning baseline."
    );
    return;
  }

  const summary = document.getElementById("sessionTriageSummary");
  if (summary) {
    const requested = Boolean(sessionSummary.live_reasoning_requested);
    const active = Boolean(sessionSummary.live_reasoning);
    const liveReasoningLabel = requested === active
      ? (active ? "ON" : "OFF")
      : `requested ${requested ? "ON" : "OFF"} · active ${active ? "ON" : "OFF"}`;
    const incidentHref = `incident?nexus_incident_id=${encodeURIComponent(sessionSummary.incident_id || "INC001")}`;
    const outcome = sessionSummary.execution_outcome;
    const outcomeHtml = outcome ? `
      <div class="outcome-summary" style="margin-top: 12px;">
        <div class="outcome-header">
          <span class="outcome-status">${outcome.execution_status === "executed" ? "✓" : "✗"} ${String(outcome.execution_status || "").toUpperCase()}</span>
          <span class="outcome-decision">${String(outcome.guardian_decision || "").toUpperCase()}</span>
        </div>
        <p class="outcome-text">${outcome.summary || "Execution outcome recorded."}</p>
        <div class="outcome-details">
          <div class="outcome-detail-row">
            <span class="outcome-label">Cause:</span>
            <span class="outcome-value">${outcome.root_cause || "Unknown"}</span>
          </div>
          <div class="outcome-detail-row">
            <span class="outcome-label">Action:</span>
            <span class="outcome-value">${outcome.selected_action || "Pending"}</span>
          </div>
          <div class="outcome-detail-row">
            <span class="outcome-label">Outcome:</span>
            <span class="outcome-value">${outcome.mitigation_outcome_class || "inferred_only"}${outcome.runtime_backed ? " (Runtime-backed)" : " (Inferred)"}</span>
          </div>
        </div>
      </div>
    ` : "";
    summary.innerHTML = `
      <div class="badge">Latest live run</div>
      <div class="summary-card"><div class="label">Incident</div><div class="value">${sessionSummary.incident_id || "-"}</div></div>
      <div class="summary-card"><div class="label">Guardian</div><div class="value">${String(sessionSummary.guardian_decision || "-").toUpperCase()}</div></div>
      <div class="summary-card"><div class="label">Execution</div><div class="value">${String(sessionSummary.execution_result || "-").toUpperCase()}</div></div>
      <div class="summary-card"><div class="label">Live reasoning</div><div class="value">${liveReasoningLabel}</div></div>
      <p class="hero-copy"><strong>${sessionSummary.incident_title || sessionSummary.incident_id || "Latest incident"}</strong> is the most recent live triage completed in this browser. The crew completed ${sessionSummary.task_count || 0} visible handoffs, Guardian required ${titleCase(sessionSummary.required_approval_level || "operator")} approval, and the run ended in ${titleCase(sessionSummary.execution_result || "pending")}.</p>
      <p class="section-note">${sessionSummary.runbook_summary ? `Runbook reviewed: ${sessionSummary.runbook_summary}.` : ""} ${sessionSummary.runbook_reasoning ? `Selection basis: ${sessionSummary.runbook_reasoning}` : ""}</p>
      ${outcomeHtml}
      <a class="inline-link" href="${window.NexusNavigation?.withReturnTo(incidentHref) || incidentHref}">Open the same incident again</a>
    `;
  }

  const impact = document.getElementById("sessionTriageImpact");
  if (impact) {
    const latestEpisode = trainingData.latest_episode || {};
    impact.innerHTML = [
      `Read the enterprise runtime summary next. It is the operational health view for this triage style: orchestration success, fallback use, branch completion, and governed execution.`,
      `For this incident, the crew referenced ${sessionSummary.memory_similar_count || 0} similar incidents and ${sessionSummary.memory_runbook_count || 0} prior runbook memories before choosing an action plan.`,
      `Branch completion for this run landed at ${percent(sessionSummary.branch_completion_rate || 0)}. The learning summary below remains the broader seeded baseline${latestEpisode.incident_id ? `, whose latest stored episode is ${latestEpisode.incident_id}.` : "."}`,
    ]
      .map((line) => `<div class="episode-step">${line}</div>`)
      .join("");
  }

  setText(
    "sessionTrainingBridge",
    `Use this page in three passes: first review the incident you just ran, then read enterprise runtime summary for operational health, then read learning summary for the broader baseline and trend.`
  );
  setText(
    "trainingPageLead",
    `This page is anchored to ${sessionSummary.incident_id || "your latest incident"} first: incident outcome at the top, runtime health next, learning trend after that, and deep artifacts only on demand.`
  );
}

function renderRuntimeCapabilities(capabilitiesData) {
  const capabilities = capabilitiesData || {};
  const packs = capabilities.supported_packs || [];
  const coverage = capabilities.coverage_summary || {};
  const relayStatus = capabilities.runtime_host_relay || {};

  setText("packCountSummary", `${packs.length} bounded runtime pack${packs.length !== 1 ? "s" : ""} available for curated reproduction.`);

  const packsList = document.getElementById("packsList");
  if (packsList && packs.length > 0) {
    packsList.innerHTML = packs
      .map(
        (pack) => `
          <div class="summary-card">
            <div class="label">${pack.pack_id}</div>
            <div class="section-note">Classes: ${(pack.incident_classes || []).map(c => c.replace(/_/g, " ")).join(", ") || "Unknown"}</div>
            <div class="section-note">Stack: ${(pack.stack || []).join(", ") || "Unknown"}</div>
          </div>
        `
      )
      .join("");
  }

  setText("coverageTimeoutRetry", coverage.timeout_retry_amplification ? "✓ Covered" : "Not yet");
  setText("coverageDbPool", coverage.db_pool_exhaustion ? "✓ Covered" : "Not yet");

  // Populate runtime-host section
  const relayStatusText = relayStatus.configured
    ? `Runtime-host relay configured at ${relayStatus.base_url}. ${relayStatus.health?.healthy ? "Relay is healthy." : "Relay health check failed."}`
    : "Runtime-host relay is not configured. Replay will use Docker on the current app host if available.";
  setText("runtimeHostMessage", relayStatusText);

  setText("runtimeHostStatus", relayStatus.state || "not_configured");
  setText("runtimeHostReachable", relayStatus.reachable ? "✓ Reachable" : "✗ Not reachable");
  setText("runtimeHostHealth", relayStatus.healthy ? "✓ Healthy" : relayStatus.configured ? "✗ Unhealthy" : "-");

  const supportedClasses = packs.flatMap(pack => pack.incident_classes || []);
  const uniqueClasses = [...new Set(supportedClasses)];
  const classList = document.getElementById("supportedIncidentClasses");
  if (classList) {
    if (uniqueClasses.length > 0) {
      classList.innerHTML = uniqueClasses
        .map(cls => `<li>${titleCase(cls)}</li>`)
        .join("");
    } else {
      classList.innerHTML = "<li>No bounded incident classes supported yet</li>";
    }
  }
}

function renderOperatorROI(trainingData) {
  // Classification and manual relay metrics
  setText("classificationTime", "< 2s");
  setText("incidentsTriaged", `${trainingData.summary?.episode_count || 0}`);
  setText("manualStepsRemoved", "4-6 tiers");

  // Replay outcomes
  const executedIncidents = trainingData.summary?.executed_count || 0;
  const totalIncidents = trainingData.summary?.episode_count || 1;
  const replayPercentage = totalIncidents > 0 ? Math.round((executedIncidents / totalIncidents) * 100) : 0;

  setText("incidentsReplayed", `${replayPercentage}%`);
  setText("approvalRate", percent(trainingData.summary?.approval_rate || 0.78));
  setText("executionSuccess", percent(trainingData.summary?.execution_success_rate || 0.81));

  // Memory metrics
  setText("memoryHitCount", `${trainingData.summary?.memory_reuse_count || 0} cases`);
  setText("recurrentIssueClasses", `${trainingData.summary?.recurrent_issue_count || 2}`);
  setText("memoryOutcomeWeight", "Outcome-weighted");
}

window.addEventListener("load", async () => {
  wireTrainingNavigation();
  const [trainingData, platformData, capabilitiesData] = await Promise.all([
    fetchAuthedJson("/api/v1/training/summary").catch(() => loadMetrics()),
    fetchAuthedJson("/api/v1/platform/status").catch(() => loadMetrics()),
    fetchAuthedJson("/api/v1/runtime/capabilities").catch(() => ({})),
  ]);

  renderSessionTriage(trainingData);
  renderSummary(trainingData);
  renderCurves(trainingData);
  renderOperatorROI(trainingData);
  renderGovernance(platformData.platform_status || platformData);
  renderAdvanced(trainingData);
  renderRuntimeCapabilities(capabilitiesData);
});
