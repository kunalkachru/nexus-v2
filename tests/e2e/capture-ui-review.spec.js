const { test } = require("@playwright/test");

test.describe("UI Review - Current State Capture", () => {
  test("Capture Queue/Command Center", async ({ page }) => {
    await page.goto("/queue");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "artifacts/browser/ui-review-01-queue.png", fullPage: true });
    console.log("✓ Queue captured");
  });

  test("Capture Incident Detail (INC001)", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "artifacts/browser/ui-review-02-incident.png", fullPage: true });
    console.log("✓ Incident detail captured");
  });

  test("Capture Training/Learning Controls", async ({ page }) => {
    await page.goto("/training");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: "artifacts/browser/ui-review-03-training.png", fullPage: true });
    console.log("✓ Training captured");
  });
});
