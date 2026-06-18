const { test, expect } = require("@playwright/test");

test("Real browser UI inspection - Incident Detail Page", async ({ page }) => {
  // Open incident detail
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });
  
  // Take screenshot of first viewport
  await page.screenshot({ path: "first-viewport-incident-detail.png" });

  const viewport = page.viewportSize();
  const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const firstViewportText = await page.locator("body").textContent();

  console.log(`\n${"=".repeat(80)}`);
  console.log("🔍 REAL BROWSER INSPECTION - INCIDENT DETAIL");
  console.log(`${"=".repeat(80)}`);
  console.log(`\n📏 METRICS:`);
  console.log(`  Viewport: ${viewport.width}x${viewport.height}`);
  console.log(`  Full page height: ${scrollHeight}px`);
  console.log(`  Scroll ratio: ${(scrollHeight / viewport.height).toFixed(2)}x`);
  console.log(`\n📋 FIRST VIEWPORT SHOWS (no scrolling):`);
  console.log(firstViewportText.substring(0, 800));
  console.log(`\n`);

  // Check for specific elements visible in first viewport
  const agentProgressCard = await page
    .locator("text=/Agent Progress|SENTINEL|PRISM|REPLICA/i")
    .first()
    .isVisible()
    .catch(() => false);

  const workingMemory = await page.locator("text=/Working Memory/i").isVisible().catch(() => false);
  const agentRelay = await page.locator("text=/Agent Relay.*Crew/i").isVisible().catch(() => false);

  console.log(`✅ ELEMENTS VISIBLE IN FIRST VIEWPORT:`);
  console.log(`  - Agent Progress Card: ${agentProgressCard ? "✓ YES" : "✗ NO"}`);
  console.log(`  - Working Memory: ${workingMemory ? "✓ YES" : "✗ NO"}`);
  console.log(`  - Agent Relay (expanded): ${agentRelay ? "✓ YES" : "✗ NO"}`);
  console.log(`\n`);

  // Get all agent states from the UI
  const agentStates = await page.evaluate(() => {
    const states = {};
    const agents = ["SENTINEL", "PRISM", "REPLICA", "TRACE", "FORGE", "GUARDIAN"];
    agents.forEach((agent) => {
      const element = document.body.innerText.match(new RegExp(`${agent}[\\s\\S]{0,100}?(Completed|Working now|Waiting|not_run)`, "i"));
      states[agent] = element ? element[1] : "unknown";
    });
    return states;
  });

  console.log(`🤖 AGENT STATES IN CURRENT UI:`);
  Object.entries(agentStates).forEach(([agent, state]) => {
    console.log(`  ${agent.padEnd(12)}: ${state}`);
  });
  console.log(`\n`);

  // Check if page is too long (more than 5 full scrolls)
  const isTooLong = scrollHeight / viewport.height > 5;
  if (isTooLong) {
    console.log(`⚠️  PAGE LENGTH ISSUE:`);
    console.log(`  Page requires ~${Math.ceil(scrollHeight / viewport.height)} full scrolls to reach bottom`);
    console.log(`  This is TOO LONG - user has to scroll excessively\n`);
  }

  // Now test FRESH INCIDENT
  console.log(`${"=".repeat(80)}`);
  console.log("🧪 TESTING FRESH INCIDENT SUBMISSION");
  console.log(`${"=".repeat(80)}\n`);

  // Navigate to inputs page
  await page.goto("http://127.0.0.1:7860/inputs", { waitUntil: "networkidle" });

  // Find and click submit for first demo bundle
  const submitButton = await page.locator("button:has-text('Submit')").first();
  console.log(`Clicking Submit button for first demo bundle...`);
  await submitButton.click();

  // Wait for navigation to new incident
  await page.waitForNavigation({ waitUntil: "networkidle" });
  console.log(`✓ Incident created and navigated to detail page\n`);

  // Monitor TRACE agent state
  console.log(`⏱️  WATCHING TRACE AGENT PROGRESSION (watching for 30 seconds):`);
  const traceProgression = [];
  const startTime = Date.now();

  while (Date.now() - startTime < 30000) {
    const currentStates = await page.evaluate(() => {
      const agents = ["SENTINEL", "PRISM", "REPLICA", "TRACE", "FORGE", "GUARDIAN"];
      const states = {};
      agents.forEach((agent) => {
        const element = document.body.innerText.match(
          new RegExp(`${agent}[\\s\\S]{0,100}?(Completed|Working now|Waiting|not_run)`, "i")
        );
        states[agent] = element ? element[1] : "unknown";
      });
      return states;
    });

    const elapsed = Math.round((Date.now() - startTime) / 1000);
    traceProgression.push({
      time: elapsed,
      states: currentStates,
    });

    process.stdout.write(
      `  ${elapsed}s: TRACE=${currentStates.TRACE} FORGE=${currentStates.FORGE} GUARDIAN=${currentStates.GUARDIAN}  \r`
    );

    // Stop if Guardian completes
    if (currentStates.GUARDIAN === "Completed") {
      console.log(`\n✓ All agents completed at ${elapsed}s`);
      break;
    }

    // Stop if TRACE is stuck for 20+ seconds
    if (elapsed > 20 && currentStates.TRACE === "Working now") {
      console.log(`\n✗ TRACE is STUCK in 'Working now' after ${elapsed}s`);
      break;
    }

    await page.waitForTimeout(1000);
  }

  console.log(`\n`);
  console.log(`📊 TRACE PROGRESSION TIMELINE:`);
  traceProgression.forEach((entry) => {
    if (entry.time % 3 === 0 || entry.states.TRACE !== "Working now") {
      console.log(
        `  ${entry.time}s: SENTINEL=${entry.states.SENTINEL} PRISM=${entry.states.PRISM} REPLICA=${entry.states.REPLICA} TRACE=${entry.states.TRACE} FORGE=${entry.states.FORGE} GUARDIAN=${entry.states.GUARDIAN}`
      );
    }
  });

  const finalStateEntry = traceProgression[traceProgression.length - 1];
  console.log(`\n${"=".repeat(80)}`);
  console.log("✅ TEST COMPLETE");
  console.log(`${"=".repeat(80)}`);
  console.log(`\nFINAL VERDICT:`);
  console.log(`  Agent states at end: ${JSON.stringify(finalStateEntry.states, null, 2)}`);
  console.log(
    `  Time to complete: ${finalStateEntry.time}s (expected ~15s if working, >20s if TRACE hangs)`
  );
  console.log(`\nSCREENSHOT SAVED: first-viewport-incident-detail.png`);
});
