const { test, expect } = require("@playwright/test");

test("Visual inspection of actual incident detail page", async ({ page }) => {
  await page.goto("http://127.0.0.1:8001/incident?nexus_incident_id=INC001");
  await page.waitForLoadState("networkidle");

  // Get full page metrics
  const viewport = page.viewportSize();
  const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const ratio = (scrollHeight / viewport.height).toFixed(2);

  console.log(`\n=== INCIDENT DETAIL PAGE - ACTUAL USER EXPERIENCE ===`);
  console.log(`Viewport: ${viewport.width}x${viewport.height}`);
  console.log(`Full page height: ${scrollHeight}px`);
  console.log(`Scroll ratio: ${ratio}x (user needs ~${Math.ceil(ratio)} full scrolls to reach bottom)`);

  // Get all visible elements at different scroll positions
  const scrollPositions = [0, viewport.height, viewport.height * 2, viewport.height * 3];
  
  for (let i = 0; i < scrollPositions.length; i++) {
    await page.evaluate((pos) => window.scrollTo(0, pos), scrollPositions[i]);
    await page.waitForTimeout(300);
    
    const visibleText = await page.evaluate(() => {
      return document.body.innerText.substring(0, 500);
    });
    
    console.log(`\n--- VIEWPORT ${i} (Scroll position: ${scrollPositions[i]}px) ---`);
    console.log(visibleText.substring(0, 300));
  }

  // Check what sections are collapsed
  const detailsElements = await page.locator("details").count();
  const openDetails = await page.locator("details[open]").count();

  console.log(`\n=== COLLAPSED SECTIONS ===`);
  console.log(`Total collapsible sections: ${detailsElements}`);
  console.log(`Currently open: ${openDetails}`);
  console.log(`Currently collapsed: ${detailsElements - openDetails}`);

  // Take full-page screenshot
  await page.screenshot({ path: "full-page-incident-detail.png", fullPage: true });
  console.log(`\n✅ Full-page screenshot saved: full-page-incident-detail.png`);
  console.log(`✅ User experience verification complete`);
});
