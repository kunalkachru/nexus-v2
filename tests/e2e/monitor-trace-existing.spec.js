const { test } = require("@playwright/test");

test("Monitor TRACE status on existing incident INC001", async ({ page }) => {
  console.log(`\n${"=".repeat(80)}`);
  console.log("🔍 MONITORING TRACE ON EXISTING INCIDENT (INC001)");
  console.log(`${"=".repeat(80)}\n`);

  // Load existing incident
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  console.log(`✓ Loaded incident INC001\n`);

  // Monitor for 30 seconds
  console.log(`⏱️  MONITORING AGENT STATES (30 seconds)\n`);

  let previousState = null;
  const stateChanges = [];

  for (let second = 0; second < 30; second++) {
    const bodyText = await page.locator("body").textContent();

    // Extract agent states
    const agents = ["SENTINEL", "PRISM", "REPLICA", "TRACE", "FORGE", "GUARDIAN"];
    const states = {};

    agents.forEach((agent) => {
      const regex = new RegExp(
        `${agent}[\\s\\S]{0,150}?(Completed|Working now|Waiting|not_run|error|completed)`,
        "i"
      );
      const match = bodyText.match(regex);
      states[agent] = match ? match[1] : null;
    });

    // Check for changes
    if (JSON.stringify(states) !== JSON.stringify(previousState)) {
      stateChanges.push({ second, states });
      previousState = states;

      console.log(
        `${second}s | S:${(states.SENTINEL || "?").substring(0, 3)} P:${(states.PRISM || "?").substring(0, 3)} R:${(states.REPLICA || "?").substring(0, 3)} T:${(states.TRACE || "?").substring(0, 3)} F:${(states.FORGE || "?").substring(0, 3)} G:${(states.GUARDIAN || "?").substring(0, 3)}`
      );
    }

    await page.waitForTimeout(1000);
  }

  console.log(`\n${"=".repeat(80)}`);
  console.log("📊 STATE CHANGES DETECTED");
  console.log(`${"=".repeat(80)}\n`);

  stateChanges.forEach((change) => {
    console.log(
      `${change.second}s: SENTINEL=${change.states.SENTINEL}, PRISM=${change.states.PRISM}, REPLICA=${change.states.REPLICA}, TRACE=${change.states.TRACE}, FORGE=${change.states.FORGE}, GUARDIAN=${change.states.GUARDIAN}`
    );
  });

  if (stateChanges.length === 0) {
    console.log(`❌ No state changes detected - states remain static\n`);
  } else {
    console.log(`\n✓ Detected ${stateChanges.length} state change(s)\n`);
  }

  const finalState = stateChanges[stateChanges.length - 1]?.states || {};
  console.log(`Final state at 29s:`);
  console.log(`  TRACE: ${finalState.TRACE || "unknown"}`);
  console.log(
    `  TRACE is ${finalState.TRACE === "Completed" ? "✅ COMPLETED" : finalState.TRACE === "Working now" ? "⏳ WORKING NOW" : "❓ " + finalState.TRACE}`
  );
  console.log(`${"=".repeat(80)}\n`);
});
