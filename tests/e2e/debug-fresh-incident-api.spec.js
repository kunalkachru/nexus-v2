const { test } = require("@playwright/test");

test("Debug fresh incident API response", async ({ page }) => {
  console.log(`\n${"=".repeat(80)}`);
  console.log("🐛 DEBUGGING FRESH INCIDENT CREATION - API RESPONSE");
  console.log(`${"=".repeat(80)}\n`);

  // Intercept network requests
  let apiResponse = null;
  page.on("response", async (response) => {
    if (response.url().includes("/api/v1/incidents")) {
      console.log(`\nAPI Response intercepted:`);
      console.log(`  URL: ${response.url()}`);
      console.log(`  Status: ${response.status()}`);
      try {
        const json = await response.json();
        console.log(`  Body: ${JSON.stringify(json, null, 2).substring(0, 500)}`);
        apiResponse = json;
      } catch (e) {
        console.log(`  (Could not parse JSON)`);
      }
    }
  });

  // Go to inputs
  await page.goto("http://127.0.0.1:7860/inputs", { waitUntil: "networkidle" });
  
  // Click submit
  console.log(`\nClicking submit button...`);
  const submitBtn = await page.locator("button:has-text('Submit')").first();
  await submitBtn.click();

  // Wait for navigation or error
  console.log(`Waiting 10 seconds for API response...`);
  await page.waitForTimeout(10000);

  // Check result
  const resultText = await page.locator("#channelResult").textContent().catch(() => null);
  console.log(`\nResult text on page: ${resultText}`);

  const currentUrl = page.url();
  console.log(`Current URL: ${currentUrl}`);

  if (apiResponse) {
    if (apiResponse.nexus_incident_id) {
      console.log(`\n✅ API returned incident ID: ${apiResponse.nexus_incident_id}`);
    } else {
      console.log(`\n❌ API response has NO nexus_incident_id field`);
      console.log(`Fields present: ${Object.keys(apiResponse).join(", ")}`);
    }
  } else {
    console.log(`\n❌ NO API response captured`);
  }

  console.log(`\n${"=".repeat(80)}\n`);
});
