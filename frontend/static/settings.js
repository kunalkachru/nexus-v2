import { fetchAuthedJson, loadMetrics } from "./api.js";

function setText(id, value) {
  const element = document.getElementById(id);
  if (element && value !== undefined && value !== null) {
    element.textContent = String(value);
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
