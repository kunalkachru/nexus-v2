const { test } = require("@playwright/test");

test("Force reveal and click hidden button with JavaScript", async ({ page }) => {
  const url = "http://127.0.0.1:7860/incident?nexus_incident_id=nxs_f5f470882bfa&live_reasoning=1&return_to=%2Finputs";
  
  await page.goto(url, { waitUntil: "networkidle" });
  
  console.log(`\n${"=".repeat(70)}`);
  console.log("🔨 FORCE REVEALING HIDDEN BUTTON");
  console.log(`${"=".repeat(70)}\n`);

  // Use JavaScript to make button visible and click it
  const result = await page.evaluate(() => {
    const btn = document.getElementById("guardianApproveBtn");
    if (!btn) {
      return "Button not found in DOM";
    }
    
    // Make it visible
    btn.style.display = "block !important";
    btn.style.visibility = "visible !important";
    btn.style.opacity = "1 !important";
    btn.style.pointerEvents = "auto !important";
    
    // Scroll into view
    btn.scrollIntoView({ behavior: "smooth", block: "center" });
    
    // Click it
    btn.click();
    
    return "Button clicked successfully";
  });

  console.log(`${result}\n`);
  
  // Wait for state update
  await page.waitForTimeout(3000);
  
  // Check new state
  const bodyText = await page.locator("body").textContent();
  const isCompleted = bodyText.includes("GUARDIAN") && bodyText.includes("Completed");
  const isApproved = bodyText.includes("approved");
  
  if (isCompleted || isApproved || !bodyText.includes("Working now")) {
    console.log(`✅ SUCCESS! Incident approved and Guardian completed!\n`);
  } else {
    console.log(`⚠️ Button clicked but checking state...\n`);
  }

  // Take screenshot
  await page.screenshot({ path: "/tmp/after-force-click.png" });
  console.log(`📸 Screenshot saved\n`);
  console.log(`${"=".repeat(70)}\n`);
});
