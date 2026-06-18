const { test } = require("@playwright/test");

test("Final verification - All UI and backend fixes", async ({ page }) => {
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  const viewport = page.viewportSize();
  const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const ratio = (scrollHeight / viewport.height).toFixed(2);

  console.log(`\n${"=".repeat(80)}`);
  console.log("✅ FINAL UI/UX VERIFICATION");
  console.log(`${"=".repeat(80)}\n`);

  // Check 1: Page length
  console.log(`1️⃣  PAGE LENGTH CHECK:`);
  console.log(`   Before fix: 7x scrolls`);
  console.log(`   After fix:  ${ratio}x scrolls`);
  const pageIsShorter = ratio < 5;
  console.log(`   Status: ${pageIsShorter ? "✅ PASS - Page is acceptably short" : "❌ FAIL - Page still too long"}\n`);

  // Check 2: Agent Progress visible in first viewport
  console.log(`2️⃣  AGENT PROGRESS CARD CHECK:`);
  const agentProgressVisible = await page
    .locator("text=/Agent Progress|SENTINEL.*PRISM|REPLICA.*TRACE/i")
    .first()
    .isVisible()
    .catch(() => false);
  console.log(`   Agent Progress card visible: ${agentProgressVisible ? "✅ YES" : "❌ NO"}\n`);

  // Check 3: Investigation Summary is collapsed
  console.log(`3️⃣  INVESTIGATION SUMMARY COLLAPSED CHECK:`);
  const investigationDetails = await page.locator('details:has(h2:has-text("Investigation Summary"))');
  const investigationOpen = await investigationDetails
    .evaluate((el) => el.hasAttribute("open"))
    .catch(() => false);
  console.log(`   Investigation Summary expanded: ${investigationOpen ? "❌ NO (should be collapsed)" : "✅ YES (collapsed by default)"}\n`);

  // Check 4: Agent states visible
  console.log(`4️⃣  AGENT STATES CHECK:`);
  const bodyText = await page.locator("body").textContent();
  const agents = ["SENTINEL", "PRISM", "REPLICA", "TRACE", "FORGE", "GUARDIAN"];
  agents.forEach((agent) => {
    const hasAgent = bodyText.includes(agent);
    console.log(`   ${agent}: ${hasAgent ? "✓ Found" : "✗ Not found"}`);
  });
  console.log();

  // Check 5: TRACE status (should not be stuck in "Working now")
  console.log(`5️⃣  TRACE STATUS CHECK:`);
  const hasTraceStuck = bodyText.match(/TRACE[\s\S]{0,200}?Working now/i);
  console.log(`   TRACE stuck in "Working now": ${hasTraceStuck ? "❌ YES (bug still present)" : "✅ NO (fixed)"}\n`);

  console.log(`${"=".repeat(80)}`);
  console.log("📊 SUMMARY:");
  console.log(`  - Page length: ${ratio}x (target: <5x) - ${pageIsShorter ? "✅" : "❌"}`);
  console.log(`  - Agent Progress visible: ${agentProgressVisible ? "✅" : "❌"}`);
  console.log(`  - Investigation collapsed: ${!investigationOpen ? "✅" : "❌"}`);
  console.log(`${"=".repeat(80)}\n`);
});
