import { fetchAuthedJson, loadMetrics } from "./api.js";

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = String(value);
  }
}

function setHtml(id, html) {
  const element = document.getElementById(id);
  if (element) {
    element.innerHTML = html;
  }
}

function titleCase(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function renderBootstrapStatus() {
  try {
    const status = await fetchAuthedJson("/api/v1/tenant/bootstrap-status");
    const isReady = status.is_ready || false;
    setText("bootstrapStatus", isReady ? "Ready ✓" : "Incomplete");
    setText("bootstrapOwners", status.owners_configured ? "✓ Configured" : "⚠ Pending");
    setText("bootstrapRepos", status.repos_configured ? "✓ Configured" : "⚠ Pending");
    setText("bootstrapDelivery", status.delivery_targets_configured ? "✓ Configured" : "⚠ Pending");
    setText("bootstrapPolicy", status.approval_policy_configured ? "✓ Configured" : "⚠ Pending");
    setText("bootstrapPacks", status.enabled_packs_configured ? "✓ Configured" : "⚠ Pending");

    const missingFields = status.missing_fields || [];
    const missingHtml = missingFields.length > 0
      ? missingFields.map(field => `<li>Configure <strong>${titleCase(field)}</strong></li>`).join("")
      : "<li>All required fields are configured. Environment is ready for use.</li>";
    setHtml("bootstrapMissingFields", missingHtml);

    // Show supported outage families
    const supportedFamilies = status.supported_outage_families || [];
    const packCoverage = status.pack_coverage || {};
    const familiesHtml = supportedFamilies.length > 0
      ? supportedFamilies.map(family => {
          const packList = Object.entries(packCoverage)
            .filter(([_, coverage]) => coverage.incident_classes && coverage.incident_classes.some(cls => family.toLowerCase().includes(cls.split('_').join(' '))))
            .map(([packId, _]) => packId);
          const supportLabel = packList.length > 0 ? "✓ Runtime-backed" : "◐ Inference-first";
          return `<li><strong>${family}</strong> — ${supportLabel}</li>`;
        }).join("")
      : "<li>No outage families are currently enabled. Configure enabled_packs to add coverage.</li>";
    setHtml("supportedFamilies", familiesHtml);
  } catch (error) {
    setText("bootstrapStatus", "Error");
    setHtml("bootstrapMissingFields", `<li>Unable to load bootstrap status: ${error.message}</li>`);
    setHtml("supportedFamilies", `<li>Unable to load supported families: ${error.message}</li>`);
  }
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

async function renderRuntimeQueueRecovery() {
  try {
    const health = await fetchAuthedJson("/api/v1/platform/health").catch(() => ({}));
    const runtimeQueue = health.runtime_queue || {};

    const statusColor =
      runtimeQueue.recovery_status === "healthy" ? "✓ Healthy" :
      runtimeQueue.recovery_status === "recovering" ? "◐ Recovering" :
      runtimeQueue.recovery_status === "degraded" ? "⚠ Degraded" :
      "Unknown";

    setText("runtimeQueueRecoveryStatus", statusColor);
    setText("runtimeQueueActiveJobs", runtimeQueue.active_jobs ?? "-");
    setText("runtimeQueueRecoveredJobs", runtimeQueue.recovered_jobs ?? "-");
    setText("runtimeQueueFailedJobs", runtimeQueue.failed_jobs ?? "-");
    setText("runtimeQueueTotalJobs", runtimeQueue.total_jobs ?? "-");
    setText("runtimeQueueMessage", runtimeQueue.message || "No runtime queue data available yet.");
  } catch (error) {
    setText("runtimeQueueRecoveryStatus", "Error");
    setText("runtimeQueueMessage", `Unable to load runtime queue status: ${error.message}`);
  }
}

async function renderDeploymentReadiness() {
  try {
    const health = await fetchAuthedJson("/api/v1/platform/health").catch(() => ({}));
    const readiness = health.deployment_readiness || {};

    const readinessLabel =
      readiness.readiness === "fully_available" ? "✓ Fully Available" :
      readiness.readiness === "partially_available" ? "◐ Partially Available" :
      readiness.readiness === "unavailable" ? "✗ Unavailable" :
      "Unknown";

    const dockerLabel = readiness.docker?.available ? "✓ Available" : "✗ Not available";
    const hostLabel = readiness.runtime_host_relay?.complete ? "✓ Configured" : readiness.runtime_host_relay?.configured ? "⚠ Configured" : "✗ Not configured";
    const packLabel = readiness.pack_root?.accessible ? `✓ Ready (${readiness.pack_root?.pack_count ?? 0} pack(s))` : "✗ Not accessible";

    setText("deploymentReadiness", readinessLabel);
    setText("deploymentDocker", dockerLabel);
    setText("deploymentRuntimeHost", hostLabel);
    setText("deploymentPackRoot", packLabel);
    setText("deploymentMessage", readiness.message || "Deployment readiness data not available.");

    const degradedList = document.getElementById("degradedFeaturesList");
    const degradedFeatures = readiness.degraded_features || [];
    if (degradedList) {
      if (degradedFeatures.length === 0) {
        degradedList.innerHTML = "<li>All features are available.</li>";
      } else {
        degradedList.innerHTML = degradedFeatures
          .map((feature) => `<li>⚠ ${feature}</li>`)
          .join("");
      }
    }
  } catch (error) {
    setText("deploymentReadiness", "Error");
    setText("deploymentMessage", `Unable to load deployment readiness: ${error.message}`);
  }
}

window.addEventListener("load", () => {
  renderBootstrapStatus().catch((error) => {
    const missingFields = document.getElementById("bootstrapMissingFields");
    if (missingFields) {
      missingFields.innerHTML = `<li>Error: ${error.message}</li>`;
    }
  });
  renderSettingsSummary().catch((error) => {
    const cards = document.getElementById("platformStatusCards");
    if (cards) {
      cards.innerHTML = `<div class="summary-card"><div class="label">Settings error</div><div class="value">${error.message}</div></div>`;
    }
  });
  renderRuntimeQueueRecovery().catch((error) => {
    setText("runtimeQueueRecoveryStatus", "Error");
    setText("runtimeQueueMessage", `Error loading runtime queue: ${error.message}`);
  });
  renderDeploymentReadiness().catch((error) => {
    setText("deploymentReadiness", "Error");
    setText("deploymentMessage", `Error loading deployment readiness: ${error.message}`);
  });
});
