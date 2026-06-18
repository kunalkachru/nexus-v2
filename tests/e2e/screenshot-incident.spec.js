const { test } = require('@playwright/test');

test('Take screenshot of incident detail page', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();

  await page.goto('http://127.0.0.1:7860/incident?nexus_incident_id=nxs_0ca4b181fc19');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  await page.screenshot({ path: '/tmp/incident-current-layout.png', fullPage: true });
  console.log('Screenshot saved to /tmp/incident-current-layout.png');

  // Also take first viewport only
  await page.screenshot({ path: '/tmp/incident-first-viewport.png' });
  console.log('First viewport screenshot saved');

  await context.close();
});
