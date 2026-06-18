const { test } = require("@playwright/test");

test("Screenshot user's exact incident page", async ({ page }) => {
  // Load the EXACT URL the user is on
  const url = "http://127.0.0.1:7860/incident?nexus_incident_id=nxs_f5f470882bfa&live_reasoning=1&return_to=%2Finputs";
  
  await page.goto(url, { waitUntil: "networkidle" });
  
  console.log(`\n${"=".repeat(70)}`);
  console.log("📸 TAKING SCREENSHOT OF USER'S EXACT INCIDENT PAGE");
  console.log(`${"=".repeat(70)}\n`);
  console.log(`URL: ${url}\n`);

  // Get viewport info
  const viewport = page.viewportSize();
  console.log(`Viewport: ${viewport.width}x${viewport.height}\n`);

  // Take full page screenshot
  await page.screenshot({ 
    path: "/tmp/user-incident-first-viewport.png",
    fullPage: false  // Just first viewport
  });

  // Also take full page
  await page.screenshot({ 
    path: "/tmp/user-incident-full-page.png",
    fullPage: true
  });

  console.log(`✅ Screenshots saved:\n`);
  console.log(`  1. First viewport: /tmp/user-incident-first-viewport.png`);
  console.log(`  2. Full page: /tmp/user-incident-full-page.png\n`);

  // Get page content analysis
  const bodyText = await page.locator("body").textContent();
  
  console.log(`Page content includes:\n`);
  console.log(`  "Approve": ${bodyText.includes("Approve") ? "✅" : "❌"}`);
  console.log(`  "Block": ${bodyText.includes("Block") ? "✅" : "❌"}`);
  console.log(`  "Guardian": ${bodyText.includes("Guardian") ? "✅" : "❌"}`);
  console.log(`  "GUARDIAN": ${bodyText.includes("GUARDIAN") ? "✅" : "❌"}`);
  console.log(`  "Working now": ${bodyText.includes("Working now") ? "✅" : "❌"}`);
  console.log(`  "Completed": ${bodyText.includes("Completed") ? "✅" : "❌"}\n`);

  console.log(`${"=".repeat(70)}\n`);
});
