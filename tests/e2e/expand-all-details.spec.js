const { test } = require("@playwright/test");

test("Expand all collapsed sections to reveal buttons", async ({ page }) => {
  const url = "http://127.0.0.1:7860/incident?nexus_incident_id=nxs_f5f470882bfa&live_reasoning=1&return_to=%2Finputs";
  
  await page.goto(url, { waitUntil: "networkidle" });
  
  console.log(`\n${"=".repeat(70)}`);
  console.log("🔓 EXPANDING ALL COLLAPSED SECTIONS");
  console.log(`${"=".repeat(70)}\n`);

  // Get all details elements
  const detailsElements = await page.locator("details").all();
  console.log(`Found ${detailsElements.length} collapsed sections\n`);

  // Expand each one
  for (let i = 0; i < detailsElements.length; i++) {
    const element = detailsElements[i];
    const summary = await element.locator("summary").first();
    const summaryText = await summary.textContent();
    
    // Click to expand
    await summary.click();
    await page.waitForTimeout(200);
    
    console.log(`${i + 1}. Expanded: ${summaryText.substring(0, 50)}`);
  }

  console.log(`\n✅ All sections expanded\n`);

  // Now try to find and click the approve button
  await page.waitForTimeout(500);
  const approveBtn = await page.locator("#guardianApproveBtn");
  const isNowVisible = await approveBtn.isVisible().catch(() => false);
  
  console.log(`\nApprove button visible now: ${isNowVisible ? "✅ YES" : "❌ NO"}\n`);

  if (isNowVisible) {
    console.log(`✅ Found! Clicking "Approve runbook"...\n`);
    await approveBtn.click();
    await page.waitForTimeout(2000);
    console.log(`✅ Clicked successfully!\n`);
  }

  console.log(`${"=".repeat(70)}\n`);
});
