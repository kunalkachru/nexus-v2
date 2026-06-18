const { test } = require("@playwright/test");

test("Click the hidden Approve button and check result", async ({ page }) => {
  const url = "http://127.0.0.1:7860/incident?nexus_incident_id=nxs_f5f470882bfa&live_reasoning=1&return_to=%2Finputs";
  
  await page.goto(url, { waitUntil: "networkidle" });
  
  console.log(`\n${"=".repeat(70)}`);
  console.log("🔵 CLICKING HIDDEN APPROVE BUTTON");
  console.log(`${"=".repeat(70)}\n`);

  // Try to click the hidden button directly (force click)
  try {
    await page.locator("#guardianApproveBtn").click({ force: true });
    console.log(`✅ Clicked "Approve runbook" button (forced)\n`);
    
    // Wait a moment for state to update
    await page.waitForTimeout(2000);
    
    // Check if Guardian state changed
    const bodyText = await page.locator("body").textContent();
    
    if (bodyText.includes("Completed") && bodyText.includes("Guardian")) {
      console.log(`✅ SUCCESS! Guardian state updated to Completed\n`);
    } else if (bodyText.includes("approved")) {
      console.log(`✅ SUCCESS! Incident shows as approved\n`);
    } else {
      console.log(`⚠️ Button clicked but state not yet updated\n`);
    }
    
    // Take screenshot
    await page.screenshot({ path: "/tmp/after-approve-click.png" });
    console.log(`📸 Screenshot saved\n`);
    
  } catch (error) {
    console.log(`❌ Could not click hidden button: ${error.message}\n`);
  }

  console.log(`${"=".repeat(70)}\n`);
});
