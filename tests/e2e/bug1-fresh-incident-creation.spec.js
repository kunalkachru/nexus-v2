const { test } = require("@playwright/test");

test("BUG 1: Fresh incident creation with demo bundle selection", async ({ page }) => {
  console.log(`\n${"=".repeat(80)}`);
  console.log("🐛 BUG 1 TEST: Fresh incident navigation");
  console.log(`${"=".repeat(80)}\n`);

  // Step 1: Go to /inputs
  console.log(`Step 1: Navigate to /inputs`);
  await page.goto("http://127.0.0.1:7860/inputs", { waitUntil: "networkidle" });
  console.log(`✅ /inputs page loaded\n`);

  // Step 2: SELECT a demo bundle (critical - this loads the log content)
  console.log(`Step 2: Select a demo bundle`);
  const firstBundle = await page.locator("[data-demo-bundle-id]").first();
  const bundleId = await firstBundle.getAttribute("data-demo-bundle-id");
  console.log(`  Clicking bundle: ${bundleId}`);
  await firstBundle.click();
  await page.waitForTimeout(2000); // Wait for logs to load
  console.log(`✅ Demo bundle selected\n`);

  // Step 3: Click Submit
  console.log(`Step 3: Submit incident`);
  const submitBtn = await page.locator("#channelSubmit");
  await submitBtn.click();
  console.log(`✅ Submit button clicked`);
  
  // Step 4: Wait for navigation
  console.log(`Step 4: Waiting for navigation (should go from /inputs to /incident?...)...`);
  let navigated = false;
  let incidentId = null;
  
  for (let attempt = 0; attempt < 30; attempt++) {
    await page.waitForTimeout(1000);
    const currentUrl = page.url();
    
    if (currentUrl.includes("/incident?") && currentUrl.includes("nexus_incident_id=")) {
      navigated = true;
      incidentId = new URL(currentUrl).searchParams.get("nexus_incident_id");
      console.log(`\n✅ NAVIGATION SUCCESSFUL!`);
      console.log(`   Navigated to: ${currentUrl}\n`);
      break;
    }
    
    if (attempt % 5 === 0) {
      console.log(`  ${attempt}s: Still on ${currentUrl.split("?")[0]}...`);
    }
  }

  if (!navigated) {
    const finalUrl = page.url();
    console.log(`\n❌ NAVIGATION FAILED`);
    console.log(`   Still on: ${finalUrl}\n`);
    
    // Check error message
    const resultText = await page.locator("#channelResult").textContent();
    console.log(`   Error shown: ${resultText}\n`);
  } else {
    console.log(`✅ TEST PASSED`);
    console.log(`   Incident created: ${incidentId}\n`);
  }

  console.log(`${"=".repeat(80)}\n`);
  return navigated ? "PASS" : "FAIL";
});
