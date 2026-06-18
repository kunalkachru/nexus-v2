const { test } = require("@playwright/test");

test("Test if TRACE completes on fresh incident", async ({ page }) => {
  // Go to inputs
  await page.goto("http://127.0.0.1:7860/inputs", { waitUntil: "networkidle" });
  
  // Find and click submit
  const submitBtn = await page.locator("button:has-text('Submit')").first();
  console.log(`\n🧪 Submitting fresh incident...`);
  await submitBtn.click();

  // Wait for navigation
  await page.waitForNavigation({ waitUntil: "networkidle", timeout: 60000 }).catch(() => {
    console.log(`⚠️ Navigation timeout - checking current page state...`);
  });

  console.log(`✓ Incident created\n`);
  
  // Monitor TRACE for 25 seconds
  console.log(`⏱️  MONITORING TRACE PROGRESSION (25 seconds):\n`);
  let traceCompleted = false;
  
  for (let i = 0; i < 25; i++) {
    const bodyText = await page.locator("body").textContent();
    
    // Extract agent states
    const traceMatch = bodyText.match(/TRACE[\s\S]{0,100}?(Completed|Working now|Waiting|not_run)/i);
    const forgeMatch = bodyText.match(/FORGE[\s\S]{0,100}?(Completed|Working now|Waiting|not_run)/i);
    const guardianMatch = bodyText.match(/GUARDIAN[\s\S]{0,100}?(Completed|Working now|Waiting|not_run)/i);
    
    const traceState = traceMatch ? traceMatch[1] : "unknown";
    const forgeState = forgeMatch ? forgeMatch[1] : "unknown";
    const guardianState = guardianMatch ? guardianMatch[1] : "unknown";
    
    process.stdout.write(`  ${i}s: TRACE=${traceState.padEnd(12)} FORGE=${forgeState.padEnd(12)} GUARDIAN=${guardianState}\r`);
    
    if (traceState === "Completed") {
      traceCompleted = true;
      console.log(`\n✅ TRACE COMPLETED at ${i}s`);
      break;
    }
    
    if (i === 24) {
      console.log(`\n❌ TRACE DID NOT COMPLETE after 25 seconds`);
    }
    
    await page.waitForTimeout(1000);
  }

  console.log(`\n${"=".repeat(70)}`);
  console.log(`RESULT: TRACE ${traceCompleted ? "✅ COMPLETED" : "❌ DID NOT COMPLETE"}`);
  console.log(`${"=".repeat(70)}\n`);
});
