import { test, expect } from '@playwright/test';

test('Manual verification: Guardian card and buttons visible in browser', async ({ page, context }) => {
  await page.goto('http://127.0.0.1:7860/incident?nexus_incident_id=INC001');
  await page.waitForLoadState('networkidle');

  // Take a full page screenshot to verify what user sees
  await page.screenshot({ path: 'guardian-card-visibility.png', fullPage: true });
  console.log('Full page screenshot saved to guardian-card-visibility.png');

  // Log all button IDs that exist on the page
  const buttons = await page.locator('button').all();
  console.log(`Total buttons on page: ${buttons.length}`);

  // Look for guardian buttons specifically
  const guardianButtons = await page.locator('button[id*="guardian"]').all();
  console.log(`Guardian buttons found: ${guardianButtons.length}`);

  if (guardianButtons.length > 0) {
    for (const btn of guardianButtons) {
      const id = await btn.getAttribute('id');
      const text = await btn.textContent();
      const isDisabled = await btn.isDisabled();
      console.log(`  - Button: ${id}, Text: "${text}", Disabled: ${isDisabled}`);
    }
  }

  // Check guardian gate card
  const card = page.locator('.guardian-gate-card');
  const cardCount = await card.count();
  console.log(`Guardian gate cards found: ${cardCount}`);

  if (cardCount > 0) {
    const text = await card.first().textContent();
    console.log(`Card preview text: ${text.substring(0, 100)}...`);
  }
});
