import { demoAuthHeaders, fetchAuthedJson, postAuthedJson } from "./api.js";

const WEBHOOK_SECRET = "nexus-demo-webhook-secret";

const CHANNELS = {
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
    launchLabel: "Open webhook incident console",
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
    launchLabel: "Open manual incident console",
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
    launchLabel: "Open slack incident console",
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
    launchLabel: "Open anomaly incident console",
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
    launchLabel: "Open batch incident console",
  },
};

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
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
  updateField("channelPayload", channel.payload);

  const launch = document.getElementById("channelLaunch");
  if (launch) {
    launch.href = `incident?nexus_incident_id=${encodeURIComponent(channel.incidentId)}`;
    launch.textContent = channel.launchLabel;
  }

  updateInputField("serviceName", channel.service);
  updateInputField("severity", channel.severity);
  updateInputField("summary", channel.overview);
  updateInputField("symptoms", channel.symptoms);

  const endpoint = document.getElementById("channelEndpoint");
  if (endpoint) {
    endpoint.textContent = card.dataset.channel === "manual_form"
      ? "POST /api/v1/incidents/manual-report"
      : card.dataset.channel === "batch_import"
        ? "POST /api/v1/incidents/batch-import"
        : card.dataset.channel === "webhook"
          ? "POST /webhooks/incident"
          : "Preview only: no live write endpoint yet";
  }

  const submit = document.getElementById("channelSubmit");
  if (submit) {
    const label = card.dataset.channel === "manual_form"
      ? "Submit manual report"
      : card.dataset.channel === "batch_import"
        ? "Run batch import"
        : card.dataset.channel === "webhook"
          ? "Send webhook intake"
          : "Preview intake only";
    submit.textContent = label;
    submit.disabled = !["manual_form", "batch_import", "webhook"].includes(card.dataset.channel);
  }

  const result = document.getElementById("channelResult");
  if (result) {
    result.textContent = "No intake submitted yet.";
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const cards = Array.from(document.querySelectorAll(".input-channel-card"));
  let selectedChannel = cards.find((card) => card.dataset.channel === "webhook") || cards[0];
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

  const submitButton = document.getElementById("channelSubmit");
  submitButton?.addEventListener("click", async () => {
    const channel = CHANNELS[selectedChannel?.dataset.channel];
    const result = document.getElementById("channelResult");
    const launch = document.getElementById("channelLaunch");
    if (!channel) {
      return;
    }

    if (!["manual_form", "batch_import", "webhook"].includes(selectedChannel.dataset.channel)) {
      if (result) {
        result.textContent = "This channel is UI-only for now. The console preview still reflects the same incident path.";
      }
      return;
    }

    if (result) {
      result.textContent = "Submitting intake to the backend contract...";
    }

    try {
      const service = document.getElementById("serviceName")?.value || channel.service;
      const severity = document.getElementById("severity")?.value || channel.severity;
      const summary = document.getElementById("summary")?.value || channel.overview;
      const symptoms = document.getElementById("symptoms")?.value || channel.symptoms;

      let response;
      if (selectedChannel.dataset.channel === "manual_form") {
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
        result.textContent = `Created ${response.nexus_incident_id} with status ${response.status}.`;
      }
      if (launch) {
        launch.href = `incident?nexus_incident_id=${encodeURIComponent(response.nexus_incident_id)}`;
        launch.textContent = `Open ${response.nexus_incident_id} incident console`;
      }
    } catch (error) {
      if (result) {
        result.textContent = `Submission failed: ${error.message}`;
      }
    }
  });
});
