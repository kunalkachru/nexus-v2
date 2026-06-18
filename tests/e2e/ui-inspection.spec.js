const { test, expect } = require("@playwright/test");

test("Inspect actual UI sections on incident detail page", async ({ page }) => {
  await page.goto("http://127.0.0.1:8001/incident?nexus_incident_id=INC001");
  await page.waitForLoadState("networkidle");

  // Get ALL h2 headings visible on the page
  const allHeadings = await page.locator("h2").allTextContents();
  console.log("\n=== ALL H2 HEADINGS VISIBLE ON INCIDENT PAGE ===");
  allHeadings.forEach((h, i) => {
    console.log(`${i + 1}. ${h}`);
  });

  // Get all section headings
  const allSectionHeaders = await page.locator(".section-header h2, summary h2").allTextContents();
  console.log("\n=== ALL SECTION HEADERS (COLLAPSED OR VISIBLE) ===");
  allSectionHeaders.forEach((h, i) => {
    console.log(`${i + 1}. ${h}`);
  });

  // Check for details elements
  const detailsElements = await page.locator("details").count();
  console.log(`\n=== DETAILS ELEMENTS (COLLAPSED SECTIONS) ===`);
  console.log(`Total collapsed sections: ${detailsElements}`);

  const openDetails = await page.locator("details[open]").count();
  console.log(`Currently expanded: ${openDetails}`);

  // Get text content of each details summary
  const summaryTexts = await page.locator("details summary").allTextContents();
  console.log(`\n=== COLLAPSED SECTION TITLES ===`);
  summaryTexts.forEach((text, i) => {
    console.log(`${i + 1}. ${text.trim().substring(0, 80)}...`);
  });

  // Take screenshot of first viewport
  await page.screenshot({ path: "actual-ui-viewport.png" });
  console.log(`\n✅ Screenshot saved: actual-ui-viewport.png`);

  // Get visible text in first viewport
  const viewportText = await page.evaluate(() => {
    const element = document.body;
    return element.innerText.substring(0, 1000);
  });

  console.log("\n=== FIRST VIEWPORT TEXT (first 1000 chars) ===");
  console.log(viewportText);
});
