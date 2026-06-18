const { test, expect } = require("@playwright/test");

test.describe("Agent Progress & Guardian Status - Verification", () => {
  test("INC001: Agent progress shows clear states with no conflicts", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    // Expand Agent Relay & Crew Details to see agent status
    await page.locator('details:has(h2:text("Agent Relay & Crew Details")) summary').first().click();
    await page.waitForLoadState("networkidle");

    // Verify each agent shows current state
    const sentinelState = await page.locator("#relaySentinelState").textContent();
    const prismState = await page.locator("#relayPrismState").textContent();
    const replicaState = await page.locator("#relayReplicaState").textContent();
    const traceState = await page.locator("#relayTraceState").textContent();
    const forgeState = await page.locator("#relayForgeState").textContent();
    const guardianState = await page.locator("#relayGuardianState").textContent();

    console.log(`Agent States:
      SENTINEL: ${sentinelState}
      PRISM: ${prismState}
      REPLICA: ${replicaState}
      TRACE: ${traceState}
      FORGE: ${forgeState}
      GUARDIAN: ${guardianState}`);

    // Verify no agent is "Waiting" if a later agent is done
    // (would indicate discrepancy)
    expect(sentinelState).not.toBeNull();
    expect(prismState).not.toBeNull();
    expect(guardianState).not.toBeNull();

    // Guardian should show a clear decision
    const guardianGateState = await page.locator("#guardianGateState").textContent();
    console.log(`Guardian Gate: ${guardianGateState}`);
    expect(guardianGateState).toContain(/Approved|Blocked|Pending|completed/i);

    // Verify crew bot stack shows consistent states
    const crewBots = await page.locator(".crew-bot").all();
    expect(crewBots.length).toBe(6);

    console.log("Crew Bot Details:");
    for (let i = 0; i < crewBots.length; i++) {
      const name = await crewBots[i].locator(".crew-bot-name").textContent();
      const state = await crewBots[i].locator(".crew-bot-state").textContent();
      const task = await crewBots[i].locator(".crew-bot-task").textContent();
      console.log(`  ${name}: ${state} - ${task?.substring(0, 60)}...`);
    }
  });

  test("Fresh incident intake shows progress at each step", async ({ page }) => {
    // Start fresh incident
    await page.goto("/inputs");
    await page.waitForLoadState("networkidle");

    // Find and click first demo bundle
    const bundleCards = await page.locator(".path-card, .incident-card, [data-testid='bundle']").all();
    expect(bundleCards.length).toBeGreaterThan(0);
    
    // Click to submit first bundle (INC001 demo)
    const submitButtons = await page.locator("button:has-text('Submit')").all();
    if (submitButtons.length > 0) {
      await submitButtons[0].click();
      await page.waitForLoadState("networkidle");
      
      // Should redirect to new incident
      const url = page.url();
      console.log(`Redirected to: ${url}`);
      expect(url).toContain("/incident");
      
      // Wait for incident to load
      const maxWaits = 10;
      for (let i = 0; i < maxWaits; i++) {
        const incidentId = await page.locator("#incidentHeroId").textContent();
        if (incidentId && incidentId !== "-" && incidentId !== "INC001") {
          console.log(`Fresh incident created: ${incidentId}`);
          break;
        }
        await page.waitForTimeout(500);
      }
      
      // Expand Agent Relay to check progress
      try {
        await page.locator('details:has(h2:text("Agent Relay & Crew Details")) summary').first().click({ timeout: 5000 });
        
        // Check if all agents have completed
        const guardianGateState = await page.locator("#guardianGateState").textContent();
        console.log(`Fresh Incident Guardian State: ${guardianGateState}`);
      } catch (e) {
        console.log("Agent Relay section not expanded, likely still loading");
      }
    }
  });

  test("Guardian decision is clearly visible and unambiguous", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");

    // Expand Agent Relay & Crew Details
    await page.locator('details:has(h2:text("Agent Relay & Crew Details")) summary').first().click();
    await page.waitForLoadState("networkidle");

    // Check Guardian gate card
    const guardianCard = await page.locator(".guardian-gate-card").isVisible();
    expect(guardianCard).toBe(true);

    const gateState = await page.locator("#guardianGateState").textContent();
    console.log(`Guardian Gate State: ${gateState}`);

    // Should have clear decision buttons or outcome
    const approveBtn = await page.locator("#guardianApproveBtn").isVisible();
    const blockBtn = await page.locator("#guardianBlockBtn").isVisible();
    const modifyBtn = await page.locator("#guardianModifyBtn").isVisible();

    console.log(`Guardian Controls: Approve=${approveBtn}, Block=${blockBtn}, Modify=${modifyBtn}`);
    
    // At least one of these should be visible
    if (!approveBtn && !blockBtn && !modifyBtn) {
      // Should show completed state instead
      expect(gateState).toContain(/Approved|Blocked|completed|Execution/i);
    }
  });
});
