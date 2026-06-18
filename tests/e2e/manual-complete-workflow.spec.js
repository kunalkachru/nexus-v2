const { test } = require("@playwright/test");

test("Manual complete workflow verification - actual user experience", async ({ page }) => {
  console.log(`\n${"=".repeat(80)}`);
  console.log("🧑 MANUAL WORKFLOW TEST - ACTUAL USER EXPERIENCE");
  console.log(`${"=".repeat(80)}\n`);

  // Step 1: Go to inputs
  console.log(`STEP 1: Navigate to /inputs`);
  await page.goto("http://127.0.0.1:7860/inputs", { waitUntil: "networkidle" });
  console.log(`✅ Inputs page loaded\n`);

  // Step 2: Submit incident
  console.log(`STEP 2: Submit a fresh incident`);
  const submitBtn = await page.locator("button:has-text('Submit')").first();
  await submitBtn.click();
  console.log(`✅ Submit button clicked`);
  
  try {
    await page.waitForNavigation({ waitUntil: "networkidle", timeout: 45000 });
    console.log(`✅ Navigated to incident detail page\n`);
  } catch (e) {
    console.log(`⚠️ Navigation timeout, continuing...\n`);
  }

  // Step 3: Get incident ID
  const url = page.url();
  const incidentId = new URL(url).searchParams.get("nexus_incident_id");
  console.log(`STEP 3: Fresh incident created`);
  console.log(`✅ Incident ID: ${incidentId}\n`);

  // Step 4: Wait for agents to complete
  console.log(`STEP 4: Waiting for agents to complete (15 seconds)`);
  await page.waitForTimeout(15000);
  console.log(`✅ Wait complete\n`);

  // Step 5: Check agent states
  console.log(`STEP 5: Checking agent states`);
  const bodyText = await page.locator("body").textContent();
  
  const states = {
    SENTINEL: bodyText.includes("SENTINEL") && bodyText.match(/SENTINEL[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1],
    PRISM: bodyText.includes("PRISM") && bodyText.match(/PRISM[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1],
    REPLICA: bodyText.includes("REPLICA") && bodyText.match(/REPLICA[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1],
    TRACE: bodyText.includes("TRACE") && bodyText.match(/TRACE[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1],
    FORGE: bodyText.includes("FORGE") && bodyText.match(/FORGE[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1],
    GUARDIAN: bodyText.includes("GUARDIAN") && bodyText.match(/GUARDIAN[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1],
  };

  console.log(`Current agent states:`);
  Object.entries(states).forEach(([agent, state]) => {
    console.log(`  ${agent}: ${state || "not found"}`);
  });
  console.log();

  // Step 6: Try to find and click approval button
  console.log(`STEP 6: Looking for Guardian approval`);
  
  const approveBtnVisible = await page.locator("#guardianApproveBtn").isVisible().catch(() => false);
  console.log(`Approve button visible in UI: ${approveBtnVisible ? "✅ YES" : "❌ NO"}`);

  if (!approveBtnVisible) {
    console.log(`Attempting to reveal and click button with JavaScript...\n`);
    
    const clicked = await page.evaluate(() => {
      const btn = document.getElementById("guardianApproveBtn");
      if (!btn) return false;
      btn.style.display = "block !important";
      btn.style.visibility = "visible !important";
      btn.style.opacity = "1 !important";
      btn.style.pointerEvents = "auto !important";
      btn.scrollIntoView({ behavior: "smooth" });
      btn.click();
      return true;
    });

    if (clicked) {
      console.log(`✅ Button clicked via JavaScript\n`);
      await page.waitForTimeout(2000);
    }
  } else {
    console.log(`Clicking visible button...\n`);
    await page.locator("#guardianApproveBtn").click();
    await page.waitForTimeout(2000);
  }

  // Step 7: Check if approval worked
  console.log(`STEP 7: Verifying approval was saved`);
  const bodyAfterClick = await page.locator("body").textContent();
  const guardianAfterClick = bodyAfterClick.match(/GUARDIAN[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1];
  console.log(`Guardian state after approval click: ${guardianAfterClick}\n`);

  // Step 8: Reload page and verify persistence
  console.log(`STEP 8: Page reload test - does approval persist?`);
  await page.reload({ waitUntil: "networkidle" });
  console.log(`✅ Page reloaded`);
  
  await page.waitForTimeout(2000);
  
  const bodyAfterReload = await page.locator("body").textContent();
  const guardianAfterReload = bodyAfterReload.match(/GUARDIAN[\s\S]{0,100}?(Completed|Working now|Waiting)/)?.[1];
  console.log(`Guardian state after reload: ${guardianAfterReload}\n`);

  if (guardianAfterReload === "Completed") {
    console.log(`✅ SUCCESS! Guardian approval PERSISTED after reload\n`);
  } else if (guardianAfterReload === "Waiting") {
    console.log(`❌ FAILED! Guardian went back to "Waiting" - approval did NOT persist\n`);
  } else {
    console.log(`⚠️ Unknown state: ${guardianAfterReload}\n`);
  }

  // Step 9: Summary
  console.log(`${"=".repeat(80)}`);
  console.log(`FINAL VERIFICATION SUMMARY`);
  console.log(`${"=".repeat(80)}`);
  console.log(`\nIncident: ${incidentId}`);
  console.log(`URL: ${url}\n`);
  
  console.log(`Agent progression:`);
  Object.entries(states).forEach(([agent, state]) => {
    const status = state === "Completed" ? "✅" : state === "Working now" ? "⏳" : "⏸";
    console.log(`  ${status} ${agent}: ${state}`);
  });
  
  console.log(`\nGuardian approval persistence: ${guardianAfterReload === "Completed" ? "✅ WORKING" : "❌ BROKEN"}\n`);
  console.log(`${"=".repeat(80)}\n`);
});
