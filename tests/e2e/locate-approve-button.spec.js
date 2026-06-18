const { test } = require("@playwright/test");

test("Locate and highlight Approve/Block buttons", async ({ page }) => {
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  console.log(`\n${"=".repeat(70)}`);
  console.log("📍 LOCATING GUARDIAN APPROVAL BUTTONS");
  console.log(`${"=".repeat(70)}\n`);

  // Find the buttons
  const approveBtn = await page.locator('button:has-text("Approve runbook")');
  const blockBtn = await page.locator('button:has-text("Block runbook")');

  // Scroll to them
  await approveBtn.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);

  // Get position
  const approveBox = await approveBtn.boundingBox();
  const blockBox = await blockBtn.boundingBox();

  console.log(`✅ FOUND BUTTONS!\n`);
  console.log(`"Approve runbook" button:`);
  console.log(`  Location: Y=${approveBox?.y}px`);
  console.log(`  Size: ${approveBox?.width}x${approveBox?.height}px\n`);

  console.log(`"Block runbook" button:`);
  console.log(`  Location: Y=${blockBox?.y}px`);
  console.log(`  Size: ${blockBox?.width}x${blockBox?.height}px\n`);

  // Highlight and take screenshot
  await approveBtn.evaluate(el => el.style.border = '3px solid red');
  await blockBtn.evaluate(el => el.style.border = '3px solid red');
  
  await page.screenshot({ 
    path: "/tmp/approve-button-highlighted.png",
    clip: {
      x: Math.max(0, (approveBox?.x || 0) - 100),
      y: Math.max(0, (approveBox?.y || 0) - 150),
      width: 600,
      height: 300
    }
  });

  console.log(`📸 Screenshot taken showing the buttons\n`);
  console.log(`${"=".repeat(70)}\n`);
  console.log(`INSTRUCTIONS:\n`);
  console.log(`1. Scroll down on the incident page`);
  console.log(`2. Look for the two buttons near the Guardian section:\n`);
  console.log(`   🟩 [Approve runbook]  ← Click this to approve\n`);
  console.log(`   🟥 [Block runbook]    ← Or click this to reject\n`);
  console.log(`3. Click one of them`);
  console.log(`4. GUARDIAN will then show as "Completed" ✅\n`);
  console.log(`${"=".repeat(70)}\n`);
});
