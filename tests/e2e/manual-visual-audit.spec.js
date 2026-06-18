const { test } = require("@playwright/test");

test("Manual visual audit of incident page - what a user ACTUALLY sees", async ({ page }) => {
  // Create a fresh incident first
  await page.goto("http://127.0.0.1:7860/inputs", { waitUntil: "networkidle" });
  
  const submitBtn = await page.locator("button:has-text('Submit')").first();
  await submitBtn.click();
  
  await page.waitForNavigation({ waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(3000);
  
  const currentUrl = page.url();
  const incidentId = new URL(currentUrl).searchParams.get("nexus_incident_id");
  
  console.log(`\n${"=".repeat(80)}`);
  console.log("👁️  MANUAL VISUAL AUDIT - WHAT A NORMAL USER SEES");
  console.log(`${"=".repeat(80)}`);
  console.log(`\nIncident ID: ${incidentId}`);
  console.log(`URL: ${currentUrl}\n`);

  // Wait for full load
  await page.waitForTimeout(5000);

  // Take screenshot of first viewport (what user sees without scrolling)
  await page.screenshot({ 
    path: "/tmp/visual-audit-first-view.png",
    fullPage: false 
  });
  console.log(`📸 Screenshot 1: First viewport (no scrolling) saved\n`);

  // Get text visible in first viewport
  const firstViewText = await page.evaluate(() => {
    const height = window.innerHeight;
    const elements = document.elementsFromPoint(window.innerWidth / 2, height / 2);
    let text = "";
    for (const el of elements) {
      if (el.textContent) {
        text += el.textContent.substring(0, 100) + " | ";
      }
    }
    return text;
  });

  console.log(`Content in first viewport:\n${firstViewText.substring(0, 300)}\n`);

  // Scroll down and take screenshots at different positions
  for (let scroll = 1; scroll <= 5; scroll++) {
    await page.evaluate((pos) => window.scrollTo(0, window.innerHeight * pos), scroll);
    await page.waitForTimeout(300);
    
    const visibleText = await page.locator("body").textContent();
    
    if (visibleText.includes("Guardian") && visibleText.includes("Waiting")) {
      console.log(`✅ Found Guardian section at scroll position ${scroll}`);
      await page.screenshot({ 
        path: `/tmp/visual-audit-guardian-section.png`,
        fullPage: false 
      });
      console.log(`📸 Screenshot 2: Guardian section saved\n`);
      break;
    }
  }

  // Scroll to bottom
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);
  
  await page.screenshot({ 
    path: "/tmp/visual-audit-bottom.png",
    fullPage: false 
  });
  console.log(`📸 Screenshot 3: Bottom of page saved\n`);

  // Take full page
  await page.goto(currentUrl, { waitUntil: "networkidle" });
  await page.screenshot({ 
    path: "/tmp/visual-audit-full-page.png",
    fullPage: true 
  });
  console.log(`📸 Screenshot 4: Full page saved\n`);

  console.log(`${"=".repeat(80)}\n`);
  console.log(`Incident created for manual review: ${incidentId}\n`);
  console.log(`URL: ${currentUrl}\n`);
  console.log(`${"=".repeat(80)}\n`);
});
