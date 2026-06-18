const { test } = require("@playwright/test");
const fs = require("fs");

async function measureScreen(page, url, screenName) {
  await page.goto(url, { waitUntil: "networkidle" });
  
  // Get dimensions
  const viewport = page.viewportSize();
  const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const ratio = (scrollHeight / viewport.height).toFixed(2);
  
  console.log(`\n=== ${screenName} ===`);
  console.log(`Viewport: ${viewport.width}x${viewport.height}`);
  console.log(`Full page height: ${scrollHeight}px`);
  console.log(`Scroll depth ratio: ${ratio}x viewport (user needs ~${Math.ceil(ratio)} full scrolls)`);
  
  // Take sequential screenshots at scroll positions
  const numScreenshots = Math.min(Math.ceil(ratio), 10); // Cap at 10 to avoid explosion
  const scrollStep = scrollHeight / numScreenshots;
  
  console.log(`\nTaking ${numScreenshots} sequential viewport screenshots...`);
  
  for (let i = 0; i < numScreenshots; i++) {
    const scrollPos = Math.floor(i * scrollStep);
    await page.evaluate((pos) => window.scrollTo(0, pos), scrollPos);
    await page.waitForTimeout(300); // Let content settle
    
    const filename = `artifacts/browser/ui-measure-${screenName.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${String(i).padStart(2, '0')}.png`;
    await page.screenshot({ path: filename });
    console.log(`  [${i}/${numScreenshots-1}] Position ${scrollPos}px → ${filename}`);
  }
  
  return { screenName, ratio, scrollHeight, viewport };
}

test.describe("UI Measurement - Real Scroll Experience", () => {
  test("Measure Queue", async ({ page }) => {
    await measureScreen(page, "/queue", "Queue");
  });

  test("Measure Incident Detail", async ({ page }) => {
    await measureScreen(page, "/incident?nexus_incident_id=INC001", "Incident Detail");
  });

  test("Measure Training", async ({ page }) => {
    await measureScreen(page, "/training", "Training");
  });
});
