const { test } = require("@playwright/test");

test("Check incident execution state", async ({ page }) => {
  const url = "http://127.0.0.1:7860/incident?nexus_incident_id=nxs_f5f470882bfa&live_reasoning=1&return_to=%2Finputs";
  
  await page.goto(url, { waitUntil: "networkidle" });
  
  console.log(`\n${"=".repeat(70)}`);
  console.log("🔍 CHECKING INCIDENT STATE");
  console.log(`${"=".repeat(70)}\n`);

  const bodyText = await page.locator("body").textContent();

  // Check for execution state
  const isExecuted = bodyText.includes("EXECUTED");
  const isPending = bodyText.includes("PENDING");
  const isApproved = bodyText.includes("Approved");
  const isBlocked = bodyText.includes("Blocked");
  const isDecisionPending = bodyText.includes("Decision pending");

  console.log(`Incident state indicators:\n`);
  console.log(`  "EXECUTED": ${isExecuted ? "✅" : "❌"}`);
  console.log(`  "PENDING": ${isPending ? "✅" : "❌"}`);
  console.log(`  "Approved": ${isApproved ? "✅" : "❌"}`);
  console.log(`  "Blocked": ${isBlocked ? "✅" : "❌"}`);
  console.log(`  "Decision pending": ${isDecisionPending ? "✅" : "❌"}\n`);

  // Check for guardian state
  const guardianWorking = bodyText.includes("Guardian") && bodyText.includes("Working");
  console.log(`Guardian "Working now": ${guardianWorking ? "✅" : "❌"}\n`);

  // Look for any text mentioning buttons/actions
  console.log(`Looking for action indicators...\n`);
  const hasApproveText = bodyText.includes("Approve");
  const hasExecuteText = bodyText.includes("Execute");
  const hasActionText = bodyText.includes("action");
  
  console.log(`  "Approve": ${hasApproveText ? "✅" : "❌"}`);
  console.log(`  "Execute": ${hasExecuteText ? "✅" : "❌"}`);
  console.log(`  "action": ${hasActionText ? "✅" : "❌"}\n`);

  if (isExecuted) {
    console.log(`⚠️  This incident is EXECUTED - no approval needed\n`);
  } else if (isApproved || isBlocked) {
    console.log(`⚠️  This incident already has a GUARDIAN decision\n`);
  } else {
    console.log(`⏳ This incident is waiting for Guardian approval\n`);
  }

  console.log(`${"=".repeat(70)}\n`);
});
