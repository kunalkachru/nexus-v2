const { test } = require("@playwright/test");

test("Show Guardian section and approval buttons", async ({ page }) => {
  // Go to any incident page
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  console.log(`\n${"=".repeat(70)}`);
  console.log("🔍 FINDING GUARDIAN APPROVAL BUTTONS");
  console.log(`${"=".repeat(70)}\n`);

  // Look for approval/rejection buttons
  const approveBtn = await page.locator("button:has-text(/approve|Approve/i)").first();
  const rejectBtn = await page.locator("button:has-text(/reject|reject|block/i)").first();
  const modifyBtn = await page.locator("button:has-text(/modify|modification|request/i)").first();

  console.log(`Looking for buttons:\n`);
  
  const approveBtnVisible = await approveBtn.isVisible().catch(() => false);
  const rejectBtnVisible = await rejectBtn.isVisible().catch(() => false);
  const modifyBtnVisible = await modifyBtn.isVisible().catch(() => false);

  console.log(`Approve button found: ${approveBtnVisible ? "✅ YES" : "❌ NO"}`);
  console.log(`Reject button found: ${rejectBtnVisible ? "✅ YES" : "❌ NO"}`);
  console.log(`Modify button found: ${modifyBtnVisible ? "✅ YES" : "❌ NO"}\n`);

  // Try to find any card with "Guardian" or "gate"
  const guardianCard = await page.locator("text=/Guardian|gate/i").first();
  const guardianVisible = await guardianCard.isVisible().catch(() => false);
  
  console.log(`Guardian-related section found: ${guardianVisible ? "✅ YES" : "❌ NO"}\n`);

  // Get all buttons on page
  console.log(`All buttons on page:\n`);
  const allButtons = await page.locator("button").allTextContents();
  allButtons.slice(0, 20).forEach((text, i) => {
    console.log(`  ${i + 1}. ${text}`);
  });

  // Take full screenshot
  await page.screenshot({ path: "/tmp/guardian-buttons.png" });
  console.log(`\n📸 Full page screenshot saved\n`);
  console.log(`${"=".repeat(70)}\n`);
});
