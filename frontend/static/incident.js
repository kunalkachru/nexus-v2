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
const DEMO_BUNDLE_CONTEXT_PREFIX = "nexus.demo_bundle_context.";
const PENDING_INCIDENT_LAUNCH_PREFIX = "nexus.pending_incident_launch.";
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

function downloadTextFile(text, filename) {
  const blob = new Blob([text], { type: "text/markdown" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

function formatTimestamp(value) {
  if (!value) {
    return "Unknown time";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString();
}

function demoBundleContextKey(incidentId) {
  return `${DEMO_BUNDLE_CONTEXT_PREFIX}${incidentId}`;
}

function pendingIncidentLaunchKey(incidentId) {
  return `${PENDING_INCIDENT_LAUNCH_PREFIX}${incidentId}`;
}

function readDemoBundleContext(incidentId) {
  if (!incidentId) {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(demoBundleContextKey(incidentId));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function readPendingIncidentLaunch(incidentId) {
  if (!incidentId) {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(pendingIncidentLaunchKey(incidentId));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearPendingIncidentLaunch(incidentId) {
  if (!incidentId) {
    return;
  }
  try {
    window.sessionStorage.removeItem(pendingIncidentLaunchKey(incidentId));
  } catch {
    // Ignore storage failures.
  }
}

function hasFreshLaunchFlag() {
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get("fresh_launch") === "1";
  } catch {
    return false;
  }
}

function clearFreshLaunchFlag() {
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("fresh_launch")) {
      return;
    }
    url.searchParams.delete("fresh_launch");
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  } catch {
    // Ignore URL rewrite failures.
  }
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
    document.getElementById("relayReplica"),
    document.getElementById("relayTrace"),
    document.getElementById("relayForge"),
    document.getElementById("relayGuardian"),
  ].filter(Boolean);
}

function setRelayNodeState(index, state) {
  const labels = ["relaySentinelState", "relayPrismState", "relayReplicaState", "relayTraceState", "relayForgeState", "relayGuardianState"];
  const progressLabels = ["agentProgressSentinel", "agentProgressPrism", "agentProgressReplica", "agentProgressTrace", "agentProgressForge", "agentProgressGuardian"];
  setText(labels[index], state);
  // Also update the Agent Progress card in first viewport
  if (progressLabels[index]) {
    setText(progressLabels[index], state);
  }
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

function showFreshIntakeLanding(data) {
  const demoOrigin = readDemoBundleContext(data?.incident?.id);
  settleRelayState(data);
  setText(
    "relayStageBanner",
    demoOrigin
      ? `Fresh intake from ${demoOrigin.title} loaded. Start at the incident summary first, then replay the handoff only if you want to inspect the crew transition.`
      : "Fresh intake loaded. Start at the incident summary first, then replay the handoff only if you want to inspect the crew transition."
  );
  setText(
    "guardianRelayPrompt",
    "Guardian already has the prepared packet. Review the top summary now, or use Replay handoff when you want to watch the bounded specialist sequence."
  );
  setText(
    "operatorNextStep",
    demoOrigin?.next_step
      ? `Review the incident summary and the proposed action first. ${demoOrigin.next_step}`
      : "Review the incident summary and the proposed action first. Replay handoff is optional and no longer interrupts the landing view."
  );
  setText(
    "collaborationOutcome",
    data.execution_result === "executed"
      ? "Execution already completed. Stay on the summary first, then inspect outcome and audit evidence below."
      : "You are landing on the top-level incident brief first. Replay handoff is available if you want to inspect how the crew reached this packet."
  );
  window.scrollTo({ top: 0, behavior: "auto" });
}

function renderPendingIncidentLaunch(incidentId) {
  const pending = readPendingIncidentLaunch(incidentId);
  if (!pending && !hasFreshLaunchFlag()) {
    return null;
  }
  const incidentHandle = formatIncidentHandle(incidentId);
  const bundleLabel = pending?.bundle_title ? `${pending.bundle_title} · ` : "";
  window.NexusNavigation?.beginRouteTransition?.("Preparing incident brief...");
  setText("incidentTitle", `${incidentHandle} · preparing fresh brief`);
  setText("incidentSubtitle", "Fresh intake captured. NEXUS is assembling the top incident brief before any deeper relay detail appears.");
  setText("incidentHeroId", incidentHandle);
  setText("incidentHeroSeverity", pending?.severity || "PENDING");
  setText("incidentHeroGuardian", "PENDING");
  setText("incidentHeroExecution", "PENDING");
  setText("incidentOverviewNote", `${bundleLabel}${pending?.service || "Fresh intake"} is being shaped into a bounded investigation packet now.`);
  setText("liveReasoningDetail", "Hydrating the fresh incident workspace. The operator-first brief will appear before deeper relay detail.");
  setText("operatorNextStep", pending?.bundle_next_step || "Hold on while NEXUS loads the incident brief, then start at the top summary before inspecting replay or TRACE.");
  setText("relayStageBanner", "Fresh intake captured. Preparing the top incident brief first so the landing page reads clearly.");
  setText("guardianRelayPrompt", "Guardian is waiting for the prepared packet. The fresh incident will open at the top summary before any deeper replay detail.");
  setText("collaborationLead", "Hydrating fresh incident brief.");
  setText("collaborationNarrative", `${incidentHandle} is loading from raw intake. The first render will prioritize the incident summary, support posture, and next operator action.`);
  setText("collaborationOutcome", "The handoff replay remains available, but it should not interrupt the first landing read.");
  setText("resultBanner", `${incidentHandle} · OPENING WORKSPACE`);
  return pending;
}

function persistLastTriageSummary(data) {
  const qualityEvaluation = data.quality_evaluation || null;
  const summary = {
    incident_id: data.incident?.id,
    incident_name: data.incident?.name,
    incident_title: `${formatIncidentHandle(data.incident?.id)} · ${summarizeIncidentTitle(data.incident?.name)}`,
    guardian_decision: data.guardian?.decision,
    execution_result: data.execution_result,
    execution_outcome: data.execution_outcome || null,
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
    quality_evaluation: qualityEvaluation,
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

function ensureReplicaHypothesisPacket() {
  if (document.getElementById("replicaHypothesisSummary")) {
    return;
  }
  const replayActions = document.querySelector(".shell-actions");
  if (!replayActions || !replayActions.parentElement) {
    return;
  }
  const wrapper = document.createElement("div");
  wrapper.id = "replicaHypothesisPacket";
  wrapper.innerHTML = `
    <p class="section-label">Replica hypothesis packet</p>
    <p class="section-note" id="replicaHypothesisSummary">REPLICA will describe the bounded environment hypothesis here once the packet loads.</p>
    <ul class="simple-list" id="replicaHypothesisChecks"></ul>
  `;
  replayActions.insertAdjacentElement("beforebegin", wrapper);
}

function ensureTraceCodePacket() {
  if (document.getElementById("traceStackSummary")) {
    return;
  }
  const traceModules = document.getElementById("traceModules");
  if (!traceModules || !traceModules.parentElement) {
    return;
  }
  const wrapper = document.createElement("div");
  wrapper.id = "traceCodePacket";
  wrapper.innerHTML = `
    <p class="section-label">Trace-to-code packet</p>
    <p class="section-note" id="traceStackSummary">TRACE will summarize the bounded stack path here once the packet loads.</p>
    <p class="section-note" id="traceFailureBoundary">TRACE will describe the failure boundary here once the packet loads.</p>
    <p class="section-note" id="traceRuntimeClue">TRACE will attach the runtime clue here once the packet loads.</p>
    <ul class="simple-list" id="traceStackPath"></ul>
  `;
  traceModules.insertAdjacentElement("beforebegin", wrapper);
}

function ensureMitigationLadderPacket() {
  if (document.getElementById("replicaMitigationLadderSummary")) {
    return;
  }
  const mitigationsList = document.getElementById("replicaMitigations");
  if (!mitigationsList || !mitigationsList.parentElement) {
    return;
  }
  const wrapper = document.createElement("div");
  wrapper.id = "replicaMitigationLadderPacket";
  wrapper.innerHTML = `
    <p class="section-label">Mitigation ladder</p>
    <p class="section-note" id="replicaMitigationLadderSummary">FORGE will summarize the bounded mitigation ladder here once the packet loads.</p>
    <ul class="simple-list" id="replicaMitigationLadderSteps"></ul>
  `;
  mitigationsList.insertAdjacentElement("beforebegin", wrapper);
}

function ensureDebuggerPacket() {
  if (document.getElementById("traceDebuggerSummary")) {
    return;
  }
  const traceAnomalies = document.getElementById("traceAnomalies");
  if (!traceAnomalies || !traceAnomalies.parentElement) {
    return;
  }
  const wrapper = document.createElement("div");
  wrapper.id = "traceDebuggerPacket";
  wrapper.innerHTML = `
    <p class="section-label">Bounded debugger packet</p>
    <p class="section-note" id="traceDebuggerSummary">TRACE will surface the bounded debugger packet here once it is available.</p>
    <ul class="simple-list" id="traceDebuggerChecks"></ul>
  `;
  traceAnomalies.insertAdjacentElement("afterend", wrapper);
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

function renderDemoOriginContext(incidentId) {
  const card = document.getElementById("demoOriginCard");
  const context = readDemoBundleContext(incidentId);
  if (!card) {
    return null;
  }
  if (!context) {
    card.hidden = true;
    return null;
  }
  card.hidden = false;
  setText("demoOriginTitle", context.title || "Fresh incident demo context");
  setText("demoOriginProof", context.proof || "This incident originated from a curated demo bundle.");
  setText("demoOriginFamily", context.family || "-");
  setText("demoOriginOwner", context.likely_owner || "-");
  setText("demoOriginNextStep", context.next_step || "Review the incident summary first, then inspect the bounded runtime or TRACE evidence.");
  return context;
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

function renderHandoffFlow(data) {
  const handoff = data.handoff_flow || {};
  const replay = window.__nexusHandoffReplayState || null;
  const events = Array.isArray(handoff.events) ? handoff.events : [];
  const replayActive = replay && Number.isInteger(replay.currentStep) && replay.currentStep >= 0 && replay.currentStep < events.length;
  const activeEvent = replayActive ? events[replay.currentStep] : null;
  const nextReplayEvent = replayActive ? events[replay.currentStep + 1] : null;
  const owner = String(activeEvent?.to || handoff.current_owner || "-");
  const previousOwner = String(activeEvent?.from || handoff.previous_owner || "-");
  const nextOwner = String(nextReplayEvent?.to || handoff.next_owner || "-");
  const transferReason = String(activeEvent?.reason || activeEvent?.title || handoff.transfer_reason || "Handoff in progress");

  setText("handoffCurrentOwner", owner);
  setText("handoffPreviousOwner", previousOwner);
  setText("handoffNextOwner", nextOwner);
  setText("handoffTransferReason", transferReason);
  setText(
    "handoffCurrentOwnerCaption",
    replayActive
      ? `${owner} owns the case at this replay step after receiving the packet from ${previousOwner}.`
      : `${owner} is the active relay owner right now. ${owner === "REPLICA" || owner === "TRACE" ? "Its contribution remains bounded to the current supported packs and outage families." : "Review its packet, then decide whether to inspect deeper technical detail."}`
  );

  const ownerNode = document.getElementById("handoffCurrentOwner");
  if (ownerNode) {
    ownerNode.className = "handoff-owner";
    ownerNode.setAttribute("data-owner", owner.toLowerCase());
  }

  const agentMap = {
    "SENTINEL": 0,
    "PRISM": 1,
    "REPLICA": 2,
    "TRACE": 3,
    "FORGE": 4,
    "GUARDIAN": 5,
  };

  const agentIndex = agentMap[owner] || -1;
  const relayNodes = getRelayNodes();
  relayNodes.forEach((node, index) => {
    node.classList.remove("relay-node-active", "relay-node-complete", "relay-node-waiting");
    if (index < agentIndex) {
      node.classList.add("relay-node-complete");
    } else if (index === agentIndex) {
      node.classList.add("relay-node-active");
    } else {
      node.classList.add("relay-node-waiting");
    }
  });

  const receivedPacketEvent = replayActive
    ? activeEvent
    : [...events].reverse().find((e) => e.to === owner && e.event_type === "packet_emitted");
  const emittedPacketEvent = replayActive
    ? nextReplayEvent
    : [...events].reverse().find((e) => e.from === owner && e.event_type === "packet_emitted");

  if (receivedPacketEvent && receivedPacketEvent.packet) {
    const packet = receivedPacketEvent.packet;
    setText("handoffReceivedPacketTitle", String(packet.packet_type || "packet"));
    setText(
      "handoffReceivedPacketMeta",
      `${receivedPacketEvent.from || "Unknown"} → ${receivedPacketEvent.to || owner} · ${titleCase(receivedPacketEvent.status || "recorded")}`
    );
    setText(
      "handoffReceivedPacketSummary",
      `This is what ${receivedPacketEvent.from || "the previous agent"} handed to ${receivedPacketEvent.to || owner}. ${String(packet.summary || "")}`.trim()
    );
    const fieldsContainer = document.getElementById("handoffReceivedPacketFields");
    if (fieldsContainer && Array.isArray(packet.fields)) {
      fieldsContainer.innerHTML = packet.fields
        .map(
          (field) => `<div class="packet-field"><div class="packet-field-label">${field.label || ""}</div><div class="packet-field-value">${field.value || ""}</div></div>`
        )
        .join("");
    }
  } else {
    setText("handoffReceivedPacketTitle", "No packet yet");
    setText("handoffReceivedPacketMeta", "No inbound handoff yet");
    setText("handoffReceivedPacketSummary", "The current owner has not received a visible packet yet.");
    document.getElementById("handoffReceivedPacketFields").innerHTML = "";
  }

  if (emittedPacketEvent && emittedPacketEvent.packet) {
    const packet = emittedPacketEvent.packet;
    setText("handoffEmittedPacketTitle", String(packet.packet_type || "packet"));
    setText(
      "handoffEmittedPacketMeta",
      `${emittedPacketEvent.from || owner} → ${emittedPacketEvent.to || "Unknown"} · ${titleCase(emittedPacketEvent.status || "planned")}`
    );
    setText(
      "handoffEmittedPacketSummary",
      replayActive
        ? `If you advance replay, ${emittedPacketEvent.from || owner} will hand this to ${emittedPacketEvent.to || "the next owner"}. ${String(packet.summary || "")}`.trim()
        : `This is the next responsibility transfer from ${emittedPacketEvent.from || owner} to ${emittedPacketEvent.to || "the next owner"}. ${String(packet.summary || "")}`.trim()
    );
    const fieldsContainer = document.getElementById("handoffEmittedPacketFields");
    if (fieldsContainer && Array.isArray(packet.fields)) {
      fieldsContainer.innerHTML = packet.fields
        .map(
          (field) => `<div class="packet-field"><div class="packet-field-label">${field.label || ""}</div><div class="packet-field-value">${field.value || ""}</div></div>`
        )
        .join("");
    }
  } else {
    setText("handoffEmittedPacketTitle", "No packet yet");
    setText("handoffEmittedPacketMeta", "No outbound handoff yet");
    setText("handoffEmittedPacketSummary", `${owner} does not have another visible handoff after this point.`);
    document.getElementById("handoffEmittedPacketFields").innerHTML = "";
  }

  const ledgerContainer = document.getElementById("handoffLedger");
  if (ledgerContainer && Array.isArray(events)) {
    ledgerContainer.innerHTML = events
      .map(
        (event, index) => {
          const isCurrentEvent = replayActive ? replay.currentStep === index : emittedPacketEvent && emittedPacketEvent.id === event.id;
          return `<div class="ledger-entry${isCurrentEvent ? " active" : ""}">
          <div class="ledger-entry-header">
            <div>${event.from || "Unknown"}</div>
            <div class="ledger-entry-arrow">→</div>
            <div>${event.to || "Unknown"}</div>
            <div class="ledger-entry-status">${event.status || "pending"}</div>
          </div>
          <div class="ledger-entry-reason">${event.reason || event.title || ""}${event.packet?.summary ? ` ${event.packet.summary}` : ""}</div>
        </div>`;
        }
      )
      .join("");
  }
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

  setText("replicaFlowMeta", "Reproduction ready");
  const replica = data.replica_summary || {};
  setText("replicaReasoning", replica.reasoning || "Awaiting sandbox validation.");
  setText("replicaFlowTransfer", "REPLICA validates the diagnosis in a bounded sandbox environment.");

  setText("traceFlowMeta", "Debugging ready");
  const trace = data.trace_summary || {};
  setText("traceReasoning", trace.reasoning || "Awaiting code path inspection.");
  setText("traceFlowTransfer", "TRACE narrows the likely failing path in the codebase.");

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
  const demoOrigin = renderDemoOriginContext(incident.id);
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
  const tenantSupport = data.tenant_support || {};
  const supportState = data.incident?.support_state || tenantSupport.support_state || "-";
  const downgradeGuidance = supportState === "unsupported" || supportState === "inference-first"
    ? ` ⚠ Support coverage note: ${tenantSupport.downgrade_guidance || ""}`
    : "";
  setText(
    "incidentOverviewNote",
    `Detected ${incident.detected_at} via ${incident.source_channel || "webhook"} and active for ${incident.duration_minutes} minutes. Likely owner: ${triage.likely_owner_team || triage.likely_owner_service || "Platform Operations"}. Support queue: ${triage.support_queue || "Production escalation"}.${demoOrigin ? ` Intake bundle: ${demoOrigin.title}.` : ""}${downgradeGuidance}`
  );
  const runtimeHint = data.replica_summary?.runtime_enablement_hint || "";
  setText(
    "operatorNextStep",
    `${nextStep} ${demoOrigin?.next_step || ""} ${triage.manual_relay_removed || ""}${runtimeHint ? ` ${runtimeHint}` : ""}`.trim()
  );
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
    const ownerInfo = triage.likely_owner_team || triage.likely_owner_service || "-";
    const ownerProvenance = triage.owner_provenance || triage.is_owner_tenant_mapped ?
      `${ownerInfo} (${triage.owner_provenance || "tenant-mapped"})` :
      ownerInfo;
    const supportState = data.incident?.support_state || data.tenant_support?.support_state || "-";
    const supportStateLabel = supportState === "runtime-backed" ? "✓ Runtime-backed" :
                             supportState === "inference-first" ? "◐ Inference-first" :
                             supportState === "unsupported" ? "⊘ Unsupported" :
                             "-";
    summary.innerHTML = [
      ["Likely owner", ownerProvenance],
      ["Issue family", triage.issue_family || "-"],
      ["Support coverage", supportStateLabel],
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
  const incident = data.incident || {};
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
  const runbook = data.runbook || {};
  const guardian = data.guardian || {};

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
  setText(
    "focusRecommendedAction",
    runbook.summary || runbook.recommended_runbook || "FORGE has not finalized the operator-facing action yet."
  );
  setText(
    "focusRuntimePosture",
    replica.runtime_comparison_summary || replica.runtime_provenance?.summary || replica.summary || "REPLICA has not yet confirmed runtime posture for this incident."
  );
  setText(
    "focusInspectHere",
    trace.inspection_point || trace.developer_handoff_summary || "TRACE has not yet narrowed the first debugging boundary."
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
    (item) => {
      const outcomeBadge = item.outcome_label ? `<span class="section-note" style="color: #4a90e2; font-weight: 500;">📊 ${item.outcome_label}</span>` : "";
      const recurrenceIcon = item.recurrence_indicator === "recurring" ? "🔄 Recurring pattern" : item.recurrence_status === "partial_resolution" ? "⚠️ Partially resolved" : "";
      return `<li><strong>${item.incident_id}</strong><br>${item.summary}<br><span class="section-note">Matched at ${percent(item.similarity || 0)} · Success ${percent(item.success_rate || 0)} · ${item.issue_family || "Historical analog"}</span>${outcomeBadge ? `<br>${outcomeBadge}` : ""}${recurrenceIcon ? `<br><span class="section-note" style="color: #e07856; font-weight: 500;">${recurrenceIcon}</span>` : ""}${item.match_reason ? `<br><span class="section-note">${item.match_reason}</span>` : ""}${item.prior_action ? `<br><span class="section-note">Prior action: ${item.prior_action}</span>` : ""}${item.remaining_risk ? `<br><span class="section-note">Residual risk: ${item.remaining_risk}</span>` : ""}</li>`;
    }
  );
  renderList(
    "memoryRunbooks",
    memoryHits.runbooks || [],
    (item) => {
      const outcomeBadge = item.outcome_note ? `<span class="section-note" style="color: #4a90e2; font-weight: 500;">${item.outcome_note}</span>` : "";
      return `<li><strong>${item.runbook_summary}</strong><br><span class="section-note">${titleCase(item.source || "memory")} · Success ${percent(item.success_rate || 0)}</span>${outcomeBadge ? `<br>${outcomeBadge}` : ""}${item.historical_reason ? `<br><span class="section-note">${item.historical_reason}</span>` : ""}${item.why_now_fit ? `<br><span class="section-note">${item.why_now_fit}</span>` : ""}</li>`;
    }
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
  const runtimeCapability = replica.runtime_capability || {};
  const runtimeProvenance = replica.runtime_provenance || {};
  const traceRuntimeProvenance = trace.runtime_provenance || {};
  const replayLifecycle = replica.replay_lifecycle || {};
  const replayLifecycleEvents = replayLifecycle.events || [];
  const runtimeTrustPacket = replica.runtime_trust_packet || {};
  const hypothesisPacket = replica.hypothesis_packet || {};
  const mitigationLadder = replica.mitigation_ladder || runbook.mitigation_ladder || guardian.mitigation_ladder || {};
  const runtimeCapabilityDetail = [
    runtimeCapability.host_label ? `Host: ${runtimeCapability.host_label}` : "",
    runtimeCapability.bounded_pack_available ? "Bounded pack mapped" : "No bounded pack",
    runtimeCapability.can_execute_replay ? "Replay can be requested now" : "Replay cannot be requested from this host state",
  ]
    .filter(Boolean)
    .join(" · ");
  const runtimeProvenanceDetail = [
    runtimeProvenance.summary ? `Runtime: ${runtimeProvenance.summary}` : "",
    runtimeProvenance.executed_by ? `Executed by: ${runtimeProvenance.executed_by}` : "",
  ]
    .filter(Boolean)
    .join(" · ") || "Runtime provenance not available";
  setText("replicaOutcome", titleCase(String(replica.best_mitigation_outcome_class || replica.baseline_outcome_class || "not_run").replace(/_/g, " ")));
  setText("replicaCapabilityState", runtimeCapability.label || "Unknown");
  setText("replicaCapabilityHost", runtimeCapability.host_label || "Unknown");
  setText("replicaRuntimeHint", runtimeProvenanceDetail);
  setText("replicaCapabilityMessage", runtimeCapability.message || "Replay capability details are not available for this incident yet.");
  setText("replicaCapabilityDetail", runtimeCapabilityDetail || "Runtime capability posture is not available for this incident yet.");

  // Populate runtime-host card
  const runtimeHostState = [
    runtimeCapability.label,
    runtimeCapability.host_label,
  ].filter(Boolean).join(" on ");
  setText("runtimeHostState", runtimeHostState || "Runtime host posture pending");

  // Populate runtime queue recovery card
  const runtimeQueueState = incident.runtime_queue_state || {};
  if (runtimeQueueState.has_queue_history) {
    const queueCard = document.getElementById("runtimeQueueCard");
    if (queueCard) {
      queueCard.style.display = "block";
      setText("runtimeQueueCurrentState", titleCase(String(runtimeQueueState.current_state || "unknown")));
      setText("runtimeQueueAttempts", String(runtimeQueueState.total_attempts || 0));
      setText("runtimeQueueRetries", String(runtimeQueueState.retry_count || 0));
      setText("runtimeQueueMessage", runtimeQueueState.message || "Queue details not available.");
      setText("runtimeQueueStatus", runtimeQueueState.message || "Queue state information is pending.");
    }
  } else {
    const queueCard = document.getElementById("runtimeQueueCard");
    if (queueCard) {
      queueCard.style.display = "none";
    }
  }

  if (hypothesisPacket.supported && hypothesisPacket.pack_id) {
    const packInfoCard = document.getElementById("runtimePackInfo");
    if (packInfoCard) {
      packInfoCard.style.display = "block";
      setText("runtimePackId", hypothesisPacket.pack_id);
      setText("runtimeIncidentClass", titleCase(hypothesisPacket.incident_class || "unknown"));
      setText("runtimeCoverage", hypothesisPacket.supported ? "Bounded pack available" : "Not supported");
    }
  }
  ensureReplicaHypothesisPacket();
  setText(
    "replicaHypothesisSummary",
    hypothesisPacket.summary
      ? `${hypothesisPacket.summary} ${hypothesisPacket.mapping_basis || ""}`.trim()
      : "REPLICA has not mapped a bounded environment hypothesis for this incident yet."
  );
  renderList(
    "replicaHypothesisChecks",
    hypothesisPacket.supported
      ? [
          {
            label: "Triggering conditions",
            items: hypothesisPacket.triggering_conditions || [],
          },
          {
            label: "Expected failure signature",
            items: hypothesisPacket.expected_failure_signature || [],
          },
          {
            label: "Mitigation checkpoints",
            items: (hypothesisPacket.mitigation_checkpoints || []).map((item) =>
              item.action ? `${item.action}${item.expected_signal ? `: ${item.expected_signal}` : ""}` : ""
            ),
          },
        ].filter((section) => section.items.length)
      : [{ label: "Scope", items: ["No curated flagship REPLICA pack matched this incident class yet."] }],
    (section) =>
      `<li><strong>${section.label}</strong><br><span class="section-note">${section.items.join(" · ")}</span></li>`
  );
  setText(
    "replicaReplayStatus",
    replica.runtime_executed
      ? (runtimeProvenance.summary || "Docker-backed replay executed for this page view.")
      : runtimeCapability.can_execute_replay
        ? (runtimeProvenance.summary || "This host can run bounded replay on demand.")
        : (runtimeCapability.message || "Replay is not available for this incident on the current host.")
  );
  setText(
    "replicaReplayLifecycleState",
    replayLifecycle.current_state
      ? `Replay lifecycle: ${titleCase(replayLifecycle.current_state)}`
      : runtimeCapability.can_execute_replay
        ? "Replay lifecycle: Ready to request"
        : "Replay lifecycle: Waiting on runtime availability"
  );
  setText("replicaComparison", replica.runtime_comparison_summary || "Runtime comparison details are not available for this incident yet.");
  setText(
    "replicaTrustSummary",
    runtimeTrustPacket.operator_summary
      ? `Replay trust packet: ${runtimeTrustPacket.operator_summary}`
      : "Replay trust packet is not available for this incident yet."
  );
  renderList(
    "replicaReplayLifecycleEvents",
    replayLifecycleEvents.length
      ? replayLifecycleEvents
      : [{ label: "Ready", recorded_at: "", message: "Replay has not been requested for this incident yet." }],
    (item) =>
      `<li><strong>${item.label || titleCase(item.state || "ready")}</strong>${item.recorded_at ? `<br><span class="section-note">${formatTimestamp(item.recorded_at)}</span>` : ""}<br><span class="section-note">${item.message || ""}</span></li>`
  );
  renderList(
    "replicaTrustChecks",
    runtimeTrustPacket.decision
      ? [
          `Decision: ${titleCase(runtimeTrustPacket.decision)}`,
          `Evidence tier: ${titleCase(runtimeTrustPacket.evidence_tier || "unknown")}`,
          `Execution mode: ${titleCase(runtimeTrustPacket.execution_mode || "unknown")}`,
          `Executor: ${runtimeTrustPacket.executor || "Unknown"}`,
          runtimeTrustPacket.limiting_factor ? `Limiting factor: ${titleCase(runtimeTrustPacket.limiting_factor)}` : "Limiting factor: none",
          runtimeTrustPacket.policy_basis ? `Bounded policy: ${runtimeTrustPacket.policy_basis}` : "",
        ].filter(Boolean)
      : ["Decision packet pending"],
    (item) => `<li>${item}</li>`
  );

  const replayButton = document.getElementById("replicaReplayBtn");
  if (replayButton) {
    replayButton.disabled = !runtimeCapability.can_execute_replay;
    replayButton.textContent = replica.runtime_executed ? "Run bounded replay again" : "Run bounded replay";
  }

  // Populate runtime comparison block
  if (replica.best_mitigation_outcome_class || replica.baseline_outcome_class) {
    const block = document.getElementById("runtimeComparisonBlock");
    const baselineRow = document.getElementById("runtimeBaselineRow");
    const mitigatedRow = document.getElementById("runtimeMitigatedRow");
    const runnerUpRow = document.getElementById("runtimeRunnerUpRow");
    const outcomeLabel = document.getElementById("runtimeOutcomeLabel");
    const comparison = replica.mitigation_comparison || {};
    const baseline = comparison.baseline || {};
    const winner = comparison.winner || {};
    const runnerUp = comparison.runner_up || {};

    // Baseline row
    const baselineStatusCode = baseline.status_code ?? replica.replay_status_code;
    const baselineStatus = baselineStatusCode ? `HTTP ${baselineStatusCode}` : `Status: ${titleCase(replica.baseline_outcome_class || baseline.outcome_class || "not_run")}`;
    const baselineDurationValue = baseline.duration_ms ?? replica.replay_duration_ms;
    const baselineDuration = baselineDurationValue ? ` · ${baselineDurationValue}ms` : "";
    baselineRow.innerHTML = `<strong>Baseline:</strong> ${baselineStatus}${baselineDuration}`;

    // Winner row
    const mitigatedStatusCode = winner.status_code ?? replica.best_mitigation_status_code;
    const mitigatedStatus = mitigatedStatusCode ? `HTTP ${mitigatedStatusCode}` : titleCase(replica.best_mitigation_outcome_class || winner.outcome_class || "not_run");
    const mitigatedDurationValue = winner.duration_ms ?? replica.best_mitigation_duration_ms;
    const mitigatedDuration = mitigatedDurationValue ? ` · ${mitigatedDurationValue}ms` : "";
    const mitigatedAction = (winner.action || replica.best_mitigation_action) ? ` · ${winner.action || replica.best_mitigation_action}` : "";
    mitigatedRow.innerHTML = `<strong>Selected:</strong> ${mitigatedStatus}${mitigatedDuration}${mitigatedAction}`;

    if (runnerUpRow) {
      if (runnerUp.action) {
        const runnerUpStatus = runnerUp.status_code ? `HTTP ${runnerUp.status_code}` : titleCase(runnerUp.outcome_class || "not_run");
        const runnerUpDuration = runnerUp.duration_ms ? ` · ${runnerUp.duration_ms}ms` : "";
        runnerUpRow.innerHTML = `<strong>Runner-up:</strong> ${runnerUpStatus}${runnerUpDuration} · ${runnerUp.action}`;
        runnerUpRow.style.display = "block";
      } else {
        runnerUpRow.innerHTML = "";
        runnerUpRow.style.display = "none";
      }
    }

    // Outcome label
    outcomeLabel.textContent = titleCase((replica.best_mitigation_outcome_class || "not_run").replace(/_/g, " "));

    block.style.display = "block";
  }

  const comparisonBlock = document.getElementById("runtimeComparisonBlock");
  let replayHistoryBlock = document.getElementById("replayHistoryBlock");
  if (comparisonBlock && comparisonBlock.parentElement && !replayHistoryBlock) {
    replayHistoryBlock = document.createElement("div");
    replayHistoryBlock.id = "replayHistoryBlock";
    replayHistoryBlock.style.marginTop = "1em";
    replayHistoryBlock.innerHTML = `
      <p class="section-label">Replay history</p>
      <ul class="simple-list" id="replayHistoryList"></ul>
    `;
    comparisonBlock.insertAdjacentElement("afterend", replayHistoryBlock);
  }
  if (replayHistoryBlock) {
    const replayHistory = replica.replay_history || [];
    if (replayHistory.length) {
      renderList(
        "replayHistoryList",
        replayHistory,
        (item) => {
          const provenance = item.runtime_provenance || {};
          const trustPacket = item.runtime_trust_packet || {};
          const lifecycleState = item.lifecycle_state ? ` · ${titleCase(item.lifecycle_state)}` : "";
          const lifecyclePath = (item.lifecycle_events || [])
            .map((event) => event.label || titleCase(event.state || ""))
            .filter(Boolean)
            .join(" → ");
          const baseline = item.replay_status_code ? `baseline HTTP ${item.replay_status_code}${item.replay_duration_ms ? ` at ${item.replay_duration_ms}ms` : ""}` : "baseline not captured";
          const selected = item.best_mitigation_action
            ? `${item.best_mitigation_action}${item.best_mitigation_status_code ? ` → HTTP ${item.best_mitigation_status_code}` : ""}${item.best_mitigation_duration_ms ? ` at ${item.best_mitigation_duration_ms}ms` : ""}`
            : "No selected mitigation";
          return `<li><strong>${item.is_latest ? "Latest replay" : `Prior replay ${item.index}`}</strong><br><span class="section-note">${formatTimestamp(item.recorded_at)} · ${provenance.label || titleCase(provenance.mode || "unknown source")}${lifecycleState}</span>${lifecyclePath ? `<br><span class="section-note">${lifecyclePath}</span>` : ""}${trustPacket.decision ? `<br><span class="section-note">${titleCase(trustPacket.decision)} · ${titleCase(trustPacket.evidence_tier || "unknown")}${trustPacket.limiting_factor ? ` · ${titleCase(trustPacket.limiting_factor)}` : ""}</span>` : ""}<br><span class="section-note">${baseline}</span><br><span class="section-note">${titleCase(String(item.best_mitigation_outcome_class || "not_run").replace(/_/g, " "))} · ${selected}</span></li>`;
        }
      );
      replayHistoryBlock.style.display = "block";
    } else {
      replayHistoryBlock.style.display = "none";
    }
  }

  if (replica.scaffold_ready && (replica.services_seen || []).length) {
    setText("replicaPack", `${replica.environment_pack_id || "-"} · ${replica.services_seen.join(", ")}`);
  }
  ensureMitigationLadderPacket();
  setText(
    "replicaMitigationLadderSummary",
    mitigationLadder.operator_summary
      ? `${mitigationLadder.operator_summary} Stop condition: ${mitigationLadder.stop_condition || "Not specified."}`
      : "FORGE has not attached a bounded mitigation ladder yet."
  );
  renderList(
    "replicaMitigationLadderSteps",
    (mitigationLadder.steps || []).length
      ? mitigationLadder.steps
      : [{ role: "primary", action: "No bounded ladder yet", summary: "Runtime comparison has not produced a primary/fallback sequence yet.", outcome_class: "inferred_only" }],
    (item) =>
      `<li><strong>${titleCase(item.role || "step")} · ${item.action || "No action"}</strong><br><span class="section-note">${titleCase(String(item.outcome_class || "inferred_only").replace(/_/g, " "))}</span>${item.summary ? `<br><span class="section-note">${item.summary}</span>` : ""}</li>`
  );
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
  setText(
    "traceReplayEvidence",
    [trace.replay_evidence_summary, traceRuntimeProvenance.summary].filter(Boolean).join(" ") || "Replay evidence is not available for this incident yet."
  );
  setText("traceInspectionPoint", trace.inspection_point || "TRACE has not narrowed an inspect-here-first path yet.");
  setText(
    "traceDeveloperHandoff",
    trace.developer_handoff_summary
      ? `${trace.developer_handoff_summary}${trace.code_owner_team ? ` Owner: ${trace.code_owner_team}` : ""}${trace.code_owner_slug ? ` (${trace.code_owner_slug})` : ""}${trace.code_owner_source ? ` · Source: ${trace.code_owner_source}` : ""}.`
      : "TRACE has not prepared a developer handoff packet yet."
  );
  ensureTraceCodePacket();
  setText("traceStackSummary", trace.stack_path_summary || "TRACE has not prepared a bounded stack path for this incident yet.");
  setText("traceFailureBoundary", trace.failure_boundary || "TRACE has not identified the failure boundary yet.");
  setText("traceRuntimeClue", trace.runtime_clue || "TRACE has not attached a runtime clue yet.");
  const residualRisk = trace.residual_risk || {};
  setText("traceResidualSummary", residualRisk.summary || "Residual risk summary will appear here.");
  setText("traceResidualScope", `Scope: ${residualRisk.scope || "Scope information will appear here."}`);
  setText("traceResidualCaveats", residualRisk.confidence_caveats || "Confidence caveats will appear here.");
  setText("traceResidualNextSteps", `If divergent: ${residualRisk.next_steps_if_divergent || "Next steps will appear here."}`);
  renderList(
    "traceStackPath",
    (trace.stack_path || []).length
      ? trace.stack_path
      : [{ service: "No bounded stack path yet", module: "", function: "", file: "", checkpoint: trace.expected_flow || "TRACE has not run on this incident yet." }],
    (item) =>
      `<li><strong>${item.service || "Unknown service"}</strong>${item.module ? `<br><span class="section-note">${item.module}</span>` : ""}${item.function ? `<br><span class="section-note">${item.function}</span>` : ""}${item.file ? `<br><span class="section-note">${item.file}</span>` : ""}${item.checkpoint ? `<br><span class="section-note">${item.checkpoint}</span>` : ""}</li>`
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
  const debuggerPacket = trace.debugger_packet || {};
  ensureDebuggerPacket();
  setText(
    "traceDebuggerSummary",
    debuggerPacket.supported
      ? `${debuggerPacket.summary} Scope: ${debuggerPacket.scope || "bounded pack only"}. ${
          debuggerPacket.validated_by_replay
            ? "This debugging trail was validated by bounded replay execution."
            : ""
        }`
      : debuggerPacket.summary || "No bounded debugger packet is implemented for this incident class yet."
  );
  const debuggerChecks = debuggerPacket.supported
    ? [
        `Target file: ${debuggerPacket.target_file || "unknown"}`,
        `Entry function: ${debuggerPacket.entry_function || "unknown"}`,
        ...((debuggerPacket.state_checkpoints || []).map(
          (item) =>
            `${item.name || "checkpoint"} · ${item.location || "unknown location"} · Expected: ${item.expected || "n/a"} · Divergence: ${item.divergence || "n/a"}`
        )),
        `Human next step: ${debuggerPacket.human_next_step || "Use the TRACE packet for manual debugging."}`,
      ]
    : ["Debugger packet not implemented for this incident class."];
  if (debuggerPacket.replay_evidence) {
    debuggerChecks.push(`Replay validation: ${debuggerPacket.replay_evidence}`);
  }
  renderList(
    "traceDebuggerChecks",
    debuggerChecks,
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

function renderFreshIntakeTruth(data) {
  const card = document.getElementById("freshTruthCard");
  const truth = data.fresh_intake_truth;
  if (!card) {
    return;
  }
  if (!truth || !truth.is_fresh_incident) {
    card.hidden = true;
    return;
  }

  card.hidden = false;
  const extracted = Array.isArray(truth.extracted_signals) ? truth.extracted_signals : [];
  const inferred = Array.isArray(truth.inferred_conclusions) ? truth.inferred_conclusions : [];
  const uncertainty = Array.isArray(truth.remaining_uncertainty) ? truth.remaining_uncertainty : [];
  setText("freshTruthSummary", truth.summary || "Fresh evidence posture is available.");
  setText("freshTruthExtractedCount", String(extracted.length));
  setText("freshTruthInferredCount", String(inferred.length));
  setText("freshTruthUncertainCount", String(uncertainty.length));
  setText("freshTruthSupportState", titleCase(String(truth.support_state || "unknown").replace(/-/g, " ")));
  setText("freshTruthGuidance", truth.operator_guidance || "Review extracted versus inferred evidence before treating the packet as decision-ready.");

  renderList(
    "freshTruthExtractedList",
    extracted.length ? extracted : [{ label: "Extracted evidence", value: "No concrete extracted signals recorded yet.", source: "n/a" }],
    (item) => `<li><strong>${item.label || "Signal"}</strong><br>${item.value || "-"}<br><span class="section-note">Source: ${titleCase(String(item.source || "unknown").replace(/_/g, " "))}</span></li>`
  );
  renderList(
    "freshTruthInferredList",
    inferred.length ? inferred : [{ label: "Inference", value: "No inferred conclusions recorded yet." }],
    (item) => `<li><strong>${item.label || "Inference"}</strong><br>${item.value || "-"}</li>`
  );
  renderList(
    "freshTruthUncertaintyList",
    uncertainty.length ? uncertainty : ["No remaining uncertainty recorded."],
    (item) => `<li>${item}</li>`
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

function formatAuditActor(entry) {
  if (!entry) {
    return "System";
  }
  const payload = entry.payload || {};
  const actor = entry.actor_user_id || payload.user_id || entry.tenant_id || "System";
  const roles = Array.isArray(entry.actor_roles) ? entry.actor_roles.filter(Boolean) : [];
  return roles.length ? `${actor} (${roles.join(", ")})` : actor;
}

function formatEvidencePostureLabel(value) {
  const posture = String(value || "").toLowerCase();
  if (posture === "runtime-backed") {
    return "Runtime-backed";
  }
  if (posture === "inference-first" || posture === "inferred-only") {
    return "Inference-first";
  }
  if (posture === "unsupported") {
    return "Unsupported";
  }
  return titleCase(value || "Recorded");
}

function renderAudit(status, auditLogs, data) {
  const recentAuditLogs = auditLogs.length ? [...auditLogs].slice(-24) : [];
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
  setText("auditLatestActor", formatAuditActor(latest));
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
      .map((entry) => `<article class="audit-preview-entry"><div class="audit-preview-top"><strong>${formatAuditEventLabel(entry.event_type)}</strong><span>${entry.payload?.status || "recorded"}</span></div><div class="audit-preview-meta">${entry.timestamp || "-"} · ${formatAuditActor(entry)}${entry.payload?.evidence_posture ? ` · ${formatEvidencePostureLabel(entry.payload.evidence_posture)}` : ""}</div></article>`)
      .join("");
  }

  renderList(
    "incidentAuditLogs",
    recentAuditLogs.length ? recentAuditLogs.reverse() : [{ event_type: "audit", timestamp: "-", payload: { note: "No audit entries yet." } }],
    (entry) => `
      <article class="audit-entry">
        <div class="audit-entry-top">
          <div><div class="audit-entry-title">${formatAuditEventLabel(entry.event_type)}</div><div class="audit-entry-meta">${entry.timestamp || "-"} · ${formatAuditActor(entry)} · ${entry.tenant_id || "tenant-system"}${entry.payload?.evidence_posture ? ` · ${formatEvidencePostureLabel(entry.payload.evidence_posture)}` : ""}</div></div>
          <div class="audit-entry-badge">${entry.payload?.status || entry.payload?.current_stage || "recorded"}</div>
        </div>
        <div class="section-note">${entry.payload?.reasoning || entry.payload?.summary || entry.payload?.note || entry.payload?.decision || "Recorded for reviewer traceability."}</div>
      </article>
    `
  );
  setText(
    "auditSummaryCaption",
    auditLogs.length > recentAuditLogs.length
      ? `Showing the latest ${recentAuditLogs.length} audit entries out of ${auditLogs.length}.`
      : `Showing ${recentAuditLogs.length || 0} audit entries.`
  );
}

function renderExecutionOutcome(data) {
  const outcome = data.execution_outcome;
  if (!outcome) {
    setText("executionResult", data.execution_result === "executed" ? "Execution completed after Guardian approval." : "Execution is waiting on a clear governance decision.");
    return;
  }

  const decisionLabel = String(outcome.guardian_decision || "").toUpperCase();
  const statusEmoji = outcome.execution_status === "executed" ? "✓" : outcome.execution_status === "blocked" ? "✗" : "⚠";
  const runtimeBacking = outcome.runtime_backed ? " (Runtime-backed)" : " (Inferred)";

  let detailsHtml = `
    <div class="outcome-summary">
      <div class="outcome-header">
        <span class="outcome-status">${statusEmoji} ${String(outcome.execution_status || "").toUpperCase()}</span>
        <span class="outcome-decision">${decisionLabel}</span>
      </div>
      <p class="outcome-text">${outcome.summary || "Execution outcome recorded."}</p>
      <div class="outcome-details">
        <div class="outcome-detail-row">
          <span class="outcome-label">Root Cause:</span>
          <span class="outcome-value">${outcome.root_cause || "Unknown"}</span>
        </div>
        <div class="outcome-detail-row">
          <span class="outcome-label">Action:</span>
          <span class="outcome-value">${outcome.selected_action || "Pending"}</span>
        </div>
        <div class="outcome-detail-row">
          <span class="outcome-label">Mitigation:</span>
          <span class="outcome-value">${outcome.mitigation_outcome_class || "inferred_only"}${runtimeBacking}</span>
        </div>
        <div class="outcome-detail-row">
          <span class="outcome-label">Recorded:</span>
          <span class="outcome-value">${formatTimestamp(outcome.recorded_at)}</span>
        </div>
      </div>
    </div>
  `;

  const executionResultElement = document.getElementById("executionResult");
  if (executionResultElement) {
    executionResultElement.innerHTML = detailsHtml;
  }
}

function renderDeliveryHistory(data) {
  const normalized_evidence = data.normalized_evidence || {};
  const delivery_history = normalized_evidence.delivery_history || [];

  if (!delivery_history || delivery_history.length === 0) {
    setText("deliveryHistory", "No deliveries yet.");
    return;
  }

  const items = delivery_history.map((entry) => {
    const icons = {
      "delivered": "✓",
      "queued": "⧗",
      "retrying": "↻",
      "failed": "✗",
      "terminal_failure": "✗✗",
    };
    const icon = icons[entry.status] || "⧖";
    const backing = entry.evidence_backing ? ` (${entry.evidence_backing})` : "";
    const reason = entry.failure_reason ? ` — ${entry.failure_reason}` : "";
    const attemptInfo = entry.attempt_count ? ` [attempt ${entry.attempt_count}]` : "";
    const statusLabel = entry.status;
    const actorInfo = entry.actor_user_id
      ? ` · ${entry.actor_user_id}${Array.isArray(entry.actor_roles) && entry.actor_roles.length ? ` (${entry.actor_roles.join(", ")})` : ""}`
      : "";
    const feedbackInfo = entry.feedback_state ? ` · feedback ${entry.feedback_state}` : "";
    const postureInfo = entry.failure_posture ? ` · ${titleCase(String(entry.failure_posture).replace(/_/g, " "))}` : "";
    const duplicateInfo = entry.duplicate_semantics ? ` · ${titleCase(String(entry.duplicate_semantics).replace(/_/g, " "))}` : "";
    return {
      label: `${icon} ${String(entry.target || "unknown").toUpperCase()} — ${statusLabel}${attemptInfo}${backing}${reason}`,
      detail: `Sent at ${formatTimestamp(entry.sent_at)}${actorInfo}${feedbackInfo}${postureInfo}${duplicateInfo}`,
      guidance: entry.operator_guidance || "",
      entry: entry,
    };
  });

  renderList("deliveryHistory", items, (item) => {
    const retryBtn = item.entry.status === "retrying" || item.entry.status === "failed" ?
      ` <button class="small-action-btn" data-delivery-retry="${item.entry.target}">Retry</button>` : "";
    return `<div><strong>${item.label}</strong><br><span class="section-note">${item.detail}</span>${item.guidance ? `<br><span class="section-note">${item.guidance}</span>` : ""}${retryBtn}</div>`;
  });

  document.querySelectorAll("[data-delivery-retry]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const target = btn.getAttribute("data-delivery-retry");
      btn.disabled = true;
      btn.textContent = "Retrying...";
      try {
        const response = await postAuthedJson(`/api/v1/incidents/${encodeURIComponent(window.getIncidentId?.() || getIncidentId())}/handoff-retry`, {
          target: target,
        });
        if (response.status === "sent" || response.status === "retrying") {
          btn.textContent = "✓ Sent";
        } else if (response.status === "terminal_failure") {
          btn.textContent = "✗ Terminal failure";
          if (response.operator_guidance) {
            alert(response.operator_guidance);
          }
        }
      } catch (error) {
        btn.textContent = "✗ Retry failed";
        console.error("Retry failed:", error);
      } finally {
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      }
    });
  });
}

function renderEngineeringFeedback(data) {
  const normalized_evidence = data.normalized_evidence || {};
  const feedback = normalized_evidence.engineering_feedback || [];

  if (!feedback || feedback.length === 0) {
    setText("engineeringFeedback", "No feedback recorded yet.");
    return;
  }

  const items = feedback.map((entry) => {
    const icon = entry.status === "accepted" ? "✓" : entry.status === "rejected" ? "✗" : entry.status === "resolved" ? "→" : "⧖";
    const reason = entry.reason ? ` — ${entry.reason}` : "";
    const continuity = entry.status_continuity ? ` · ${titleCase(String(entry.status_continuity).replace(/_/g, " "))}` : "";
    return {
      label: `${icon} ${String(entry.status || "pending").toUpperCase()}${reason}${continuity}`,
      detail: `Recorded at ${formatTimestamp(entry.recorded_at)}`,
    };
  });

  renderList("engineeringFeedback", items, (item) => `<div><strong>${item.label}</strong><br><span class="section-note">${item.detail}</span></div>`);
}

function setupEngineeringFeedbackHandlers(incidentId) {
  const submitFeedback = async (status, reason = "") => {
    const btn = document.getElementById(`feedback${status.charAt(0).toUpperCase() + status.slice(1)}Btn`);
    if (btn) {
      btn.disabled = true;
      btn.textContent = `Submitting ${status}...`;
    }
    try {
      await postAuthedJson(
        `/api/v1/incidents/${encodeURIComponent(incidentId)}/engineering-feedback`,
        { status, reason }
      );
      alert(`Feedback recorded: ${status}`);
      location.reload();
    } catch (err) {
      console.error("Feedback submission failed:", err);
      alert("Failed to record feedback. See console for details.");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = `Mark as ${status}`;
      }
    }
  };

  document.getElementById("feedbackAcceptedBtn")?.addEventListener("click", () => submitFeedback("accepted"));
  document.getElementById("feedbackRejectedBtn")?.addEventListener("click", () => submitFeedback("rejected"));
  document.getElementById("feedbackResolvedBtn")?.addEventListener("click", () => submitFeedback("resolved"));
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
  const data = await loadIncident(incidentId, options);

  renderSummary(data);
  renderThread(data);
  renderHandoffFlow(data);
  renderCrew(data);
  renderEnterprise(data);
  renderSourcePayload(data.incident);
  renderFreshIntakeTruth(data);
  renderEvidence(data);
  renderExecutionOutcome(data);
  renderDeliveryHistory(data);
  renderEngineeringFeedback(data);
  setupEngineeringFeedbackHandlers(incidentId);
  setText("workflowSummary", `${data.incident.id} flowing from ${data.incident.source_channel || "webhook"} to verified outcome`);
  setText("workflowSummaryCopy", "Loading the audit timeline and reviewer traceability now.");
  setText("statusStage", "Loading...");
  setText("statusQueuePosition", "...");
  setText("statusEta", "...");
  setText("statusSource", data.incident.source_channel || "webhook");
  setText("auditEntryCount", "...");
  setText("auditLatestEvent", "Loading...");
  setText("auditLatestActor", "Loading...");
  setText("auditLatestState", "Loading...");
  setText("auditSummaryCaption", "Loading audit trail and reviewer traceability.");
  setText(
    "guardianGateState",
    `${data.guardian.reasoning}${data.guardian.required_approval_level ? ` Approval level: ${data.guardian.required_approval_level}.` : ""}${data.guardian.rollback_readiness ? ` Rollback: ${data.guardian.rollback_readiness}.` : ""}`
  );
  const outcomeEmoji = data.execution_outcome ? "✓" : "⧖";
  setText("resultBanner", `${formatIncidentHandle(data.incident.id)} · ${String(data.guardian.decision).toUpperCase()} · ${data.execution_result === "executed" ? `${outcomeEmoji} EXECUTED` : "PENDING"}`);
  persistLastTriageSummary(data);

  try {
    const [status, auditLogs] = await Promise.all([
      fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/status`),
      fetchAuthedJson(`/api/v1/audit-logs/${encodeURIComponent(incidentId)}`),
    ]);
    renderAudit(status, auditLogs, data);
  } catch (error) {
    setText("auditSummaryCaption", `Audit trail is temporarily unavailable: ${error.message}`);
    setText("statusStage", "Unavailable");
    setText("auditLatestEvent", "Audit unavailable");
  }
  return data;
}

async function maybePlayInitialRelay(incidentId, data) {
  if (isFreshTriageIncident(incidentId)) {
    markRelaySeen(incidentId);
    clearFreshTriageIncident(incidentId);
    showFreshIntakeLanding(data);
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

async function loadUserCapabilities() {
  try {
    const context = await fetchAuthedJson("/api/v1/auth/user-context");
    return context.capabilities || {};
  } catch {
    return {};
  }
}

function applyRoleBasedVisibility(capabilities) {
  const controls = {
    replay: document.getElementById("replayRelayBtn"),
    handoff_send: document.getElementById("sendBtn"),
    guardian_approve: document.getElementById("guardianApproveBtn"),
    guardian_block: document.getElementById("guardianBlockBtn"),
    guardian_modify: document.getElementById("guardianModifyBtn"),
  };

  if (!capabilities.trigger_replay && controls.replay) {
    controls.replay.disabled = true;
    controls.replay.title = "Your role does not have permission to trigger replay";
  }

  if (!capabilities.send_handoff && controls.handoff_send) {
    controls.handoff_send.disabled = true;
    controls.handoff_send.title = "Your role does not have permission to send handoffs";
  }

  if (!capabilities.approve_action) {
    if (controls.guardian_approve) controls.guardian_approve.style.display = "none";
    if (controls.guardian_block) controls.guardian_block.style.display = "none";
    if (controls.guardian_modify) controls.guardian_modify.style.display = "none";
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  const incidentId = getIncidentId();
  const historyReviewMode = isHistoryReviewMode();
  const pendingLaunch = renderPendingIncidentLaunch(incidentId);
  let currentIncidentData = null;
  syncLiveReasoningToggle();
  syncOpenAIKeyUI();

  const userCapabilities = await loadUserCapabilities();
  applyRoleBasedVisibility(userCapabilities);

  async function refreshIncident(options = {}) {
    currentIncidentData = await loadAndRenderIncident(incidentId, options);
    return currentIncidentData;
  }

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
      const refreshed = await refreshIncident();
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
    await refreshIncident();
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
    await refreshIncident();
  });

  document.getElementById("clearOpenAIKeyBtn")?.addEventListener("click", async () => {
    clearUserOpenAIKey();
    syncOpenAIKeyUI("User key cleared. The app is back in deterministic demo mode.");
    await refreshIncident();
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
      const current = await refreshIncident();
      await replayRelayForIncident(incidentId, current);
    } finally {
      if (button) {
        button.disabled = false;
      }
    }
  });

  let replayState = { inProgress: false, currentStep: -1, events: [] };
  const handoffReplayStart = document.getElementById("handoffReplayStart");
  const handoffReplayNext = document.getElementById("handoffReplayNext");
  const handoffReplayReset = document.getElementById("handoffReplayReset");

  function updateReplayUI() {
    const isRunning = replayState.inProgress;
    const hasEvents = replayState.events.length > 0;
    const isAtEnd = replayState.currentStep >= replayState.events.length - 1;
    const activeEvent = replayState.currentStep >= 0 ? replayState.events[replayState.currentStep] : null;
    const upcomingEvent = replayState.currentStep >= 0 ? replayState.events[replayState.currentStep + 1] : replayState.events[0];

    if (handoffReplayStart) handoffReplayStart.disabled = isRunning || !hasEvents;
    if (handoffReplayNext) handoffReplayNext.disabled = isRunning || !hasEvents || isAtEnd;
    if (handoffReplayReset) handoffReplayReset.disabled = !isRunning && replayState.currentStep === -1;
    if (handoffReplayNext) {
      handoffReplayNext.textContent = upcomingEvent ? `Next: ${upcomingEvent.to || "step"}` : "Replay complete";
    }

    const stateLabel = isRunning
      ? activeEvent
        ? `Step ${replayState.currentStep + 1} of ${replayState.events.length} · ${activeEvent.to || "Unknown"} now owns the case`
        : `Replay armed · ${replayState.events.length} baton transfers available`
      : replayState.currentStep >= 0
        ? `Paused at step ${replayState.currentStep + 1}`
        : "Ready to replay";
    setText("handoffReplayState", stateLabel);
    setText(
      "handoffReplayHint",
      activeEvent
        ? `${activeEvent.from || "Unknown"} handed responsibility to ${activeEvent.to || "Unknown"}. ${upcomingEvent ? `Next up: ${upcomingEvent.from || activeEvent.to || "Unknown"} → ${upcomingEvent.to || "Unknown"}.` : "This is the final visible handoff in the chain."}`
        : "Use replay when you want to step through baton transfer one handoff at a time."
    );
  }

  handoffReplayStart?.addEventListener("click", () => {
    if (currentIncidentData?.handoff_flow?.events) {
      replayState = { inProgress: true, currentStep: 0, events: currentIncidentData.handoff_flow.events };
      window.__nexusHandoffReplayState = replayState;
      renderHandoffFlow(currentIncidentData);
      updateReplayUI();
    }
  });

  handoffReplayNext?.addEventListener("click", () => {
    if (replayState.inProgress && replayState.currentStep < replayState.events.length - 1) {
      replayState.currentStep += 1;
      window.__nexusHandoffReplayState = replayState;
      renderHandoffFlow(currentIncidentData);
      updateReplayUI();
    }
  });

  handoffReplayReset?.addEventListener("click", () => {
    replayState = { inProgress: false, currentStep: -1, events: [] };
    window.__nexusHandoffReplayState = null;
    updateReplayUI();
    if (currentIncidentData) {
      renderHandoffFlow(currentIncidentData);
    }
  });

  const exportDropdown = document.getElementById("exportDropdown");
  const exportBtn = document.getElementById("exportHandoffBtn");
  const exportFormatMap = {
    "markdown": { ext: "md", mime: "text/markdown" },
    "github": { ext: "md", mime: "text/markdown" },
    "jira": { ext: "txt", mime: "text/plain" },
    "slack": { ext: "txt", mime: "text/plain" },
  };

  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      if (exportDropdown) {
        exportDropdown.style.display = exportDropdown.style.display === "none" ? "block" : "none";
      }
    });
  }

  document.querySelectorAll(".export-option")?.forEach(option => {
    option.addEventListener("click", async (e) => {
      const format = e.target.getAttribute("data-format") || "markdown";
      if (exportDropdown) {
        exportDropdown.style.display = "none";
      }
      if (exportBtn) {
        exportBtn.disabled = true;
        exportBtn.textContent = "Generating export...";
      }
      try {
        const response = await fetchAuthedJson(
          `/api/v1/incidents/${encodeURIComponent(incidentId)}/handoff-export?format=${format}`
        );
        const text = response.handoff_text || "No handoff generated";
        const formatInfo = exportFormatMap[format] || exportFormatMap.markdown;
        downloadTextFile(text, `${incidentId}-handoff.${formatInfo.ext}`);
      } catch (err) {
        console.error("Handoff export failed:", err);
        alert("Failed to generate engineering handoff. See console for details.");
      } finally {
        if (exportBtn) {
          exportBtn.disabled = false;
          exportBtn.textContent = "Export to engineering";
        }
      }
    });
  });

  document.addEventListener("click", (e) => {
    if (exportDropdown && !e.target.closest("#exportHandoffBtn") && !e.target.closest(".export-dropdown")) {
      exportDropdown.style.display = "none";
    }
  });

  document.getElementById("exportGovernanceBtn")?.addEventListener("click", async () => {
    const button = document.getElementById("exportGovernanceBtn");
    if (button) {
      button.disabled = true;
      button.textContent = "Generating governance packet...";
    }
    try {
      const response = await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/governance-packet`);
      const govData = response;
      const govText = `# Governance Packet — ${govData.incident_id}

## Incident Summary
- Title: ${govData.incident_title}
- Service: ${govData.incident_service}
- Severity: ${govData.incident_severity}

## Approval Timeline
${(govData.approval_timeline || []).map(event => `- **${event.event}** (${event.actor || 'system'}): ${event.summary}${event.evidence_posture ? ` [${event.evidence_posture}]` : ''}`).join('\n')}

## Governance Decisions
- Decision: ${govData.governance_decisions?.guardian_decision || 'PENDING'}
- Confidence: ${govData.governance_decisions?.guardian_confidence || 0}%
- Risk Assessment: ${govData.governance_decisions?.risk_assessment || 'UNKNOWN'}

## Evidence Posture
- Root Cause Evidence: ${govData.evidence_posture?.root_cause_evidence || 'inferred-only'}
- Support Posture: ${govData.evidence_posture?.support_posture || 'inference-first'}
- Hypothesis Confidence: ${govData.evidence_posture?.hypothesis_confidence || 0}%
- Mitigation Validated: ${govData.evidence_posture?.mitigation_validated ? 'Yes' : 'No'}

## Reviewer Traceability
- Latest actor: ${govData.reviewer_traceability?.latest_actor_label || 'System'}
- Governance actor: ${govData.reviewer_traceability?.governance_actor_label || 'System'}
- Replay actor: ${govData.reviewer_traceability?.replay_actor_label || 'Not recorded'}
- Delivery actor: ${govData.reviewer_traceability?.delivery_actor_label || 'Not recorded'}
- Audit entries considered: ${govData.reviewer_traceability?.audit_entry_count || 0}

## Execution Record
- Status: ${govData.execution_record?.status || 'pending'}
- Summary: ${govData.execution_record?.summary || 'Not executed'}

---
Generated: ${govData.generated_at}
`;
      downloadTextFile(govText, `${incidentId}-governance-packet.txt`);
    } catch (err) {
      console.error("Governance packet export failed:", err);
      alert("Failed to generate governance packet. See console for details.");
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Export governance";
      }
    }
  });

  document.getElementById("exportProofBtn")?.addEventListener("click", async () => {
    const button = document.getElementById("exportProofBtn");
    if (button) {
      button.disabled = true;
      button.textContent = "Generating proof export...";
    }
    try {
      const response = await fetchAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/proof-export`);
      const proof = response;
      const proofText = `# Case Proof Export — ${proof.case_id}

${proof.case_title}

## Summary
${proof.proof_summary}

## Before State
- Incident: ${proof.before_state.incident_title}
- Severity: ${proof.before_state.severity}
- Issue Family: ${proof.before_state.issue_family}
- Business Impact: ${proof.before_state.business_impact}
- Manual Relay Required: ${proof.before_state.manual_relay_required ? 'Yes' : 'No'}

## After State
- Root Cause: ${proof.after_state.root_cause}
- Likely Owner: ${proof.after_state.likely_owner}
- Recommended Action: ${proof.after_state.recommended_action}
- Triage Time Saved: ${proof.after_state.triage_time_saved}
- Manual Relay Required: ${proof.after_state.manual_relay_required ? 'Yes' : 'No'}
- Execution Status: ${proof.after_state.execution_status}

## Support Posture
${proof.evidence_posture}

## Proof Signals
${proof.value_signals.map(s => `- ${s}`).join('\n')}

## Honest Boundaries
${proof.honest_boundaries.map(b => `- ${b}`).join('\n')}

---
Generated: ${proof.export_timestamp}
`;
      downloadTextFile(proofText, `${incidentId}-case-proof.txt`);
    } catch (err) {
      console.error("Proof export failed:", err);
      alert("Failed to generate proof export. See console for details.");
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Export case proof";
      }
    }
  });

  const sendDropdown = document.getElementById("sendDropdown");
  const sendBtn = document.getElementById("sendHandoffBtn");

  if (sendBtn) {
    sendBtn.addEventListener("click", () => {
      if (sendDropdown) {
        sendDropdown.style.display = sendDropdown.style.display === "none" ? "block" : "none";
      }
    });
  }

  document.querySelectorAll(".send-option")?.forEach(option => {
    option.addEventListener("click", async (e) => {
      const target = e.target.getAttribute("data-target") || "github";
      if (sendDropdown) {
        sendDropdown.style.display = "none";
      }
      if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = `Sending to ${target}...`;
      }
      try {
        const response = await postAuthedJson(
          `/api/v1/incidents/${encodeURIComponent(incidentId)}/handoff-send`,
          { target }
        );
        if (response.status === "delivered") {
          alert(`Successfully sent to ${target}!`);
        } else {
          alert(`Send failed: ${response.failure_reason || 'Unknown error'}`);
        }
      } catch (err) {
        console.error("Handoff send failed:", err);
        alert("Failed to send engineering handoff. See console for details.");
      } finally {
        if (sendBtn) {
          sendBtn.disabled = false;
          sendBtn.textContent = "Send to engineering";
        }
      }
    });
  });

  document.addEventListener("click", (e) => {
    if (sendDropdown && !e.target.closest("#sendHandoffBtn") && !e.target.closest(".send-dropdown")) {
      sendDropdown.style.display = "none";
    }
  });

  document.getElementById("replicaReplayBtn")?.addEventListener("click", async () => {
    const button = document.getElementById("replicaReplayBtn");
    if (button) {
      button.disabled = true;
      button.textContent = "Running bounded replay...";
    }
    setText("replicaReplayStatus", "Requesting bounded replay from the current host...");
    setText("replicaReplayLifecycleState", "Replay lifecycle: Requested");
    renderList(
      "replicaReplayLifecycleEvents",
      [
        {
          label: "Requested",
          recorded_at: new Date().toISOString(),
          message: "The operator requested bounded replay from the incident console.",
        },
      ],
      (item) =>
        `<li><strong>${item.label}</strong><br><span class="section-note">${formatTimestamp(item.recorded_at)}</span><br><span class="section-note">${item.message}</span></li>`
    );
    try {
      await sleep(180);
      setText("replicaReplayLifecycleState", "Replay lifecycle: Running");
      renderList(
        "replicaReplayLifecycleEvents",
        [
          {
            label: "Requested",
            recorded_at: new Date(Date.now() - 180).toISOString(),
            message: "The operator requested bounded replay from the incident console.",
          },
          {
            label: "Running",
            recorded_at: new Date().toISOString(),
            message: "NEXUS is dispatching the bounded runtime plan to the current app host or configured relay host.",
          },
        ],
        (item) =>
          `<li><strong>${item.label}</strong><br><span class="section-note">${formatTimestamp(item.recorded_at)}</span><br><span class="section-note">${item.message}</span></li>`
      );
      const response = await postAuthedJson(`/api/v1/incidents/${encodeURIComponent(incidentId)}/replica-replay`, {});
      currentIncidentData = await refreshIncident();
      renderSummary(currentIncidentData);
      renderHandoffFlow(currentIncidentData);
      renderEnterprise(currentIncidentData);
      setText("replicaReplayStatus", response.message || "Replay request completed.");
    } catch (error) {
      setText("replicaReplayStatus", `Replay request failed: ${error.message}`);
      setText("replicaReplayLifecycleState", "Replay lifecycle: Failed");
    } finally {
      const replayCapability = currentIncidentData?.replica_summary?.runtime_capability || {};
      if (button) {
        button.disabled = !replayCapability.can_execute_replay;
        button.textContent = currentIncidentData?.replica_summary?.runtime_executed ? "Run bounded replay again" : "Run bounded replay";
      }
    }
  });

  try {
    const data = await refreshIncident({
      liveReasoningOverride: historyReviewMode ? "0" : undefined,
    });
    if (data?.handoff_flow?.events) {
      replayState.events = data.handoff_flow.events;
      updateReplayUI();
    }
    if (historyReviewMode) {
      setText(
        "liveReasoningDetail",
        "History view opens in deterministic review mode for faster loading. Turn live reasoning on again only when you want to re-run this incident with your key."
      );
      syncLiveReasoningState({ ...data, live_reasoning: false });
    }
    await maybePlayInitialRelay(incidentId, data);
    clearPendingIncidentLaunch(incidentId);
    clearFreshLaunchFlag();
    window.NexusNavigation?.endRouteTransition?.();
  } catch (error) {
    setText("incidentTitle", "Incident unavailable");
    setText("resultBanner", `Failed to load ${incidentId}: ${error.message}`);
    window.NexusNavigation?.endRouteTransition?.();
  }
});
