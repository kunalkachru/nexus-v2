const { test } = require("@playwright/test");

test("Zoom in on Guardian approval buttons", async ({ page }) => {
  const url = "http://127.0.0.1:7860/incident?nexus_incident_id=nxs_f5f470882bfa&live_reasoning=1&return_to=%2Finputs";
  
  await page.goto(url, { waitUntil: "networkidle" });
  
  // Scroll to bottom to see buttons
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);

  // Find the Guardian buttons
  const approveBtn = await page.locator("#guardianApproveBtn");
  const blockBtn = await page.locator("#guardianBlockBtn");
  const modifyBtn = await page.locator("#guardianModifyBtn");

  // Get their positions
  const approveBounds = await approveBtn.boundingBox();
  const blockBounds = await blockBtn.boundingBox();
  const modifyBounds = await modifyBtn.boundingBox();

  console.log(`\n${"=".repeat(70)}`);
  console.log("🔵 GUARDIAN BUTTON LOCATIONS");
  console.log(`${"=".repeat(70)}\n`);

  if (approveBounds) {
    console.log(`✅ "Approve runbook" button found`);
    console.log(`   Position: Y=${approveBounds.y}px (${Math.round(approveBounds.y / 720 * 100)}% down page)`);
    console.log(`   → This is the LEFTMOST orange button\n`);
  }

  if (blockBounds) {
    console.log(`✅ "Block runbook" button found`);
    console.log(`   Position: Y=${blockBounds.y}px`);
    console.log(`   → This is the MIDDLE orange button\n`);
  }

  if (modifyBounds) {
    console.log(`✅ "Request modification" button found`);
    console.log(`   Position: Y=${modifyBounds.y}px`);
    console.log(`   → This is the RIGHTMOST orange button\n`);
  }

  // Take close-up screenshot of the button area
  if (approveBounds) {
    const minY = Math.max(0, (approveBounds.y || 0) - 100);
    const maxY = Math.max(0, (modifyBounds?.y || approveBounds.y || 0) + 150);
    
    await page.screenshot({
      path: "/tmp/guardian-buttons-closeup.png",
      clip: {
        x: 0,
        y: minY,
        width: 1280,
        height: maxY - minY + 100
      }
    });

    console.log(`📸 Close-up screenshot saved: /tmp/guardian-buttons-closeup.png\n`);
  }

  console.log(`${"=".repeat(70)}\n`);
  console.log(`TO COMPLETE GUARDIAN:\n`);
  console.log(`Scroll to the BOTTOM of the page and click the LEFTMOST orange button:\n`);
  console.log(`[Approve runbook] ← CLICK THIS ONE\n`);
  console.log(`This will complete the incident processing.\n`);
  console.log(`${"=".repeat(70)}\n`);
});
