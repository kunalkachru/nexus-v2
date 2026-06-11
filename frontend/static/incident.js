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

const FRESH_TRIAGE_STORAGE_KEY = "nexus.fresh_triage_incident_id";
const LAST_TRIAGE_SUMMARY_KEY = "nexus.last_triage_summary";
const RELAY_SEEN_PREFIX = "nexus.relay_seen.";
let relayRunToken = 0;
const RELAY_STAGE_META = [
  {
    banner: "SENTINEL is classifying the incident and creating the shared incident frame.",
    guardianPrompt: "Guardian is waiting for the crew to finish the first classification step.",
  },
  {
    banner: "PRISM is actively correlating evidence and can loop back if the confidence story changes.",
    guardianPrompt: "Guardian is still waiting while PRISM breaks the issue into investigation branches.",
  },
  {
    banner: "FORGE is turning the diagnosis into a concrete runbook proposal.",
    guardianPrompt: "Guardian is about to receive the proposed runbook and decide whether it is safe enough to execute.",
  },
  {
    banner: "GUARDIAN now controls the workflow and the operator must make the final safety decision.",
    guardianPrompt: "Guardian now has control. Review the runbook and choose approve, block, or request modification.",
  },
];

function percent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function titleCase(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function getCrewNodes() {
  return Array.from(document.querySelectorAll(".crew-bot"));
}

function getHandoffNodes() {
  return [
    document.getElementById("handoffSentinel"),
    document.getElementById("handoffPrism"),
    document.getElementById("handoffForge"),
    document.getElementById("handoffGuardian"),
  ].filter(Boolean);
}

function getRelayNodes() {
  return [
    document.getElementById("relaySentinel"),
    document.getElementById("relayPrism"),
    document.getElementById("relayForge"),
    document.getElementById("relayGuardian"),
  ].filter(Boolean);
}

function setRelayNodeState(index, state) {
  const labels = ["relaySentinelState", "relayPrismState", "relayForgeState", "relayGuardianState"];
  setText(labels[index], state);
}

function setRelayStep(index) {
  const crewNodes = getCrewNodes();
  const handoffNodes = getHandoffNodes();
  const relayNodes = getRelayNodes();
  crewNodes.forEach((node, nodeIndex) => {
    node.classList.toggle("crew-active", nodeIndex === index);
    node.classList.toggle("crew-complete", nodeIndex < index);
    setRelayNodeState(nodeIndex, nodeIndex < index ? "Completed" : nodeIndex === index ? "Working now" : "Waiting");
  });
  handoffNodes.forEach((node, nodeIndex) => {
    node.classList.toggle("handoff-entry-active", nodeIndex === index);
    node.classList.toggle("handoff-entry-complete", nodeIndex < index);
  });
  relayNodes.forEach((node, nodeIndex) => {
    node.classList.toggle("relay-node-active", nodeIndex === index);
    node.classList.toggle("relay-node-complete", nodeIndex < index);
  });
  setText("relayStageBanner", RELAY_STAGE_META[index]?.banner || "The crew is coordinating on the incident.");
  setText("guardianRelayPrompt", RELAY_STAGE_META[index]?.guardianPrompt || currentGuardianPrompt({ guardian: {}, execution_result: "pending" }));
}

function currentGuardianPrompt(data) {
  if (data.execution_result === "executed") {
    return "Guardian approved the runbook and the execution outcome is now visible below.";
  }
  if (String(data.guardian.decision || "").toLowerCase() === "reject") {
    return "Guardian blocked the plan. Review the decision and the policy notes below.";
  }
  if (String(data.guardian.decision || "").toLowerCase() === "request_modification") {
    return "Guardian requested a modification. Review the guardrails and adjust the runbook.";
  }
  return "Guardian now has control. Review the runbook and choose approve, block, or request modification.";
}

function updateGuardianPrompt(data) {
  setText("guardianRelayPrompt", currentGuardianPrompt(data));
}

function scrollToOutcomePanel() {
  const target = document.getElementById("resultBanner") || document.getElementById("executionResult");
  target?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function showResolvedGuardianState(data) {
  setRelayStep(3);
  setText(
    "relayStageBanner",
    data.execution_result === "executed"
      ? "Guardian approved the runbook and the incident moved into execution."
      : "Guardian is the current control point for this incident."
  );
  updateGuardianPrompt(data);
}

async function playAgentRelay(data, { focusGuardian = false, revealOutcome = false } = {}) {
  const relayToken = ++relayRunToken;
  const decision = String(data.guardian.decision || "").toLowerCase();
  const finalStep = data.execution_result === "executed" || decision === "approve" ? 3 : 3;

  for (let index = 0; index <= finalStep; index += 1) {
    if (relayToken !== relayRunToken) {
      return;
    }
    setRelayStep(index);
    await sleep(index === finalStep ? 500 : 420);
  }

  setText(
    "relayStageBanner",
    data.execution_result === "executed"
      ? "Guardian approved the runbook and the incident moved into execution."
      : "Guardian now controls the workflow and is waiting for an operator decision."
  );
  updateGuardianPrompt(data);

  if (focusGuardian) {
    document.querySelector(".guardian-gate-card")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  if (revealOutcome) {
    await sleep(250);
    if (relayToken !== relayRunToken) {
      return;
    }
    scrollToOutcomePanel();
  }
}

function isFreshTriageIncident(incidentId) {
  try {
    return window.sessionStorage.getItem(FRESH_TRIAGE_STORAGE_KEY) === incidentId;
  } catch {
    return false;
  }
}

function clearFreshTriageIncident(incidentId) {
  try {
    if (window.sessionStorage.getItem(FRESH_TRIAGE_STORAGE_KEY) === incidentId) {
      window.sessionStorage.removeItem(FRESH_TRIAGE_STORAGE_KEY);
    }
  } catch {
    // Ignore storage failures.
  }
}

function relaySeenKey(incidentId) {
  return `${RELAY_SEEN_PREFIX}${incidentId}`;
}

function hasSeenRelay(incidentId) {
  try {
    return window.sessionStorage.getItem(relaySeenKey(incidentId)) === "1";
  } catch {
    return false;
  }
}

function markRelaySeen(incidentId) {
  try {
    window.sessionStorage.setItem(relaySeenKey(incidentId), "1");
  } catch {
    // Ignore storage failures.
  }
}

function persistLastTriageSummary(data) {
  const summary = {
    incident_id: data.incident?.id,
    incident_name: data.incident?.name,
    incident_title: `${formatIncidentHandle(data.incident?.id)} · ${summarizeIncidentTitle(data.incident?.name)}`,
    guardian_decision: data.guardian?.decision,
    execution_result: data.execution_result,
    required_approval_level: data.guardian?.required_approval_level,
    live_reasoning: Boolean(data.live_reasoning),
    live_reasoning_requested: getLiveReasoningPreference(),
    live_reasoning_mode: String(data.llm_access?.mode || (data.live_reasoning ? "live" : "deterministic")),
    task_count: data.task_board?.tasks?.length || 0,
    memory_similar_count: data.memory_hits?.similar_incidents?.length || 0,
    memory_runbook_count: data.memory_hits?.runbooks?.length || 0,
    branch_completion_rate: data.orchestration?.branch_completion_rate || 0,
    runbook_summary: data.runbook?.summary || data.runbook?.recommended_runbook || "",
    runbook_reasoning: data.runbook?.selection_logic || data.runbook?.reasoning || "",
    updated_at: new Date().toISOString(),
  };
  try {
    window.localStorage.setItem(LAST_TRIAGE_SUMMARY_KEY, JSON.stringify(summary));
  } catch {
    // Ignore storage failures.
  }
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
  setText("liveReasoningState", `Live reasoning: requested ${enabled ? "ON" : "OFF"} · active OFF`);
  const button = document.getElementById("liveReasoningToggle");
  if (button) {
    button.textContent = enabled ? "Turn live reasoning off" : "Turn live reasoning on";
  }
}

function syncLiveReasoningState(data) {
  const requested = getLiveReasoningPreference();
  const active = Boolean(data.live_reasoning);
  setText("liveReasoningState", `Live reasoning: requested ${requested ? "ON" : "OFF"} · active ${active ? "ON" : "OFF"}`);
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
  const triage = data.triage_summary || {};
  setText(
    "threadSentinelCopy",
    `${data.classification.reasoning} SENTINEL turned noisy signals into one shared incident frame for ${triage.impacted_customer_path || "the affected customer path"} and routed it toward ${triage.likely_owner_team || triage.likely_owner_service || "the likely owner"}.`
  );
  setText(
    "threadPrismCopy",
    `${data.diagnosis.correlation_analysis || data.diagnosis.reasoning}${memoryCount ? ` PRISM used ${memoryCount} memory references to check whether this matched the ${triage.issue_family || "known failure"} pattern.` : ""}`
  );
  setText(
    "threadForgeCopy",
    `${data.runbook.selection_logic || data.runbook.reasoning} FORGE focused on the option that looked fastest to recover, safest to review, and easiest to roll back.`
  );
  setText(
    "threadGuardianCopy",
    `${data.guardian.reasoning}${data.guardian.risk_class ? ` Risk class: ${String(data.guardian.risk_class).toUpperCase()}.` : ""} ${data.guardian.required_approval_level ? `Approval needed: ${titleCase(data.guardian.required_approval_level)}.` : ""}`
  );
}

function renderCrew(data) {
  const triage = data.triage_summary || {};
  setText("sentinelFlowMeta", `${percent(data.classification.confidence)} confidence`);
  setText("sentinelReasoning", data.classification.reasoning);
  setText(
    "sentinelFlowTransfer",
    `SENTINEL handed PRISM a triage frame for ${triage.likely_owner_team || triage.likely_owner_service || "the likely owner"} and the ${triage.issue_family || "active issue family"}.`
  );

  setText("prismFlowMeta", `${percent(data.diagnosis.confidence)} confidence`);
  setText("prismReasoning", data.diagnosis.correlation_analysis || data.diagnosis.reasoning);
  setText("prismFlowTransfer", "PRISM broke the issue into evidence, change, and history branches before merging one diagnosis packet.");

  const forgeConfidence = data.runbook.candidate_fixes?.length
    ? Math.max(...data.runbook.candidate_fixes.map((item) => item.success_rate))
    : 0;
  setText("forgeFlowMeta", `${percent(forgeConfidence)} confidence`);
  setText("forgeReasoning", data.runbook.selection_logic || data.runbook.reasoning);
  setText("forgeFlowTransfer", "FORGE chose the recovery path that best fit the evidence, memory, and rollback posture.");

  setText("guardianFlowMeta", String(data.guardian.decision || "pending").toUpperCase());
  setText("guardianReasoning", data.guardian.reasoning);
  setText(
    "guardianFlowTransfer",
    data.guardian.required_approval_level
      ? `GUARDIAN is holding execution until ${titleCase(data.guardian.required_approval_level)} approval is satisfied.`
      : "GUARDIAN is holding the execution gate."
  );
}

function renderSummary(data) {
  const incident = data.incident;
  const triage = data.triage_summary || {};
  const decision = String(data.guardian.decision || "").toLowerCase();
  const nextStep =
    data.execution_result === "executed"
      ? "Execution completed. Review the outcome, audit trail, and training linkage for this incident."
      : decision === "reject"
        ? "Guardian blocked the plan. Review the policy notes below and choose whether to request a safer modification."
        : decision === "request_modification"
          ? "Guardian requested a modification. Review the guardrails, adjust the runbook, and resubmit."
          : "Guardian now owns the control point. Review the proposed runbook and decide whether to approve, block, or request modification.";
  setText("incidentTitle", `${formatIncidentHandle(incident.id)} · ${summarizeIncidentTitle(incident.name)}`);
  setText("incidentSubtitle", incident.summary);
  setText("incidentHeroId", formatIncidentHandle(incident.id));
  setText("incidentHeroSeverity", incident.severity);
  setText("incidentHeroGuardian", String(data.guardian.decision || "").toUpperCase());
  setText("incidentHeroExecution", String(data.execution_result || "").toUpperCase());
  setText(
    "incidentOverviewNote",
    `Detected ${incident.detected_at} via ${incident.source_channel || "webhook"} and active for ${incident.duration_minutes} minutes. Likely owner: ${triage.likely_owner_team || triage.likely_owner_service || "Platform Operations"}. Support queue: ${triage.support_queue || "Production escalation"}.`
  );
  const runtimeHint = data.replica_summary?.runtime_enablement_hint || "";
  setText("operatorNextStep", `${nextStep} ${triage.manual_relay_removed || ""}${runtimeHint ? ` ${runtimeHint}` : ""}`);
  setText(
    "liveReasoningDetail",
    data.llm_access?.message || (
      data.live_reasoning ? "Live LLM reasoning is active for this incident." : "Deterministic fallback is active for this incident."
    )
  );
  syncLiveReasoningState(data);
  syncOpenAIKeyUI(data.llm_access?.message);
  updateGuardianPrompt(data);

  const summary = document.getElementById("incidentSummary");
  if (summary) {
    summary.innerHTML = [
      ["Likely owner", triage.likely_owner_team || triage.likely_owner_service || "-"],
      ["Issue family", triage.issue_family || "-"],
      ["Customer path", triage.impacted_customer_path || "-"],
      ["Approval", titleCase(data.guardian.required_approval_level || "operator")],
      ["Proposed fix", data.structured_result?.proposed_fix || data.runbook.recommended_runbook],
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
  setText(
    "runbookExplainer",
    `${data.runbook.summary || data.runbook.recommended_runbook || "Runbook pending"} is the operator-facing recovery plan FORGE prepared from the diagnosis. Approving it means the workflow may execute that plan.`
  );
  setText(
    "runbookImpact",
    `${data.runbook.selection_logic || data.runbook.reasoning || "Waiting for runbook reasoning."} ${triage.approval_focus ? `${triage.approval_focus} ` : ""}${triage.blast_radius ? `Blast radius: ${triage.blast_radius} ` : ""}${data.guardian.rollback_readiness ? `Rollback posture: ${titleCase(data.guardian.rollback_readiness)}.` : ""}`
  );
}

function renderEnterprise(data) {
  const orchestration = data.orchestration || {};
  const tasks = data.task_board?.tasks || [];
  const memoryHits = data.memory_hits || {};
  const metrics = data.agent_metrics || {};
  const fallbackSummary = data.fallback_summary || [];
  const decision = String(data.guardian.decision || "").toLowerCase();
  const topMemory = (memoryHits.similar_incidents || [])[0];
  const triage = data.triage_summary || {};
  const replica = data.replica_summary || {};
  const trace = data.trace_summary || {};

  setText(
    "orchestrationState",
    orchestration.active_story || `State: ${String(orchestration.state || "waiting").replace(/_/g, " ")}`
  );
  setText(
    "memorySummary",
    `The crew checked ${(memoryHits.similar_incidents || []).length} similar incidents and ${(memoryHits.runbooks || []).length} runbook memories before converging on a ${triage.issue_family || "production"} fix.`
  );
  setText(
    "fallbackSummaryNote",
    fallbackSummary.length
      ? "One branch used a bounded fallback, but the orchestrator kept the incident moving with partial evidence."
      : "All branches completed without fallback for this incident."
  );
  setText(
    "collaborationLead",
    data.execution_result === "executed"
      ? "Guardian completed the governed execution handoff."
      : decision === "approve"
        ? "Guardian has approved the plan and is ready to release execution."
        : "Guardian is holding the control point while the crew’s plan is reviewed."
  );
  setText(
    "collaborationNarrative",
    `${orchestration.active_story || "The crew is assembling a shared incident story."} SENTINEL scoped the incident, PRISM investigated it in parallel branches, FORGE selected a reversible response path, and GUARDIAN decided whether the plan was safe enough to execute for ${triage.impacted_customer_path || "the affected customer path"}.`
  );
  setText(
    "collaborationConfidence",
    `Confidence comes from ${(memoryHits.similar_incidents || []).length} prior incident matches, ${(memoryHits.runbooks || []).length} runbook references, ${topMemory ? `with ${topMemory.incident_id} as the closest historical analog, ` : ""}and ${fallbackSummary.length ? "a bounded fallback path" : "a clean branch completion path"}.`
  );
  setText(
    "collaborationOutcome",
    data.execution_result === "executed"
      ? "The plan executed. Review outcome, audit trail, and training linkage next."
      : decision === "approve"
        ? "Approve the runbook to release execution, then confirm the outcome below."
        : decision === "reject"
          ? "Execution is blocked. Review the Guardian decision and request a safer plan."
          : "The crew produced a plan, but execution is still gated by Guardian policy."
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
                  <div class="workflow-step-label">${task.owner}</div>
                  <div class="workflow-step-meta">${task.title}</div>
                </div>
                <div class="badge workflow-status">${titleCase(task.status)}</div>
              </div>
              <div class="workflow-step-transfer">${task.handoff_to ? `Next: ${task.handoff_to}` : "Next: complete"}</div>
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
    (item) => `<li><strong>${item.incident_id}</strong><br>${item.summary}<br><span class="section-note">Matched at ${percent(item.similarity || 0)} · ${item.issue_family || "Historical analog"}</span>${item.match_reason ? `<br><span class="section-note">${item.match_reason}</span>` : ""}${item.prior_action ? `<br><span class="section-note">Prior action: ${item.prior_action}</span>` : ""}${item.remaining_risk ? `<br><span class="section-note">Residual risk: ${item.remaining_risk}</span>` : ""}</li>`
  );
  renderList(
    "memoryRunbooks",
    memoryHits.runbooks || [],
    (item) => `<li><strong>${item.runbook_summary}</strong><br><span class="section-note">${titleCase(item.source || "memory")} · ${percent(item.success_rate || 0)} historical success</span>${item.historical_reason ? `<br><span class="section-note">${item.historical_reason}</span>` : ""}${item.why_now_fit ? `<br><span class="section-note">${item.why_now_fit}</span>` : ""}</li>`
  );
  renderList(
    "memoryUnresolvedItems",
    memoryHits.unresolved_items || [],
    (item) => `<li><strong>${item.incident_id}</strong><br>${item.title || item.summary}<br><span class="section-note">${titleCase(item.status || "open")} · ${item.severity || "-"}</span>${item.follow_up_reason ? `<br><span class="section-note">${item.follow_up_reason}</span>` : ""}</li>`
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
            <div class="section-note">${metric.fallback_used ? "Fallback used" : `${Math.round(Number(metric.duration_ms || 0))}ms`}</div>
            <div class="section-note">${metric.handoff_to ? `Hands off to ${metric.handoff_to}` : "Final stage"}</div>
          </div>
        `
      )
      .join("");
  }

  setText("replicaSummary", replica.reasoning || "Reproduction findings are not available yet.");
  setText("replicaPack", replica.environment_pack_id || "-");
  setText("replicaStatus", titleCase(replica.reproduction_status || "not_run"));
  setText("replicaHypothesis", replica.hypothesis_supported ? "Supported" : "Not yet proven");
  setText("replicaDelta", `${replica.confidence_delta ? `${Math.round(Number(replica.confidence_delta) * 100)} pts` : "0 pts"}`);
  setText(
    "replicaBaseline",
    replica.replay_status_code !== null && replica.replay_status_code !== undefined
      ? `${replica.replay_status_code}${replica.replay_duration_ms ? ` · ${replica.replay_duration_ms}ms` : ""}`
      : "Not replayed"
  );
  setText(
    "replicaBestMitigation",
    replica.best_mitigation_action
      ? `${replica.best_mitigation_action}${replica.best_mitigation_duration_ms ? ` · ${replica.best_mitigation_duration_ms}ms` : ""}`
      : "No validated mitigation"
  );
  setText("replicaOutcome", titleCase(String(replica.best_mitigation_outcome_class || replica.baseline_outcome_class || "not_run").replace(/_/g, " ")));
  setText("replicaRuntimeHint", replica.runtime_enablement_hint || "Runtime mode details are not available for this incident yet.");
  setText("replicaComparison", replica.runtime_comparison_summary || "Runtime comparison details are not available for this incident yet.");
  if (replica.scaffold_ready && (replica.services_seen || []).length) {
    setText("replicaPack", `${replica.environment_pack_id || "-"} · ${replica.services_seen.join(", ")}`);
  }
  renderList(
    "replicaMitigations",
    (replica.tested_mitigations || []).length
      ? replica.tested_mitigations
      : [{ action: "No reproduction validation yet", result: "The case is still relying on triage and memory only." }],
    (item) =>
      `<li><strong>${item.action}${item.won ? " · selected" : ""}</strong><br>${item.result}${item.outcome_class ? `<br><span class="section-note">Runtime outcome: ${titleCase(String(item.outcome_class).replace(/_/g, " "))}</span>` : ""}${item.confidence_delta ? `<br><span class="section-note">Confidence delta: ${Math.round(Number(item.confidence_delta) * 100)} pts</span>` : ""}</li>`
  );

  setText("traceSummary", trace.reasoning || "Debugging hints are not available yet.");
  setText("traceStatus", titleCase(trace.trace_status || "not_run"));
  setText("traceConfidence", trace.confidence ? percent(trace.confidence) : "0%");
  setText("traceReplayEvidence", trace.replay_evidence_summary || "Replay evidence is not available for this incident yet.");
  setText("traceInspectionPoint", trace.inspection_point || "TRACE has not narrowed an inspect-here-first path yet.");
  setText(
    "traceDeveloperHandoff",
    trace.developer_handoff_summary
      ? `${trace.developer_handoff_summary}${trace.code_owner_team ? ` Owner: ${trace.code_owner_team}` : ""}${trace.code_owner_slug ? ` (${trace.code_owner_slug})` : ""}.`
      : "TRACE has not prepared a developer handoff packet yet."
  );
  renderList(
    "traceModules",
    (trace.suspected_modules || []).length
      ? trace.suspected_modules.map((moduleName, index) => ({
          moduleName,
          functionName: (trace.suspected_functions || [])[index] || "",
          fileName: (trace.suspected_files || [])[index] || "",
          divergence: trace.observed_divergence || "",
        }))
      : [{ moduleName: "No narrowed code path yet", functionName: "", divergence: trace.expected_flow || "TRACE has not run on this incident yet." }],
    (item) =>
      `<li><strong>${item.moduleName}</strong>${item.functionName ? `<br><span class="section-note">${item.functionName}</span>` : ""}${item.fileName ? `<br><span class="section-note">${item.fileName}</span>` : ""}${item.divergence ? `<br><span class="section-note">${item.divergence}</span>` : ""}</li>`
  );
  renderList(
    "traceAnomalies",
    (trace.state_anomalies || []).length
      ? trace.state_anomalies
      : [trace.expected_flow || "Expected flow not yet captured."],
    (item) => `<li>${item}</li>`
  );
}

function renderSourcePayload(incident) {
  const rawText = String(incident.raw_input_text || "").trim();
  setText("rawInputText", rawText || "No raw incident text captured yet.");

  const normalized = incident.normalized_evidence || {};
  setText("rawDetectedService", normalized.service || incident.related_services?.[0] || "-");
  setText("rawDetectedSeverity", normalized.severity || incident.severity || "-");
  setText("rawDetectedSignature", normalized.signature || "General incident");
  setText("rawDetectedAction", rawText ? "Open incident workspace" : "Waiting for raw input");

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

function settleRelayState(data) {
  const decision = String(data.guardian?.decision || "").toLowerCase();
  if (data.execution_result === "executed" || ["approve", "reject", "request_modification"].includes(decision)) {
    setRelayStep(3);
    setText(
      "relayStageBanner",
      data.execution_result === "executed"
        ? "Guardian approved the runbook and the incident moved into execution."
        : "Guardian is the current control point for this incident."
    );
    updateGuardianPrompt(data);
    return;
  }
  setRelayStep(3);
}

async function loadAndRenderIncident(incidentId, options = {}) {
  const [data, status, auditLogs] = await Promise.all([
    loadIncident(incidentId, options),
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
  persistLastTriageSummary(data);
  return data;
}

async function maybePlayInitialRelay(incidentId, data) {
  if (isFreshTriageIncident(incidentId)) {
    await playAgentRelay(data, { focusGuardian: true, revealOutcome: false });
    markRelaySeen(incidentId);
    clearFreshTriageIncident(incidentId);
    return;
  }

  if (incidentId.startsWith("nxs_") && !hasSeenRelay(incidentId)) {
    await playAgentRelay(data, { focusGuardian: false, revealOutcome: false });
    markRelaySeen(incidentId);
    return;
  }

  settleRelayState(data);
}

async function replayRelayForIncident(incidentId, data) {
  await playAgentRelay(data, { focusGuardian: false, revealOutcome: false });
  markRelaySeen(incidentId);
  showResolvedGuardianState(data);
}

function getIncidentId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("incident_id") || params.get("nexus_incident_id") || "INC001";
}

function isHistoryReviewMode() {
  const params = new URLSearchParams(window.location.search);
  return params.get("history_view") === "1";
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
  const historyReviewMode = isHistoryReviewMode();
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
      const refreshed = await loadAndRenderIncident(incidentId);
      markRelaySeen(incidentId);
      showResolvedGuardianState(refreshed);
      document.querySelector(".guardian-gate-card")?.scrollIntoView({ behavior: "smooth", block: "center" });
      await sleep(250);
      scrollToOutcomePanel();
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
  document.getElementById("replayRelayBtn")?.addEventListener("click", async () => {
    const button = document.getElementById("replayRelayBtn");
    if (button) {
      button.disabled = true;
    }
    try {
      const current = await loadAndRenderIncident(incidentId);
      await replayRelayForIncident(incidentId, current);
    } finally {
      if (button) {
        button.disabled = false;
      }
    }
  });

  try {
    const data = await loadAndRenderIncident(incidentId, {
      liveReasoningOverride: historyReviewMode ? "0" : undefined,
    });
    if (historyReviewMode) {
      setText(
        "liveReasoningDetail",
        "History view opens in deterministic review mode for faster loading. Turn live reasoning on again only when you want to re-run this incident with your key."
      );
      syncLiveReasoningState({ ...data, live_reasoning: false });
    }
    await maybePlayInitialRelay(incidentId, data);
  } catch (error) {
    setText("incidentTitle", "Incident unavailable");
    setText("resultBanner", `Failed to load ${incidentId}: ${error.message}`);
  }
});
