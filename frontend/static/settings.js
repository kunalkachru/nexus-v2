import { fetchAuthedJson, loadMetrics } from "./api.js";

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

async function renderSettingsSummary() {
  const data = await fetchAuthedJson("/api/v1/platform/status").catch(() => loadMetrics());
  const platform = data.platform_status || data || {};

  setText("platformMode", platform.mode);
  setText("platformAuth", platform.webhook_auth);
  setText("platformPolicies", platform.policy_status);
  setText("platformIntegrations", platform.integrations);
  setText("platformSignature", platform.webhook_signature_verification);

  setText("platformWebhookAuth", platform.webhook_auth);
  setText("platformRateLimiting", platform.rate_limiting);
  setText("platformAuditLogs", platform.audit_logs);
  setText("platformReplayReadiness", platform.replay_readiness);
  setText("platformReplayLaunches", platform.replay_launches);
  setText("platformTrainingSnapshots", platform.training_snapshots);
  setText("platformLearningContracts", platform.learning_contracts);
  setText("platformAuditEvents", platform.audit_events);
  setText("platformGuardianReviews", platform.guardian_reviews);

  const runtimeHost = platform.runtime_host_relay || {};
  setText("runtimeHostState", runtimeHost.status_label || titleCase(runtimeHost.state || "not_configured"));
  setText(
    "runtimeHostReachability",
    runtimeHost.configured
      ? runtimeHost.reachable
        ? "Reachable"
        : "Unreachable"
      : "Not configured"
  );
  setText("runtimeHostPackCount", runtimeHost.pack_count ?? 0);
  setText("runtimeHostAuth", runtimeHost.auth_configured ? "Configured" : "Missing");
  setText("runtimeHostMessage", runtimeHost.message || "Runtime host posture is not available.");
  setText("runtimeHostHealthMessage", runtimeHost.health_message || "Runtime host health details are not available.");
  setText("runtimeHostBaseUrl", runtimeHost.base_url || "No runtime host relay configured.");

  const runtimeHostPacks = document.getElementById("runtimeHostPacks");
  if (runtimeHostPacks) {
    const packs = runtimeHost.supported_packs || [];
    runtimeHostPacks.innerHTML = packs.length
      ? packs
          .map(
            (pack) => `
              <li>
                <strong>${pack.pack_id}</strong><br>
                <span class="section-note">${(pack.stack || []).join(" · ") || "bounded stack"}</span><br>
                <span class="section-note">Outage classes: ${(pack.incident_classes || []).join(", ") || "n/a"}</span>
              </li>
            `
          )
          .join("")
      : "<li>No bounded runtime packs are published for relay execution yet.</li>";
  }

  const intakeContracts = document.getElementById("platformIntakeContracts");
  const readContracts = document.getElementById("platformReadContracts");
  const contractSurface = platform.contract_surface || [];
  if (intakeContracts && readContracts && contractSurface.length) {
    intakeContracts.innerHTML = contractSurface.slice(0, 3).map((item) => `<li><code>${item}</code></li>`).join("");
    readContracts.innerHTML = contractSurface.slice(3).map((item) => `<li><code>${item}</code></li>`).join("");
  }
}

window.addEventListener("load", () => {
  renderSettingsSummary().catch((error) => {
    const cards = document.getElementById("platformStatusCards");
    if (cards) {
      cards.innerHTML = `<div class="summary-card"><div class="label">Settings error</div><div class="value">${error.message}</div></div>`;
    }
  });
});
