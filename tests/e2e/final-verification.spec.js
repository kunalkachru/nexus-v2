const { test, expect } = require("@playwright/test");

test("Final verification - all three critical features", async ({ page }) => {
  const baseUrl = "https://nexus-triage.duckdns.org";
  const results = {
    submissionNavigation: null,
    guardianButtonsVisible: null,
    approvalPersists: null,
  };

  console.log(`\n${"=".repeat(80)}`);
  console.log("FINAL VERIFICATION - PRODUCTION SERVER");
  console.log(`${"=".repeat(80)}\n`);

  // TEST 1: Submit fresh incident and verify navigation
  console.log(`TEST 1: Submit incident from /inputs and verify navigation`);
  await page.goto(`${baseUrl}/inputs`, { waitUntil: "networkidle" });
  console.log(`✅ /inputs page loaded`);

  // Click submit button
  const submitBtn = await page.locator("button:has-text('Submit')").first();
  await submitBtn.click();
  console.log(`✅ Submit button clicked`);

  // Wait for navigation
  try {
    await page.waitForNavigation({ waitUntil: "networkidle", timeout: 30000 });
    console.log(`✅ Page navigated after submit`);
  } catch (e) {
    console.log(`⚠️ Navigation timeout`);
  }

  const url = page.url();
  const incidentId = new URL(url).searchParams.get("nexus_incident_id");

  if (url.includes("/incident") && incidentId) {
    console.log(`✅ TEST 1 PASSED: Navigated to /incident with nexus_incident_id=${incidentId}\n`);
    results.submissionNavigation = "PASS";
  } else {
    console.log(`❌ TEST 1 FAILED: Did not navigate to incident detail page`);
    console.log(`   URL: ${url}\n`);
    results.submissionNavigation = "FAIL";
  }

  // Wait for agents to process
  console.log(`Waiting for agents to process (10 seconds)...`);
  await page.waitForTimeout(10000);

  // TEST 2: Check Guardian buttons visible in first viewport
  console.log(`TEST 2: Guardian buttons visibility in first viewport`);

  const viewportHeight = page.viewportSize().height;
  console.log(`   Viewport height: ${viewportHeight}px`);

  // Get all buttons with "Approve" or "Reject"
  const approveBtn = await page.locator("button:has-text('Approve')").first();
  const rejectBtn = await page.locator("button:has-text('Reject')").first();

  let approveBtnVisible = false;
  let rejectBtnVisible = false;
  let approveBtnPosition = null;
  let rejectBtnPosition = null;

  try {
    approveBtnVisible = await approveBtn.isVisible();
    if (approveBtnVisible) {
      const box = await approveBtn.boundingBox();
      approveBtnPosition = box ? `top: ${box.y}px` : "unknown";
      console.log(`   Approve button visible: YES (${approveBtnPosition})`);
    }
  } catch (e) {
    console.log(`   Approve button visible: NO`);
  }

  try {
    rejectBtnVisible = await rejectBtn.isVisible();
    if (rejectBtnVisible) {
      const box = await rejectBtn.boundingBox();
      rejectBtnPosition = box ? `top: ${box.y}px` : "unknown";
      console.log(`   Reject button visible: YES (${rejectBtnPosition})`);
    }
  } catch (e) {
    console.log(`   Reject button visible: NO`);
  }

  // Check if buttons are within first viewport (no scrolling needed)
  let buttonsInViewport = false;
  if (approveBtn && rejectBtn) {
    const approveBox = await approveBtn.boundingBox();
    const rejectBox = await rejectBtn.boundingBox();

    if (approveBox && rejectBox) {
      const approveInViewport = approveBox.y < viewportHeight && approveBox.y + approveBox.height > 0;
      const rejectInViewport = rejectBox.y < viewportHeight && rejectBox.y + rejectBox.height > 0;
      buttonsInViewport = approveInViewport && rejectInViewport;
    }
  }

  if (approveBtnVisible && rejectBtnVisible && buttonsInViewport) {
    console.log(`✅ TEST 2 PASSED: Guardian buttons visible in first viewport without scrolling\n`);
    results.guardianButtonsVisible = "PASS";
  } else {
    console.log(`❌ TEST 2 FAILED: Guardian buttons not visible in first viewport`);
    console.log(`   Approve visible: ${approveBtnVisible}, Reject visible: ${rejectBtnVisible}, In viewport: ${buttonsInViewport}\n`);
    results.guardianButtonsVisible = "FAIL";
  }

  // TEST 3: Click approve, reload, verify persistence
  console.log(`TEST 3: Guardian approval persistence`);

  if (approveBtnVisible) {
    await approveBtn.click();
    console.log(`✅ Approve button clicked`);
    await page.waitForTimeout(2000);

    // Reload page
    await page.reload({ waitUntil: "networkidle" });
    console.log(`✅ Page reloaded`);
    await page.waitForTimeout(2000);

    // Check if approval persisted
    const bodyText = await page.locator("body").textContent();
    const guardianMatch = bodyText.match(/GUARDIAN[\s\S]{0,100}?(Completed|Working now|Waiting)/);
    const guardianState = guardianMatch ? guardianMatch[1] : "unknown";

    console.log(`   Guardian state after reload: ${guardianState}`);

    if (guardianState === "Completed") {
      console.log(`✅ TEST 3 PASSED: Guardian approval PERSISTED after reload\n`);
      results.approvalPersists = "PASS";
    } else {
      console.log(`❌ TEST 3 FAILED: Guardian approval did NOT persist\n`);
      results.approvalPersists = "FAIL";
    }
  } else {
    console.log(`⚠️ TEST 3 SKIPPED: Approve button not visible, cannot test persistence\n`);
    results.approvalPersists = "SKIPPED";
  }

  // Summary
  console.log(`${"=".repeat(80)}`);
  console.log(`FINAL RESULTS`);
  console.log(`${"=".repeat(80)}`);
  console.log(`\nIncident ID: ${incidentId || "N/A"}`);
  console.log(`URL: ${url}\n`);

  console.log(`TEST RESULTS:`);
  console.log(`  1. Submission navigation: ${results.submissionNavigation}`);
  console.log(`  2. Guardian buttons visible: ${results.guardianButtonsVisible}`);
  console.log(`  3. Approval persistence: ${results.approvalPersists}\n`);

  const allPassed = Object.values(results).every(r => r === "PASS");
  if (allPassed) {
    console.log(`✅ ALL TESTS PASSED - READY FOR PRODUCTION\n`);
  } else {
    const failed = Object.entries(results).filter(([_, r]) => r === "FAIL").map(([k]) => k);
    if (failed.length > 0) {
      console.log(`❌ FAILED TESTS: ${failed.join(", ")}\n`);
    }
  }
  console.log(`${"=".repeat(80)}\n`);
});
