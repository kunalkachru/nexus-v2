const { test } = require("@playwright/test");

test("Take full page screenshot of current incident", async ({ page }) => {
  // Load any incident
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  console.log(`\nTaking FULL page screenshot...\n`);

  // Scroll to bottom to see all content
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);

  // Take full page screenshot
  await page.screenshot({ path: "/tmp/full-page-all-content.png", fullPage: true });

  console.log(`✅ Full page screenshot saved\n`);
  console.log(`Analyzing page content:\n`);

  // Get all text on page
  const bodyText = await page.locator("body").textContent();
  
  // Check for approval-related text
  const hasApprove = bodyText.includes("Approve");
  const hasBlock = bodyText.includes("Block");
  const hasGuardian = bodyText.includes("Guardian");
  const hasGate = bodyText.includes("gate");
  
  console.log(`Page contains:`);
  console.log(`  "Approve": ${hasApprove ? "✅ YES" : "❌ NO"}`);
  console.log(`  "Block": ${hasBlock ? "✅ YES" : "❌ NO"}`);
  console.log(`  "Guardian": ${hasGuardian ? "✅ YES" : "❌ NO"}`);
  console.log(`  "gate": ${hasGate ? "✅ YES" : "❌ NO"}\n`);

  // Count all buttons
  const buttons = await page.locator("button").count();
  console.log(`Total buttons on page: ${buttons}\n`);
});
