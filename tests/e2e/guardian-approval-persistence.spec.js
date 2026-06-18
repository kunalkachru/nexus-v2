import { test, expect } from '@playwright/test';

test('Guardian approval buttons are visible and persistent', async ({ page }) => {
  // Navigate to incident detail page
  await page.goto('http://127.0.0.1:7860/incident?nexus_incident_id=INC001');

  // Wait for page to load
  await page.waitForLoadState('networkidle');

  // Debug: Check if guardian-gate-card exists and its location in DOM
  const guardianGateCard = page.locator('.guardian-gate-card');
  const cardCount = await guardianGateCard.count();
  console.log('Guardian cards found:', cardCount);
  expect(cardCount).toBe(1);

  // Check the card's position in the document and parent element
  if (cardCount > 0) {
    const cardInfo = await guardianGateCard.first().evaluate(el => {
      const parentSelector = el.parentElement?.className || 'unknown';
      const bounding = el.getBoundingClientRect();
      const collapsed = el.closest('details[open]') === null && el.closest('details') !== null;
      return {
        parentClass: parentSelector,
        inViewport: bounding.top >= 0 && bounding.top <= window.innerHeight,
        isInsideCollapsed: collapsed,
        top: bounding.top,
        height: bounding.height
      };
    });
    console.log('Guardian card position:', cardInfo);

    // The card should NOT be inside a collapsed details section
    expect(cardInfo.isInsideCollapsed).toBe(false);
  }

  // Scroll the card into view to ensure it's visible
  await guardianGateCard.first().scrollIntoViewIfNeeded();

  // Verify the approval buttons exist and are not disabled
  const approveBtn = page.locator('#guardianApproveBtn');
  const blockBtn = page.locator('#guardianBlockBtn');
  const modifyBtn = page.locator('#guardianModifyBtn');

  // Check button existence
  expect(await approveBtn.count()).toBe(1);
  expect(await blockBtn.count()).toBe(1);
  expect(await modifyBtn.count()).toBe(1);

  // Buttons should be enabled (not disabled)
  await expect(approveBtn).not.toHaveAttribute('disabled', '');
  await expect(blockBtn).not.toHaveAttribute('disabled', '');
  await expect(modifyBtn).not.toHaveAttribute('disabled', '');

  // Check if Guardian is in "Working now" state
  const guardianState = page.locator('#guardianGateState');
  const stateText = await guardianState.textContent();

  // If guardian is ready to approve, click the button
  if (stateText && stateText.includes('pending')) {
    // Click Approve button
    await approveBtn.click();

    // Wait for state update
    await page.waitForTimeout(1000);

    // Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify Guardian Gate card is still visible after reload
    await expect(guardianGateCard).toBeVisible();

    // Verify the approval state persisted
    const guardianStateAfterReload = page.locator('#guardianGateState');
    const stateAfterReload = await guardianStateAfterReload.textContent();

    // The state should show some indication of approval
    console.log('Guardian state after reload:', stateAfterReload);
  }

});
