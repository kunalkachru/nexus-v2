const { test, expect } = require('@playwright/test');

test('Bug 2: Guardian approval persists after page reload', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('\n[STEP 1] Navigating to /inputs to submit fresh incident...');
  await page.goto('http://127.0.0.1:7860/inputs');
  await page.waitForLoadState('networkidle');

  console.log('[STEP 2] Selecting demo bundle...');
  // Click on the first demo bundle (Checkout timeout)
  const bundleButton = page.locator('button', { hasText: 'Checkout timeout' }).first();
  await bundleButton.click();
  await page.waitForTimeout(500);

  console.log('[STEP 3] Clicking Submit button...');
  const submitButton = page.locator('button', { hasText: 'Submit raw logs' });
  await submitButton.click();

  console.log('[STEP 4] Waiting for incident detail page to load...');
  // Wait for navigation to incident page
  await page.waitForURL(/\/incident\?nexus_incident_id=/);
  const incidentId = new URL(page.url()).searchParams.get('nexus_incident_id');
  console.log(`✓ Fresh incident created: ${incidentId}`);

  console.log('[STEP 5] Waiting for Guardian to appear in Agent Progress...');
  // Wait for Guardian progress element to be visible
  const guardianStatus = page.locator('#agentProgressGuardian');
  await guardianStatus.waitFor({ state: 'visible', timeout: 10000 });
  console.log('✓ Guardian status visible');

  console.log('[STEP 6] Waiting for Guardian to transition from Waiting to Working/Completed (max 25s)...');
  // Monitor the guardian status for state changes
  let finalGuardianState = null;
  let guardianIsWorking = false;

  // Wait up to 25 seconds for GUARDIAN to show as "Working" or for approval options to appear
  const startTime = Date.now();
  while (Date.now() - startTime < 25000) {
    const statusText = await guardianStatus.textContent();
    console.log(`  Current Guardian status: ${statusText}`);

    // Check if approval buttons are visible
    const approveBtnByText = page.locator('button', { hasText: /^Approve runbook$/ });
    const approveBtnVisible = await approveBtnByText.isVisible().catch(() => false);

    if (approveBtnVisible || statusText.includes('Working') || statusText.includes('Completed')) {
      guardianIsWorking = true;
      console.log('✓ Guardian is now active/working');
      break;
    }

    await page.waitForTimeout(1000);
  }

  if (!guardianIsWorking) {
    console.log('⚠ Guardian did not reach "Working" state within 25s. Checking current state...');
    const statusText = await guardianStatus.textContent();
    console.log(`  Guardian status: ${statusText}`);
  }

  console.log('[STEP 7] Looking for Guardian approval buttons...');
  // Try to find by text content
  const approveBtnByText = page.locator('button', { hasText: /Approve runbook/ });
  const blockBtnByText = page.locator('button', { hasText: /Block runbook/ });
  const modifyBtnByText = page.locator('button', { hasText: /Request modification/ });

  let approveBtnExists = await approveBtnByText.isVisible().catch(() => false);

  if (!approveBtnExists) {
    // Scroll down to see if buttons are below the fold
    console.log('[STEP 7b] Scrolling down to find Guardian buttons...');
    await page.evaluate(() => {
      const guardianGate = document.querySelector('.guardian-gate-actions') ||
                           Array.from(document.querySelectorAll('div')).find(el =>
                             el.textContent.includes('Approve') && el.textContent.includes('runbook')
                           );
      if (guardianGate) {
        guardianGate.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
    await page.waitForTimeout(1500);

    approveBtnExists = await approveBtnByText.isVisible().catch(() => false);
  }

  if (!approveBtnExists) {
    throw new Error('Guardian approval buttons not found or not visible. Test cannot proceed.');
  }

  console.log('✓ Guardian approval buttons are visible');

  console.log('[STEP 8] Clicking Approve button...');
  // Use JavaScript to click directly and bypass stability checks
  try {
    await page.evaluate(() => {
      const btn = document.querySelector('#guardianApproveBtn') ||
                  Array.from(document.querySelectorAll('button')).find(b =>
                    b.textContent.includes('Approve') && b.textContent.includes('runbook')
                  );
      if (btn) {
        console.log('Found button, clicking via JavaScript');
        btn.click();
      } else {
        throw new Error('Could not find approve button in DOM');
      }
    });
    await page.waitForTimeout(2000);
    console.log('✓ Approve button clicked via JavaScript');
  } catch (error) {
    console.error('Failed to click button:', error.message);
    throw error;
  }

  // Check if approval was processed
  const approvalConfirm = page.locator('text=/approved|Guardian approved/i');
  const approvalVisible = await approvalConfirm.isVisible().catch(() => false);
  if (approvalVisible) {
    console.log('✓ Approval confirmation visible on page');
  } else {
    console.log('⚠ Approval confirmation text not immediately visible');
  }

  console.log('[STEP 9] Reloading page to test persistence...');
  await page.reload();
  await page.waitForLoadState('networkidle');
  console.log('✓ Page reloaded');

  console.log('[STEP 10] Verifying approval persists after reload...');
  // Wait for Guardian section to be visible again
  await guardianStatus.waitFor({ state: 'visible', timeout: 10000 });

  // Check if approval state is still visible - look for confirmation text or buttons being gone
  const approvalTextAfterReload = page.locator('text=/approved|Guardian approved/i');
  const isApprovalConfirmVisible = await approvalTextAfterReload.isVisible().catch(() => false);

  // Also check if buttons are still visible (they should be gone if approved)
  const approveBtnStillVisible = await approveBtnByText.isVisible().catch(() => false);

  if (isApprovalConfirmVisible) {
    console.log('✓✓✓ PASS: Guardian approval PERSISTED after page reload (confirmation text visible)');
  } else if (!approveBtnStillVisible) {
    console.log('✓✓✓ PASS: Guardian approval PERSISTED after page reload (buttons no longer visible)');
  } else {
    // Try to find any confirmation in the guardian section
    const guardianGateSection = page.locator('.guardian-gate-actions');
    const sectionText = await guardianGateSection.textContent().catch(() => '');

    if (sectionText.includes('approved') || sectionText.includes('Approved')) {
      console.log('✓✓✓ PASS: Guardian approval PERSISTED (shown in section text after reload)');
    } else {
      console.log(`✗✗✗ FAIL: Guardian approval did NOT persist after reload`);
      console.log(`Guardian section content: ${sectionText}`);
      throw new Error('Guardian approval not persisted');
    }
  }

  await context.close();
});
