import { demoAuthHeaders, fetchAuthedJson, getLiveReasoningPreference, postAuthedJson, setLiveReasoningPreference } from "./api.js";

const RAW_LOG_EXAMPLE = `2026-05-30T10:14:22Z checkout-api ERROR timeout waiting for payment service
2026-05-30T10:14:23Z checkout-api WARN retry budget exhausted
2026-05-30T10:14:25Z payments-worker ERROR queue depth exceeded threshold
service=checkout-api severity=P1`;

const WEBHOOK_SECRET = "nexus-demo-webhook-secret";
const FRESH_TRIAGE_STORAGE_KEY = "nexus.fresh_triage_incident_id";
const DEMO_BUNDLE_CONTEXT_PREFIX = "nexus.demo_bundle_context.";
const DEMO_BUNDLES_URL = "static/demo/demo-bundles.json";
let tenantServiceHints = [];
let demoBundles = [];
let selectedDemoBundle = null;

const CHANNELS = {
  raw_text: {
    label: "Paste Raw Logs",
    summary: "Paste raw incident text, stack traces, or error output.",
    auth: "Operator paste or copied incident transcript.",
    next: "Raw text is parsed into structured evidence, then routed into the same triage workflow as other channels.",
    payload: "",
    previewPayload: RAW_LOG_EXAMPLE,
    incidentId: "INC001",
    service: "checkout-api",
    severity: "P1",
    overview: "Paste logs, stack traces, or incident notes.",
    symptoms: "timeout waiting for payment service, retry budget exhausted, queue depth exceeded",
    launchLabel: "Open incident workspace",
  },
  webhook: {
    label: "Webhook",
    summary: "Primary machine-to-machine alert ingestion.",
    auth: "Signed request or integration token.",
    next: "Webhook input lands in the incident queue, is normalized, and opens the Incident Console with the same workflow states.",
    payload: "POST /webhooks/incident\nX-Signature: sha256=...\nBody: service, severity, summary, symptoms",
    incidentId: "INC001",
    service: "payments-api",
    severity: "P1",
    overview: "Checkout latency spike detected by webhook.",
    symptoms: "HTTP 500s, elevated queue depth, and increased checkout latency.",
    launchLabel: "Open webhook incident workspace",
  },
  manual_form: {
    label: "Manual Form",
    summary: "Operator-submitted incident report.",
    auth: "Signed-in user and tenant context.",
    next: "Manual intake keeps the operator on the same page while preserving a consistent incident object.",
    payload: "Service: billing-service\nSeverity: P2\nSummary: checkout latency increase\nSymptoms: 500s, queue depth, timeout spikes",
    incidentId: "INC002",
    service: "billing-service",
    severity: "P2",
    overview: "Operator-reported checkout degradation.",
    symptoms: "Checkout latency increase with timeout spikes and elevated retries.",
    launchLabel: "Open manual incident workspace",
  },
  slack_command: {
    label: "Slack Command",
    summary: "Slack-style reporting from an on-call channel.",
    auth: "Workspace identity and command scope.",
    next: "Slack intake adds workspace context and then routes to the same incident workflow.",
    payload: "/incident report\nService: search-api\nSeverity: P2\nSummary: indexing delay",
    incidentId: "INC003",
    service: "search-api",
    severity: "P2",
    overview: "Slack report from the on-call channel.",
    symptoms: "Indexing delay and delayed search results after a traffic spike.",
    launchLabel: "Open slack incident workspace",
  },
  stream_anomaly: {
    label: "Stream Anomaly",
    summary: "Continuous detector output from telemetry pipelines.",
    auth: "Service token or stream subscription.",
    next: "Stream anomalies create the same incident object while preserving detector metadata for diagnosis.",
    payload: "Detector: memory-growth-anomaly\nService: worker-fleet\nSeverity: P1\nSignal: RSS threshold crossed",
    incidentId: "INC003",
    service: "worker-fleet",
    severity: "P1",
    overview: "Telemetry anomaly from the worker fleet.",
    symptoms: "RSS growth, CPU pressure, and rising memory alerts across the stream.",
    launchLabel: "Open anomaly incident workspace",
  },
  batch_import: {
    label: "Batch Import",
    summary: "Backfill incidents and historical records.",
    auth: "Privileged operator or import job.",
    next: "Batch import is replay-ready and feeds the same workflow used for live incidents.",
    payload: "Import file: replay_bundle.csv\nMode: historical backfill\nSeverity: P1\nRecords: 128",
    incidentId: "INC005",
    service: "historical-import",
    severity: "P1",
    overview: "Replay-ready import for historical incidents.",
    symptoms: "Backfill of closed incidents, payloads, and evidence packs.",
    launchLabel: "Open batch incident workspace",
  },
};

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function incidentHref(incidentId, liveReasoning) {
  const reasoningParam = liveReasoning ? `&live_reasoning=${liveReasoning}` : "";
  const target = `incident?nexus_incident_id=${encodeURIComponent(incidentId)}${reasoningParam}`;
  return window.NexusNavigation?.withReturnTo(target) || target;
}

function demoBundleContextKey(incidentId) {
  return `${DEMO_BUNDLE_CONTEXT_PREFIX}${incidentId}`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function persistDemoBundleContext(incidentId, bundle) {
  if (!incidentId || !bundle) {
    return;
  }
  const payload = {
    id: bundle.id,
    title: bundle.title,
    family: bundle.family,
    likely_owner: bundle.likely_owner,
    proof: bundle.proof,
    expected_path: bundle.expected_path,
    next_step: bundle.next_step,
    runtime_posture: bundle.runtime_posture,
    trace_posture: bundle.trace_posture,
    stored_at: new Date().toISOString(),
  };
  try {
    window.sessionStorage.setItem(demoBundleContextKey(incidentId), JSON.stringify(payload));
  } catch {
    // Ignore storage failures; the incident can still open without the additive demo note.
  }
}

function updateField(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function updateInputField(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.value = value;
  }
}

function matchTenantServiceHints(rawText, hints) {
  const lowered = String(rawText || "").toLowerCase();
  return (hints || []).filter((hint) => {
    const normalized = String(hint || "").trim().toLowerCase();
    return normalized && new RegExp(`(^|[^a-z0-9._-])${normalized.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^a-z0-9._-]|$)`, "i").test(lowered);
  });
}

function computePreviewQuality({ service, severity, signature, lines, serviceSource, severitySource, tenantMatches }) {
  const missingSignals = [];
  const weakSignals = [];
  let score = 0.2;

  if (serviceSource === "defaulted") {
    missingSignals.push("service");
    weakSignals.push("service");
  } else {
    score += 0.25;
  }

  if (severitySource === "default") {
    missingSignals.push("severity");
    weakSignals.push("severity");
  } else {
    score += 0.2;
  }

  if ((lines || []).length >= 2) {
    score += 0.15;
  } else {
    weakSignals.push("multi-line logs");
  }

  if (signature !== "General incident") {
    score += 0.15;
  } else {
    weakSignals.push("specific signature");
  }

  if (tenantMatches.length) {
    score += 0.05;
  }

  const posture = score >= 0.8 && missingSignals.length === 0
    ? "Strong"
    : score >= 0.45
      ? "Partial"
      : "Weak";

  return {
    posture,
    missingSignals,
    hintSource: tenantMatches.length ? "Tenant bootstrap hints" : "Browser preview",
    operatorRead: posture === "Strong"
      ? "Ready for bounded triage"
      : posture === "Partial"
        ? "Route now, confirm gaps before approval"
        : "Ask for service, severity, and 2-3 raw lines",
  };
}

function parseRawLogText(rawText) {
  const text = String(rawText || "").trim();
  if (!text) {
    return {
      service: "-",
      severity: "-",
      signature: "Paste logs to preview",
      action: "Load example logs or paste raw incident text",
      summary: "Paste raw incident text to preview the parsed evidence.",
      posture: "Awaiting input",
      missingSignals: ["Add logs"],
      hintSource: "Browser preview",
      operatorRead: "Paste logs to shape the case",
    };
  }
  const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const joined = lines.join(" ").toLowerCase();
  const serviceMatch = text.match(/(?:service|svc|app)\s*[:=]\s*([a-z0-9._-]+)/i) || text.match(/\b([a-z0-9._-]+-api|[a-z0-9._-]+-worker)\b/i);
  const severityMatch = text.match(/\b(P\d+)\b/i) || text.match(/\b(critical|urgent|high|medium|normal|low|info)\b/i);
  const tenantMatches = matchTenantServiceHints(text, tenantServiceHints);

  let signature = "General incident";
  if (joined.includes("queue_backlog") || joined.includes("consumer_lag") || joined.includes("backlog threshold exceeded")) {
    signature = "Queue / worker backlog";
  } else if (joined.includes("deploy completed") || joined.includes("rollback") || joined.includes("status=500") || joined.includes("status=502")) {
    signature = "Deploy regression / 5xx spike";
  } else if (joined.includes("pool exhausted") || joined.includes("postgres") || joined.includes("database") || joined.includes("session scope")) {
    signature = "Database / session leak";
  } else if (joined.includes("token validation") || joined.includes("jwks") || joined.includes("unauthorized") || joined.includes("auth dependency")) {
    signature = "Auth dependency slowdown";
  } else if (joined.includes("timeout")) {
    signature = "Timeout / queue pressure";
  } else if (joined.includes("memory") || joined.includes("rss")) {
    signature = "Memory pressure / leak";
  } else if (joined.includes("panic") || joined.includes("exception") || joined.includes("traceback")) {
    signature = "Unhandled exception";
  }

  const service = serviceMatch?.[1] || tenantMatches[0] || "checkout-api";
  const serviceSource = serviceMatch?.[1] ? "explicit" : tenantMatches[0] ? "tenant_hint" : "defaulted";
  const severity = severityMatch?.[1]?.toUpperCase() || "P2";
  const severitySource = severityMatch?.[1] ? "explicit" : "default";
  const quality = computePreviewQuality({
    service,
    severity,
    signature,
    lines,
    serviceSource,
    severitySource,
    tenantMatches,
  });

  return {
    service,
    severity,
    signature,
    action: "Open incident workspace",
    summary: lines[0] || "Paste raw incident text to preview the parsed evidence.",
    posture: quality.posture,
    missingSignals: quality.missingSignals.length ? quality.missingSignals : ["None"],
    hintSource: quality.hintSource,
    operatorRead: quality.operatorRead,
  };
}

async function signWebhookPayload(body) {
  const encodedKey = new TextEncoder().encode(WEBHOOK_SECRET);
  const key = await window.crypto.subtle.importKey(
    "raw",
    encodedKey,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const encodedBody = new TextEncoder().encode(body);
  const signature = await window.crypto.subtle.sign("HMAC", key, encodedBody);
  const bytes = Array.from(new Uint8Array(signature));
  return `sha256=${bytes.map((byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

function setActiveChannel(card, cards) {
  const channel = CHANNELS[card.dataset.channel];
  if (!channel) {
    return;
  }

  cards.forEach((node) => {
    node.classList.remove("active");
    node.setAttribute("aria-pressed", "false");
  });
  card.classList.add("active");
  card.setAttribute("aria-pressed", "true");

  updateField("channelPreview", `${channel.label}: ${channel.summary}`);
  updateField("channelAuth", `Auth: ${channel.auth}`);
  updateField("channelNextStep", channel.next);
  updateField("channelPayload", channel.previewPayload || channel.payload);

  const launch = document.getElementById("channelLaunch");
  if (launch) {
    launch.href = incidentHref(channel.incidentId);
    launch.textContent = channel.launchLabel;
    launch.dataset.incidentId = channel.incidentId;
  }

  updateInputField("serviceName", channel.service);
  updateInputField("severity", channel.severity);
  updateInputField("summary", channel.overview);
  updateInputField("symptoms", channel.symptoms);
  const rawLogInput = document.getElementById("rawLogInput");
  if (rawLogInput) {
    if (card.dataset.channel !== "raw_text") {
      rawLogInput.value = channel.payload;
      rawLogInput.dataset.autofilled = "1";
    } else if (rawLogInput.dataset.autofilled === "1") {
      rawLogInput.value = "";
      rawLogInput.dataset.autofilled = "0";
    }
    renderRawLogPreview(rawLogInput.value);
  }

  const endpoint = document.getElementById("channelEndpoint");
  if (endpoint) {
    endpoint.textContent = card.dataset.channel === "manual_form"
      ? "POST /api/v1/incidents/manual-report"
      : card.dataset.channel === "raw_text"
        ? "POST /api/v1/incidents/raw-text"
      : card.dataset.channel === "batch_import"
        ? "POST /api/v1/incidents/batch-import"
        : card.dataset.channel === "webhook"
          ? "POST /webhooks/incident"
          : "Preview only: no live write endpoint yet";
  }

  const submit = document.getElementById("channelSubmit");
  if (submit) {
    const label = card.dataset.channel === "raw_text"
      ? "Submit raw logs"
      : card.dataset.channel === "manual_form"
      ? "Submit manual report"
      : card.dataset.channel === "batch_import"
        ? "Run batch import"
        : card.dataset.channel === "webhook"
          ? "Send webhook intake"
          : "Preview intake only";
    submit.textContent = label;
    submit.disabled = !["raw_text", "manual_form", "batch_import", "webhook"].includes(card.dataset.channel);
  }

  syncChannelLaunchLiveReasoning();

  const result = document.getElementById("channelResult");
  if (result) {
    result.textContent = card.dataset.channel === "raw_text"
      ? selectedDemoBundle
        ? `Selected bundle: ${selectedDemoBundle.title}. Submit these logs to preserve the same story in the fresh incident workspace.`
        : "Paste raw logs or load the example to preview parsed evidence. For Docker-backed REPLICA replay after intake, start NEXUS with NEXUS_ENABLE_REPLICA_RUNTIME=1."
      : "No intake parsed yet. For Docker-backed REPLICA replay after intake, start NEXUS with NEXUS_ENABLE_REPLICA_RUNTIME=1.";
  }
}

function renderRawLogPreview(rawText) {
  const parsed = parseRawLogText(rawText);
  updateField("rawDetectedService", parsed.service);
  updateField("rawDetectedSeverity", parsed.severity);
  updateField("rawDetectedSignature", parsed.signature);
  updateField("rawDetectedAction", parsed.action);
  updateField("rawDetectedPosture", parsed.posture);
  updateField("rawMissingSignals", parsed.missingSignals.join(", "));
  updateField("rawHintSource", parsed.hintSource);
  updateField("rawOperatorRead", parsed.operatorRead);

  const result = document.getElementById("channelResult");
  if (result) {
    result.textContent = parsed.service === "-"
      ? "Paste raw logs or click Load example logs to preview parsed evidence."
      : selectedDemoBundle
        ? `Loaded ${selectedDemoBundle.title}. Parsed ${parsed.service} as ${parsed.severity} with ${parsed.signature.toLowerCase()}. Intake posture is ${parsed.posture.toLowerCase()}.`
        : `Parsed ${parsed.service} as ${parsed.severity} with ${parsed.signature.toLowerCase()}. Intake posture is ${parsed.posture.toLowerCase()}. Runtime-backed replay becomes available when NEXUS_ENABLE_REPLICA_RUNTIME=1 is enabled.`;
  }
}

function renderDemoBundleDetails(bundle) {
  updateField("demoBundleTitle", bundle?.title || "No demo bundle selected yet");
  updateField(
    "demoBundleProof",
    bundle?.proof
      ? `What this proves: ${bundle.proof}`
      : "Choose a bundle to explain what the logs should prove, which team the case should route to, and what kind of bounded runtime or debugging evidence to expect."
  );
  updateField("demoBundleExpectedFamily", bundle?.family || "Select a bundle");
  updateField("demoBundleExpectedOwner", bundle?.likely_owner || "Select a bundle");
  updateField("demoBundleRuntimePosture", bundle?.runtime_posture || "Select a bundle");
  updateField("demoBundleTracePosture", bundle?.trace_posture || "Select a bundle");
  updateField("demoBundleExpectedPath", bundle?.expected_path || "SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN");
  updateField("demoBundleNextStep", bundle?.next_step || "Choose a bundle to see what the operator should watch for after submit.");
}

function renderDemoBundleList() {
  const container = document.getElementById("demoBundleList");
  if (!container) {
    return;
  }
  if (!demoBundles.length) {
    container.innerHTML = `<div class="section-note">Curated demo bundles are unavailable right now. You can still paste your own logs below.</div>`;
    return;
  }
  container.innerHTML = demoBundles
    .map(
      (bundle) => `
        <button class="demo-bundle-btn${selectedDemoBundle?.id === bundle.id ? " is-active" : ""}" type="button" data-demo-bundle-id="${escapeHtml(bundle.id)}">
          <div class="demo-bundle-btn-top">
            <div>
              <strong>${escapeHtml(bundle.title)}</strong>
              <div class="section-note">${escapeHtml(bundle.family)}</div>
            </div>
            <span class="demo-bundle-pill">${escapeHtml(bundle.incident_hint || "Demo")}</span>
          </div>
          <div class="section-note">${escapeHtml(bundle.proof)}</div>
        </button>
      `
    )
    .join("");
}

async function loadDemoBundles() {
  try {
    const response = await fetch(DEMO_BUNDLES_URL, { headers: demoAuthHeaders() });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    demoBundles = Array.isArray(payload?.bundles) ? payload.bundles : [];
  } catch {
    demoBundles = [];
  }
  renderDemoBundleList();
  renderDemoBundleDetails(selectedDemoBundle);
}

async function applyDemoBundle(bundle, cards) {
  if (!bundle) {
    return;
  }
  selectedDemoBundle = bundle;
  renderDemoBundleList();
  renderDemoBundleDetails(bundle);

  const rawTextCard = cards.find((card) => card.dataset.channel === "raw_text");
  if (rawTextCard) {
    setActiveChannel(rawTextCard, cards);
  }

  const rawLogInput = document.getElementById("rawLogInput");
  if (!rawLogInput) {
    return;
  }

  try {
    const response = await fetch(bundle.log_path, { headers: demoAuthHeaders() });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const logText = await response.text();
    rawLogInput.value = logText;
    rawLogInput.dataset.autofilled = "1";
    renderRawLogPreview(rawLogInput.value);
    const result = document.getElementById("channelResult");
    if (result) {
      result.textContent = `Loaded ${bundle.title}. Submit these logs to open a fresh incident that carries the same stakeholder story into the incident workspace.`;
    }
  } catch {
    const result = document.getElementById("channelResult");
    if (result) {
      result.textContent = `Could not load ${bundle.title}. You can still paste your own logs below.`;
    }
  }
}

async function loadTenantInputHints() {
  try {
    const config = await fetchAuthedJson("/api/v1/tenant/bootstrap-config");
    const repos = config?.repos && typeof config.repos === "object" ? Object.keys(config.repos) : [];
    tenantServiceHints = repos.filter(Boolean);
  } catch {
    tenantServiceHints = [];
  }
}

function syncChannelLaunchLiveReasoning() {
  const launch = document.getElementById("channelLaunch");
  if (!launch?.dataset.incidentId) {
    return;
  }
  const liveReasoning = getLiveReasoningPreference() ? "1" : "0";
  launch.href = incidentHref(launch.dataset.incidentId, liveReasoning);
}

function setSubmitProgress(step = 0) {
  [1, 2, 3].forEach((index) => {
    const node = document.getElementById(`submitProgressStep${index}`);
    if (!node) {
      return;
    }
    node.classList.toggle("is-active", index === step);
    node.classList.toggle("is-complete", step > index);
  });
}

function setSubmissionPending(pending, label = "") {
  const submit = document.getElementById("channelSubmit");
  const launch = document.getElementById("channelLaunch");
  const loadExample = document.getElementById("loadRawExample");
  if (submit) {
    if (!submit.dataset.defaultLabel) {
      submit.dataset.defaultLabel = submit.textContent || "Submit";
    }
    submit.disabled = pending;
    submit.dataset.pending = pending ? "1" : "0";
    submit.textContent = pending ? (label || "Submitting intake...") : (submit.dataset.defaultLabel || submit.textContent);
  }
  if (launch) {
    launch.classList.toggle("is-disabled", pending);
    launch.setAttribute("aria-disabled", pending ? "true" : "false");
    launch.style.pointerEvents = pending ? "none" : "";
    launch.style.opacity = pending ? "0.55" : "";
  }
  if (loadExample) {
    loadExample.disabled = pending;
  }
  if (!pending) {
    setSubmitProgress(0);
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  const cards = Array.from(document.querySelectorAll(".input-channel-card"));
  let selectedChannel = cards.find((card) => card.dataset.channel === "raw_text") || cards[0];
  cards.forEach((card) => {
    card.addEventListener("click", () => {
      selectedChannel = card;
      setActiveChannel(card, cards);
    });
  });

  const defaultCard = selectedChannel;
  if (defaultCard) {
    setActiveChannel(defaultCard, cards);
  }
  setSubmitProgress(0);

  const rawLogInput = document.getElementById("rawLogInput");
  rawLogInput?.addEventListener("input", () => {
    rawLogInput.dataset.autofilled = "0";
    renderRawLogPreview(rawLogInput.value);
  });

  const loadExampleButton = document.getElementById("loadRawExample");
  loadExampleButton?.addEventListener("click", async () => {
    if (!rawLogInput) {
      return;
    }
    if (selectedDemoBundle) {
      await applyDemoBundle(selectedDemoBundle, cards);
      return;
    }
    rawLogInput.value = RAW_LOG_EXAMPLE;
    rawLogInput.dataset.autofilled = "1";
    renderRawLogPreview(rawLogInput.value);
  });

  const bundleList = document.getElementById("demoBundleList");
  bundleList?.addEventListener("click", async (event) => {
    const button = event.target instanceof Element ? event.target.closest("[data-demo-bundle-id]") : null;
    if (!button) {
      return;
    }
    const bundle = demoBundles.find((item) => item.id === button.getAttribute("data-demo-bundle-id"));
    if (!bundle) {
      return;
    }
    await applyDemoBundle(bundle, cards);
  });

  const liveReasoningButton = document.getElementById("liveReasoningToggle");
  const liveReasoningState = document.getElementById("liveReasoningState");
  const syncLiveReasoning = () => {
    const enabled = getLiveReasoningPreference();
    if (liveReasoningState) {
      liveReasoningState.textContent = `Live reasoning: ${enabled ? "ON" : "OFF"}`;
    }
    if (liveReasoningButton) {
      liveReasoningButton.textContent = enabled ? "Turn live reasoning off" : "Turn live reasoning on";
    }
  };
  syncLiveReasoning();
  liveReasoningButton?.addEventListener("click", () => {
    const enabled = !getLiveReasoningPreference();
    setLiveReasoningPreference(enabled);
    syncLiveReasoning();
    syncChannelLaunchLiveReasoning();
  });

  const submitButton = document.getElementById("channelSubmit");
  submitButton?.addEventListener("click", async () => {
    const channel = CHANNELS[selectedChannel?.dataset.channel];
    const result = document.getElementById("channelResult");
    const launch = document.getElementById("channelLaunch");
    if (!channel) {
      return;
    }

    if (!['raw_text', 'manual_form', 'batch_import', 'webhook'].includes(selectedChannel.dataset.channel)) {
      if (result) {
        result.textContent = "This channel is UI-only for now. The console preview still reflects the same incident path.";
      }
      return;
    }

    if (result) {
      result.textContent = "Step 1 of 3: normalizing the intake and opening a bounded incident record.";
    }
    setSubmissionPending(true, "Normalizing intake...");
    setSubmitProgress(1);

    try {
      const service = document.getElementById("serviceName")?.value || channel.service;
      const severity = document.getElementById("severity")?.value || channel.severity;
      const summary = document.getElementById("summary")?.value || channel.overview;
      const symptoms = document.getElementById("symptoms")?.value || channel.symptoms;

      let response;
      if (selectedChannel.dataset.channel === "raw_text") {
        const rawText = rawLogInput?.value || channel.payload;
        const parsed = parseRawLogText(rawText);
        response = await postAuthedJson("/api/v1/incidents/raw-text", {
          raw_text: rawText,
          source_hint: "paste",
          reported_by: "demo-operator",
          team: "platform",
          severity_hint: parsed.severity,
        });
      } else if (selectedChannel.dataset.channel === "manual_form") {
        response = await postAuthedJson("/api/v1/incidents/manual-report", {
          affected_service: service,
          symptoms: symptoms.split(/\n|,/).map((item) => item.trim()).filter(Boolean),
          severity,
          reported_by: "demo-operator",
          team: "platform",
          root_cause_suspected: summary,
          additional_context: summary,
          symptom_start_time: new Date().toISOString(),
          affected_regions: ["us-east-1"],
          affected_hosts: [service],
        });
      } else if (selectedChannel.dataset.channel === "batch_import") {
        response = await postAuthedJson("/api/v1/incidents/batch-import", {
          batch_name: slugify(service || channel.service) || "historical-batch",
          source_uri: "s3://nexus/demo/replay_bundle.csv",
          record_count: 128,
          severity,
        });
      } else {
        const body = JSON.stringify({
          incident_id: `${slugify(service || channel.service) || "incident"}-${Date.now()}`,
          title: summary,
          severity,
          detected_at: new Date().toISOString(),
          monitoring_source: "datadog",
          metrics: {
            service,
            symptoms,
          },
        });
        response = await fetchAuthedJson("/webhooks/incident", {
          method: "POST",
          headers: {
            ...demoAuthHeaders(),
            "content-type": "application/json",
            "x-tenant-id": "tenant-a",
            "x-signature": await signWebhookPayload(body),
          },
          body,
        });
      }

      if (result) {
        result.textContent = `Step 2 of 3: created ${response.nexus_incident_id} with status ${response.status}. Preparing the incident workspace...`;
      }
      setSubmissionPending(true, "Opening workspace...");
      setSubmitProgress(2);
      try {
        window.sessionStorage.setItem(FRESH_TRIAGE_STORAGE_KEY, response.nexus_incident_id);
        if (selectedChannel.dataset.channel === "raw_text" && selectedDemoBundle) {
          persistDemoBundleContext(response.nexus_incident_id, selectedDemoBundle);
        }
      } catch {
        // Ignore storage failures; the incident console still opens normally.
      }
      if (launch) {
        const liveReasoning = getLiveReasoningPreference() ? "1" : "0";
        launch.href = incidentHref(response.nexus_incident_id, liveReasoning);
        launch.dataset.incidentId = response.nexus_incident_id;
        launch.textContent = `Open ${response.nexus_incident_id} incident workspace`;
      }
      syncChannelLaunchLiveReasoning();
      const targetHref = launch?.href;
      if (targetHref) {
        if (result) {
          result.textContent = `Step 3 of 3: opening ${response.nexus_incident_id}. The incident will land at the top summary first, and you can replay the handoff only if you want to inspect the crew transition.`;
        }
        setSubmitProgress(3);
        window.NexusNavigation?.beginRouteTransition?.("Opening incident workspace...");
        window.location.assign(targetHref);
        return;
      }
    } catch (error) {
      if (result) {
        result.textContent = `Submission failed: ${error.message}`;
      }
    } finally {
      setSubmissionPending(false);
    }
  });

  await loadDemoBundles();
  await loadTenantInputHints();
  renderRawLogPreview(rawLogInput?.value || "");
});
