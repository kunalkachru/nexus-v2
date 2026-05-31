import { fetchAuthedJson, postAuthedJson } from "./api.js";

const SCENARIOS = {
  api_timeout_cascade: {
    title: "API timeout cascade",
    summary: "Stress tests classification, metrics correlation, and guardrail handoff.",
    pills: ["webhook", "api-gateway", "P1", "timeout cascade"],
    payload: [
      "Source payload",
      "POST /webhooks/incident",
      "Service: api-gateway",
      "Severity: P1",
      "Symptoms: timeout spikes, retry storm, downstream saturation",
    ],
    evidence: [
      "Evidence pack",
      "P95 latency 8.5s, error rate 45.2%, retries 9x baseline",
      "Trace summaries show a cascading dependency chain",
      "Related incident: API timeout after retry budget exhaustion",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: classified a severe timeout cascade",
      "PRISM: linked retries and dependency pressure to the gateway",
      "FORGE: proposed retry-storm mitigation",
      "GUARDIAN: approved the rollback-safe path",
    ],
    outcome: [
      "Final result",
      "Execution approved and verified in the incident console",
    ],
    incidentId: "INC001",
    launchLabel: "Open API timeout console",
  },
  db_connection_pool_exhaustion: {
    title: "DB connection pool exhaustion",
    summary: "Validates diagnosis and rollback logic under saturation.",
    pills: ["manual_form", "payments", "P1", "database"],
    payload: [
      "Source payload",
      "Manual report",
      "Service: payments-api",
      "Severity: P1",
      "Symptoms: pool exhaustion, slow checkout, retry failures",
    ],
    evidence: [
      "Evidence pack",
      "Connection pool maxed at 500 with overflow exhausted",
      "Deploy event aligns with retry patch rollout",
      "Historical pattern matches prior session leak incidents",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: severity elevated to P1",
      "PRISM: linked queue saturation to leaked sessions",
      "FORGE: recommended connection reset and rollback",
      "GUARDIAN: approved after safety checks passed",
    ],
    outcome: [
      "Final result",
      "Execution approved and workflow marked learned",
    ],
    incidentId: "INC002",
    launchLabel: "Open database console",
  },
  memory_leak_after_deploy: {
    title: "Memory leak after deploy",
    summary: "Checks deployment-aware root cause and remediation selection.",
    pills: ["stream_anomaly", "worker-fleet", "P2", "deploy"],
    payload: [
      "Source payload",
      "Stream anomaly",
      "Service: worker-fleet",
      "Severity: P2",
      "Symptoms: RSS growth, eviction pressure, worker slowdown",
    ],
    evidence: [
      "Evidence pack",
      "Memory graph trends upward after deploy",
      "Logs indicate sustained object retention",
      "Deployment timeline shows a recent build change",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: classified as non-urgent but escalating",
      "PRISM: traced the leak to the new build path",
      "FORGE: recommended restart plus rollback guardrail",
      "GUARDIAN: approved with deployment scope checks",
    ],
    outcome: [
      "Final result",
      "Incident resolved and episode captured for training",
    ],
    incidentId: "INC003",
    launchLabel: "Open memory console",
  },
  redis_saturation: {
    title: "Redis saturation",
    summary: "Exercises memory growth, eviction pressure, and recovery choices.",
    pills: ["webhook", "redis", "P2", "cache"],
    payload: [
      "Source payload",
      "Webhook alert",
      "Service: redis-cache",
      "Severity: P2",
      "Symptoms: memory pressure, eviction thrash, cache misses",
    ],
    evidence: [
      "Evidence pack",
      "Cache size growth accelerates after deploy",
      "Eviction rate exceeds steady-state norm",
      "Related incidents show recurring cache growth patterns",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: confirmed cache degradation",
      "PRISM: tied pressure to workload growth and eviction policy",
      "FORGE: proposed cache trim and policy adjustment",
      "GUARDIAN: approved because rollback path remained safe",
    ],
    outcome: [
      "Final result",
      "Mitigation executed and system returned to stable state",
    ],
    incidentId: "INC004",
    launchLabel: "Open cache console",
  },
  queue_backlog_worker_stall: {
    title: "Queue backlog and worker stall",
    summary: "Confirms consumer recovery and safe remediation sequencing.",
    pills: ["batch_import", "billing", "P1", "queue"],
    payload: [
      "Source payload",
      "Batch import",
      "Service: billing-workers",
      "Severity: P1",
      "Symptoms: queue depth growth, worker stall, processing lag",
    ],
    evidence: [
      "Evidence pack",
      "Queue depth climbed above SLA threshold",
      "Worker heartbeat stalled after a deployment change",
      "Historical reference indicates retry budget pressure",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: classified as customer-impacting",
      "PRISM: correlated worker stall with queue backlog",
      "FORGE: proposed worker restart and traffic shaping",
      "GUARDIAN: approved the staged remediation",
    ],
    outcome: [
      "Final result",
      "Execution approved and recovery verified",
    ],
    incidentId: "INC005",
    launchLabel: "Open queue console",
  },
  bad_deployment_regression: {
    title: "Bad deployment regression",
    summary: "Proves rollback-first reasoning with change history context.",
    pills: ["webhook", "deployment", "P1", "rollback"],
    payload: [
      "Source payload",
      "Webhook alert",
      "Service: api-gateway",
      "Severity: P1",
      "Symptoms: regression after deployment, elevated errors, blocked checkout",
    ],
    evidence: [
      "Evidence pack",
      "Deploy event overlaps with error spike",
      "Rollback window is available and safe",
      "Historical match suggests recent change regression",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: escalated severity after regression detection",
      "PRISM: tied behavior to deployment delta",
      "FORGE: selected rollback-first remediation",
      "GUARDIAN: approved because rollback preserved safety",
    ],
    outcome: [
      "Final result",
      "Rollback executed and incident closed",
    ],
    incidentId: "INC004",
    launchLabel: "Open regression console",
  },
  certificate_expiry: {
    title: "Certificate expiry",
    summary: "Validates alerting, safety review, and operator escalation.",
    pills: ["webhook", "security", "P1", "expiry"],
    payload: [
      "Source payload",
      "Webhook alert",
      "Service: edge-gateway",
      "Severity: P1",
      "Symptoms: certificate expiry, TLS handshake failures, connection errors",
    ],
    evidence: [
      "Evidence pack",
      "Certificate expiry window is immediate",
      "Handshake failures affect all ingress traffic",
      "Historical response requires controlled replacement",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: flagged immediate customer impact",
      "PRISM: confirmed expiry as root cause",
      "FORGE: proposed cert rotation runbook",
      "GUARDIAN: approved after safety checks",
    ],
    outcome: [
      "Final result",
      "Certificate replacement path approved",
    ],
    incidentId: "INC005",
    launchLabel: "Open certificate console",
  },
  cache_explosion: {
    title: "Cache explosion",
    summary: "Shows repetitive remediation logic on a classic enterprise failure mode.",
    pills: ["webhook", "cache", "P2", "eviction"],
    payload: [
      "Source payload",
      "Webhook alert",
      "Service: redis-cache",
      "Severity: P2",
      "Symptoms: cache growth, eviction thrash, memory pressure",
    ],
    evidence: [
      "Evidence pack",
      "Cache growth exceeds stable working set",
      "Eviction policy amplifies read misses",
      "Similar incidents resolved with trim and policy tuning",
    ],
    agents: [
      "Agent outputs",
      "SENTINEL: identified cache-related degradation",
      "PRISM: tied growth to policy and workload mix",
      "FORGE: proposed trim plus policy adjustment",
      "GUARDIAN: approved the safe remediation",
    ],
    outcome: [
      "Final result",
      "Cache stabilized and service recovered",
    ],
    incidentId: "INC004",
    launchLabel: "Open cache console",
  },
};

let BACKEND_SCENARIOS = {};
let ACTIVE_SCENARIO_ID = "api_timeout_cascade";

function renderPills(items) {
  return items.map((item) => `<div class="pill">${item}</div>`).join("");
}

function renderBlock(lines) {
  return lines.join("\n");
}

function scenarioIncidentId(scenario) {
  return scenario?.incidentId || scenario?.incident_id || "INC001";
}

function scenarioLaunchLabel(scenario) {
  return scenario?.launchLabel || scenario?.launch_label || `Open ${scenarioIncidentId(scenario)} console`;
}

function setActiveScenario(card, cards) {
  const scenario = BACKEND_SCENARIOS[card.dataset.scenarioId] || SCENARIOS[card.dataset.scenarioId];
  if (!scenario) {
    return;
  }

  ACTIVE_SCENARIO_ID = card.dataset.scenarioId;

  cards.forEach((node) => node.classList.remove("active"));
  card.classList.add("active");

  document.getElementById("replayTitle").textContent = scenario.title;
  document.getElementById("replaySummary").textContent = scenario.summary;
  document.getElementById("replayPills").innerHTML = renderPills(scenario.pills);
  document.getElementById("replayPayload").textContent = renderBlock(scenario.payload);
  document.getElementById("replayEvidence").textContent = renderBlock(scenario.evidence);
  document.getElementById("replayAgents").textContent = renderBlock(scenario.agents);
  document.getElementById("replayOutcome").textContent = renderBlock(scenario.outcome);

  const launch = document.getElementById("replayLaunch");
  const incidentUrl = `incident?nexus_incident_id=${encodeURIComponent(scenarioIncidentId(scenario))}`;
  launch.href = window.NexusNavigation?.withReturnTo(incidentUrl) || incidentUrl;
  launch.textContent = scenarioLaunchLabel(scenario);
}

window.addEventListener("DOMContentLoaded", () => {
  const cards = Array.from(document.querySelectorAll(".scenario-card"));
  const status = document.getElementById("replayStatus");
  cards.forEach((card) => {
    card.addEventListener("click", () => setActiveScenario(card, cards));
  });

  const launchButtons = [
    document.getElementById("replayLaunchScenarioHero"),
    document.getElementById("replayLaunchScenario"),
  ].filter(Boolean);
  launchButtons.forEach((launchButton) => {
    launchButton.addEventListener("click", async (event) => {
      event.preventDefault();
      const scenario = BACKEND_SCENARIOS[ACTIVE_SCENARIO_ID] || SCENARIOS[ACTIVE_SCENARIO_ID];
      if (!scenario) {
        return;
      }
      if (status) {
        status.textContent = "Launching replay scenario...";
      }
      try {
        const response = await postAuthedJson(`/api/v1/replay/scenarios/${encodeURIComponent(ACTIVE_SCENARIO_ID)}/launch`, {});
        const launch = document.getElementById("replayLaunch");
        if (launch) {
          const incidentUrl = `incident?nexus_incident_id=${encodeURIComponent(response.nexus_incident_id)}`;
          launch.href = window.NexusNavigation?.withReturnTo(incidentUrl) || incidentUrl;
          launch.textContent = `Open ${response.nexus_incident_id} console`;
        }
        if (status) {
          status.textContent = `Replay launched as ${response.nexus_incident_id}. Open the incident console to inspect the live run.`;
        }
      } catch (error) {
        if (status) {
          status.textContent = `Replay launch failed: ${error.message}`;
        }
      }
    });
  });

  const defaultCard = cards.find((card) => card.dataset.scenarioId === "api_timeout_cascade") || cards[0];
  fetchAuthedJson("/api/v1/replay/scenarios")
    .then((payload) => {
      BACKEND_SCENARIOS = Object.fromEntries((payload.items || []).map((scenario) => [scenario.scenario_id, scenario]));
    })
    .catch(() => {
      BACKEND_SCENARIOS = {};
    })
    .finally(() => {
      if (defaultCard) {
        setActiveScenario(defaultCard, cards);
      }
    });
});
