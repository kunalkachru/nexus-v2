const { test, expect } = require("@playwright/test");

test("Verify page length after UI fix", async ({ page }) => {
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  const viewport = page.viewportSize();
  const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  const ratio = (scrollHeight / viewport.height).toFixed(2);

  console.log(`PAGE METRICS: ${scrollHeight}px / ${viewport.height}px = ${ratio}x scrolls`);
  
  // Take screenshot
  await page.screenshot({ path: "verify-page-length.png" });
});
