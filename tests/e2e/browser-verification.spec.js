const { test, expect } = require("@playwright/test");

async function disableLiveReasoning(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("nexus.live_reasoning", "0");
  });
}

test.describe("NEXUS browser verification", () => {
  test.beforeEach(async ({ page }) => {
    await disableLiveReasoning(page);
  });

  test("command center feels agent-first and keeps queue internals secondary", async ({ page }) => {
    await page.goto("/queue");
    await page.waitForLoadState("networkidle");

    await expect(page).toHaveTitle(/Command Center/);
    await expect(page.getByRole("navigation", { name: "Primary" })).toContainText("Command Center");
    await expect(page.getByRole("navigation", { name: "Primary" })).toContainText("Incident Detail");
    await expect(page.getByRole("navigation", { name: "Primary" })).toContainText("Learning & Controls");
    await expect(page.getByRole("navigation", { name: "Primary" })).not.toContainText("Inputs");
    await expect(page.getByRole("navigation", { name: "Primary" })).not.toContainText("History");
    await expect(page.getByRole("navigation", { name: "Primary" })).not.toContainText("Replay");
    await expect(page.getByRole("navigation", { name: "Primary" })).not.toContainText("Settings");

    await expect(page.getByRole("heading", { name: "Turn support chaos into one focused operating room." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Choose your path" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Start from raw logs", exact: true }).first()).toBeVisible();
    await expect(page.getByText("Supported five-family wedge")).toBeVisible();
    await expect(page.locator(".seeded-incident-link")).toHaveCount(5);
    await expect(page.getByText("Agent Crew")).toBeVisible();
    await expect(page.locator(".agent-crew-strip .crew-bot")).toHaveCount(4);
    await expect(page.locator(".crew-bot-name")).toHaveText(["SENTINEL", "PRISM", "FORGE", "GUARDIAN"]);
    await expect(page.locator(".section-collapsible")).not.toHaveAttribute("open", "");
    await expect(page.locator(".queue-list .incident-btn").first()).toContainText(/INC-|INC\d+/);

    await page.screenshot({ path: "artifacts/browser/queue-command-center-default.png", fullPage: true });

    await page.locator(".section-collapsible summary").click();
    await expect(page.locator("#queueControls")).toBeVisible();
    await page.screenshot({ path: "artifacts/browser/queue-command-center-expanded.png", fullPage: true });
  });

  test("incident detail shows autonomous handoffs and hides technical detail by default", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    await expect(page).toHaveTitle(/Incident Detail/);
    await expect(page.getByRole("heading", { name: /INC001/ })).toBeVisible();
    await expect(page.getByText("Specialist crew")).toBeVisible();
    await expect(page.locator(".crew-bot-stack .crew-bot")).toHaveCount(6);
    await expect(page.locator("#handoffCurrentOwnerCaption")).toContainText(/active relay owner|owns the case/i);
    await expect(page.locator("#handoffReceivedPacketMeta")).toContainText(/→|No inbound handoff yet/i);
    await expect(page.locator("#handoffReplayHint")).toContainText(/replay|baton transfer/i);
    await expect(page.getByRole("heading", { name: "Investigation Summary & Operator Path" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Enterprise Task Board" })).toBeVisible();
    await expect(page.locator("#focusRecommendedAction")).toBeVisible();
    await expect(page.locator("#focusRuntimePosture")).toBeVisible();
    await expect(page.locator("#focusInspectHere")).toBeVisible();
    await expect(page.locator(".enterprise-depth-details")).not.toHaveAttribute("open", "");
    await expect(page.getByRole("heading", { name: "What is the incident?" })).toBeVisible();
    await expect(page.locator(".guardian-gate-card .badge")).toHaveText("Governance Bot");
    await expect(page.locator(".byo-key-card .badge")).toHaveText("Bring your own OpenAI key");
    await expect(page.locator(".section-collapsible")).not.toHaveAttribute("open", "");
    await expect(page.locator("#liveReasoningState")).toContainText("OFF");
    await expect(page.locator("#incidentHeroId")).toContainText(/INC(?:-|)\w+/);

    await page.screenshot({ path: "artifacts/browser/incident-detail-default.png", fullPage: true });

    await page.getByRole("button", { name: /Turn live reasoning on/i }).click();
    await expect(page.locator("#liveReasoningState")).toContainText("ON");

    await page.locator(".enterprise-depth-details > summary").click();
    await expect(page.getByText("Memory-grounded context")).toBeVisible();
    await expect(page.locator("#taskBoard .workflow-step")).toHaveCount(8);
    await expect(page.getByText("Investigation depth · REPLICA")).toBeVisible();
    await expect(page.getByText("Investigation depth · TRACE")).toBeVisible();
    await expect(page.getByText("Best mitigation")).toBeVisible();
    await expect(page.getByRole("button", { name: /Run bounded replay/i })).toBeVisible();
    await expect(page.locator("#replicaCapabilityDetail")).toContainText(/Host:|No bounded pack/);
    await expect(page.locator("#replicaHypothesisSummary")).toContainText(/Prove|bounded/);
    await expect(page.locator("#replicaHypothesisChecks")).toContainText("Triggering conditions");
    await expect(page.locator("#replicaReplayLifecycleState")).toContainText("Replay lifecycle");
    await expect(page.locator("#replicaTrustSummary")).toContainText("Replay trust packet");
    await expect(page.locator("#traceInspectionPoint")).not.toContainText("TRACE has not narrowed");
    await expect(page.locator("#traceDeveloperHandoff")).toContainText("trace_ownership_map.json");
    await page.getByRole("button", { name: "Start replay" }).click();
    await expect(page.locator("#handoffReplayState")).toContainText(/Step 1 of|Replay armed/i);
    await expect(page.locator("#handoffCurrentOwner")).toContainText(/PRISM|REPLICA|TRACE|FORGE|GUARDIAN/);
    await page.locator(".section-collapsible summary").click();
    await expect(page.locator("#rawInputText")).toBeVisible();
    await expect(page.locator("#workflowTimeline")).toBeVisible();
    await expect(page.locator("#incidentAuditLogs")).toBeVisible();

    await page.screenshot({ path: "artifacts/browser/incident-detail-expanded.png", fullPage: true });
  });

  test("incident detail does not introduce horizontal overflow at common laptop widths", async ({ page }) => {
    for (const width of [1365, 1280, 1180]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/incident?nexus_incident_id=INC001");
      await page.waitForLoadState("networkidle");

      const layout = await page.evaluate(() => ({
        innerWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        bodyScrollWidth: document.body.scrollWidth,
      }));

      expect(layout.scrollWidth, `document overflow at ${width}px`).toBeLessThanOrEqual(layout.innerWidth);
      expect(layout.bodyScrollWidth, `body overflow at ${width}px`).toBeLessThanOrEqual(layout.innerWidth);
    }
  });

  test("incident detail keeps BYO key masked and request-scoped", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#openaiKeyStatus")).toContainText("No user key attached");
    await page.locator("#openaiApiKeyInput").fill("sk-test-1234567890");
    await page.getByRole("button", { name: "Use this key" }).click();
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#liveReasoningState")).toContainText("ON");
    await expect(page.locator("#openaiKeyStatus")).toContainText("sk-t...7890");
    await expect(page.locator("#openaiKeyStatus")).not.toContainText("sk-test-1234567890");

    await page.getByRole("button", { name: "Clear key" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#openaiKeyStatus")).toContainText("No user key attached");
  });

  test("using a BYO OpenAI key does not cause incident-detail horizontal truncation", async ({ page }) => {
    for (const width of [1365, 1280, 1180]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/incident?nexus_incident_id=INC001");
      await page.waitForLoadState("networkidle");

      await page.locator("#openaiApiKeyInput").fill("sk-test-1234567890");
      await page.getByRole("button", { name: "Use this key" }).click();
      await page.waitForLoadState("networkidle");

      await expect(page.locator("#openaiKeyStatus")).toContainText("sk-t...7890");
      await expect(page.locator("#liveReasoningState")).toContainText("ON");

      const layout = await page.evaluate(() => ({
        innerWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        bodyScrollWidth: document.body.scrollWidth,
      }));

      expect(layout.scrollWidth, `document overflow after key use at ${width}px`).toBeLessThanOrEqual(layout.innerWidth);
      expect(layout.bodyScrollWidth, `body overflow after key use at ${width}px`).toBeLessThanOrEqual(layout.innerWidth);
    }
  });

  test("learning and controls leads with progress while keeping RL artifacts collapsed", async ({ page }) => {
    await page.goto("/training");
    await page.waitForLoadState("networkidle");

    await expect(page).toHaveTitle(/Learning & Controls/);
    await expect(page.getByRole("heading", { name: "Make the last triage legible. Keep the rest of the learning stack in reserve." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Enterprise runtime summary" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Learning summary" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Governance summary" })).toBeVisible();
    await expect(page.locator("#rewardCurve > div")).toHaveCount(30);
    await expect(page.locator("#agentStats .summary-card")).toHaveCount(4);
    await expect(page.locator(".section-collapsible")).not.toHaveAttribute("open", "");

    await page.screenshot({ path: "artifacts/browser/training-learning-controls-default.png", fullPage: true });

    await page.locator(".section-collapsible summary").click();
    await expect(page.locator("#episodeTable")).toBeVisible();
    await expect(page.locator("#trajectoryTable")).toBeVisible();
    await expect(page.locator("#stateMap")).toBeVisible();

    await page.screenshot({ path: "artifacts/browser/training-learning-controls-expanded.png", fullPage: true });
  });

  test("settings exposes runtime-host posture and bounded pack coverage", async ({ page }) => {
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");

    await expect(page).toHaveTitle(/Settings/);
    await expect(page.getByRole("heading", { name: "Runtime Host" })).toBeVisible();
    await expect(page.locator("#runtimeHostState")).toBeVisible();
    await expect(page.locator("#runtimeHostPackCount")).not.toHaveText("-");
    await expect(page.locator("#runtimeHostPacks")).toContainText("checkout-python-fastapi-auth-redis-v1");
  });

  test("advanced routes preserve return context back into the incident console", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    await page.getByRole("link", { name: "Inspect intake" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/inputs(?:\?|$)/);
    await expect(page.getByRole("link", { name: "Back to Incident Detail" })).toBeVisible();

    await page.getByRole("link", { name: /Open incident workspace/i }).click();
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/incident\?[^#]*nexus_incident_id=INC001[^#]*return_to=/);
    await expect(page.getByRole("link", { name: "Back to Input Channels" })).toBeVisible();
    await page.getByRole("link", { name: "Back to Input Channels" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/inputs(?:\?|$)/);

    await page.goto("/replay");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#replayLaunch")).toBeVisible();
    await page.locator("#replayLaunch").click();
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/incident\?[^#]*nexus_incident_id=INC001[^#]*return_to=/);
    await expect(page.getByRole("link", { name: "Back to Replay" })).toBeVisible();
  });

  test("raw log submission opens the created incident with populated agent context", async ({ page }) => {
    await page.goto("/inputs");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#rawDetectedPosture")).toContainText("Awaiting input");
    await expect(page.locator("#rawMissingSignals")).toContainText("Add logs");
    await expect(page.locator("#submitProgress")).toContainText("Normalize intake");
    await expect(page.locator("#submitProgress")).toContainText("Create incident");
    await expect(page.locator("#submitProgress")).toContainText("Open workspace");

    await page.getByRole("button", { name: "Load example logs" }).click();
    await expect(page.locator("#rawDetectedPosture")).toContainText(/Strong|Partial/);
    await expect(page.locator("#rawMissingSignals")).toContainText(/None|Explicit/);
    await page.getByRole("button", { name: "Submit raw logs" }).click();

    await expect(page).toHaveURL(/\/incident\?[^#]*nexus_incident_id=nxs_[a-z0-9]+/i, { timeout: 10000 });
    await expect(page.locator("#incidentTitle")).toContainText("INC-");
    await expect(page.locator("#relayStageBanner")).toContainText("Start at the incident summary first");
    await expect(page.locator("#freshTruthCard")).toBeVisible();
    await expect(page.locator("#freshTruthSummary")).toContainText(/extracted|inferred|uncertainty/i);
    await expect(page.locator("#freshTruthExtractedList")).toContainText(/Service token|Severity hint|Evidence lines/i);
    await expect(page.locator("#sentinelReasoning")).not.toHaveText("Waiting for incident context.");
    await expect(page.locator("#threadSentinelCopy")).not.toHaveText("Waiting for incident context.");
    await expect(page.locator("#guardianReasoning")).toContainText(/Guardian review is pending|recorded|safe/i);
    await expect(page.locator("#replicaHypothesisSummary")).toContainText(/Prove|bounded/);

    const landing = await page.evaluate(() => ({
      scrollY: window.scrollY,
      titleTop: document.getElementById("incidentTitle")?.getBoundingClientRect().top ?? null,
      guardianTop: document.querySelector(".guardian-gate-card")?.getBoundingClientRect().top ?? null,
    }));

    expect(landing.scrollY).toBeLessThan(80);
    expect(landing.titleTop).toBeLessThan(360);
    expect(landing.guardianTop).toBeGreaterThan(landing.titleTop);
  });

  test("inputs offers curated demo bundles that preload a stakeholder-ready outage story", async ({ page }) => {
    await page.goto("/inputs");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Guided demo bundles" })).toBeVisible();
    await expect(page.getByText("Use a bounded outage bundle when you want a fast, truthful stakeholder walkthrough.")).toBeVisible();

    await page.getByRole("button", { name: /Checkout timeout \/ retry amplification/i }).click();
    await expect(page.locator("#demoBundleTitle")).toContainText("Checkout timeout / retry amplification");
    await expect(page.locator("#demoBundleProof")).toContainText(/what this proves/i);
    await expect(page.locator("#demoBundleExpectedFamily")).toContainText(/checkout timeout/i);
    await expect(page.locator("#demoBundleExpectedOwner")).toContainText(/checkout platform/i);
    await expect(page.locator("#demoBundleExpectedPath")).toContainText(/SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN/);
    await expect(page.locator("#rawLogInput")).toHaveValue(/timeout waiting for payment service/i);
    await expect(page.locator("#rawDetectedSignature")).toContainText(/Timeout/i);
  });

  test("bundle-backed raw log submission carries demo origin into the fresh incident workspace", async ({ page }) => {
    await page.goto("/inputs");
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: /DB pool exhaustion \/ session leak/i }).click();
    await page.getByRole("button", { name: "Submit raw logs" }).click();

    await expect(page).toHaveURL(/\/incident\?[^#]*nexus_incident_id=nxs_[a-z0-9]+/i, { timeout: 10000 });
    await expect(page.locator("#demoOriginCard")).toBeVisible();
    await expect(page.locator("#demoOriginTitle")).toContainText("DB pool exhaustion / session leak");
    await expect(page.locator("#demoOriginFamily")).toContainText(/DB pool exhaustion/i);
    await expect(page.locator("#demoOriginOwner")).toContainText(/Checkout Data/i);
    await expect(page.locator("#demoOriginNextStep")).toContainText(/runtime comparison/i);
  });

  // ── NEW TESTS added for items 9-12 ──────────────────────────────────────────

  // Item 12: runtime comparison block must be present and populated
  test("INC001 runtime comparison block shows baseline vs mitigated outcome", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    await page.locator(".enterprise-depth-details > summary").click();
    await expect(page.locator("#runtimeComparisonBlock")).toBeVisible();
    await expect(page.locator("#runtimeBaselineRow")).toBeVisible();
    await expect(page.locator("#runtimeMitigatedRow")).toBeVisible();
    await expect(page.locator("#runtimeRunnerUpRow")).toBeVisible();
    await expect(page.locator("#runtimeOutcomeLabel")).toBeVisible();
    await expect(page.locator("#replicaMitigationLadderSummary")).toContainText(/Stop condition|fallback|bounded/i);
    await expect(page.locator("#replicaMitigationLadderSteps")).toContainText(/Primary|Fallback/);

    const outcomeText = await page.locator("#runtimeOutcomeLabel").textContent();
    expect(/resolved|improved|not improved|inferred/i.test(outcomeText || "")).toBeTruthy();

    await page.screenshot({ path: "artifacts/browser/inc001-runtime-comparison.png", fullPage: true });
  });

  test("INC002 runtime comparison block shows baseline vs mitigated outcome", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC002");
    await page.waitForLoadState("networkidle");

    await page.locator(".enterprise-depth-details > summary").click();
    await expect(page.locator("#runtimeComparisonBlock")).toBeVisible();
    await expect(page.locator("#runtimeBaselineRow")).toBeVisible();
    await expect(page.locator("#runtimeMitigatedRow")).toBeVisible();
    await expect(page.locator("#runtimeRunnerUpRow")).toBeVisible();
    await expect(page.locator("#runtimeOutcomeLabel")).toBeVisible();

    const outcomeText = await page.locator("#runtimeOutcomeLabel").textContent();
    expect(/resolved|improved|not improved|inferred/i.test(outcomeText || "")).toBeTruthy();

    await page.screenshot({ path: "artifacts/browser/inc002-runtime-comparison.png", fullPage: true });
  });

  // Item 11: TRACE inspection_point must cite real code — not placeholder text
  test("INC001 TRACE inspection point cites real module or function", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    const inspectionText = await page.locator("#traceInspectionPoint").textContent();
    expect(inspectionText).not.toContain("Wait for REPLICA");
    expect(inspectionText).not.toContain("TRACE has not narrowed");
    expect(/middleware|retry|circuit.?breaker|auth|gateway|timeout/i.test(inspectionText || "")).toBeTruthy();
    await expect(page.locator("#traceDeveloperHandoff")).toContainText("trace_ownership_map.json");
    await expect(page.locator("#traceStackSummary")).toContainText(/gateway timeout guard|retry policy|bounded stack/i);
    await expect(page.locator("#traceRuntimeClue")).toContainText(/runtime|replay|504/i);
    await expect(page.locator("#traceStackPath")).toContainText(/gateway\.timeout_guard|auth\.middleware\.retry/);
    await expect(page.locator("#traceDebuggerSummary")).toContainText(/Bounded debugger packet|timeout\/retry outage|curated 504 replay/i);
    await expect(page.locator("#traceDebuggerChecks")).toContainText(/retry_count|timeout_budget_ms_remaining|circuit_state/);
  });

  // Items 9 & 10: FORGE reasoning cites runtime; GUARDIAN posture is non-generic
  test("INC001 FORGE reasoning cites runtime outcome and GUARDIAN posture is non-generic", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    const forgeText = await page.locator("#forgeReasoning").textContent();
    expect(/resolved|improved|validated|runtime|mitigation/i.test(forgeText || "")).toBeTruthy();

    const guardianText = await page.locator("#guardianReasoning").textContent();
    expect(guardianText).not.toContain("Waiting for incident context.");
    expect(/reproduced|validated|inferred|runtime|resolved|improved/i.test(guardianText || "")).toBeTruthy();

    await page.screenshot({ path: "artifacts/browser/inc001-forge-guardian-reasoning.png", fullPage: true });
  });
});
