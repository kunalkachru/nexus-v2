const { test } = require("@playwright/test");

test("Find all buttons on incident page", async ({ page }) => {
  const url = "http://127.0.0.1:7860/incident?nexus_incident_id=nxs_f5f470882bfa&live_reasoning=1&return_to=%2Finputs";
  
  await page.goto(url, { waitUntil: "networkidle" });
  
  console.log(`\nSearching for buttons with 'Approve' or 'Block' text:\n`);

  // Get all buttons and their text
  const buttons = await page.locator("button").all();
  
  for (let i = 0; i < buttons.length; i++) {
    const text = await buttons[i].textContent();
    const isVisible = await buttons[i].isVisible();
    
    if (text.includes("Approve") || text.includes("Block") || text.includes("Execute")) {
      console.log(`Button ${i}: "${text.trim()}" ${isVisible ? "✅ VISIBLE" : "❌ HIDDEN"}`);
      
      // Get position
      try {
        const box = await buttons[i].boundingBox();
        if (box) {
          console.log(`  Position: Y=${box.y}px, X=${box.x}px`);
        }
      } catch (e) {
        console.log(`  (position unavailable)`);
      }
    }
  }

  // Scroll to each button and screenshot
  console.log(`\n\nScrolling down and taking final screenshot...\n`);
  
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);
  
  await page.screenshot({ path: "/tmp/bottom-of-page.png", fullPage: false });
  console.log(`✅ Screenshot of bottom saved\n`);
});
