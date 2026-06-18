const { test } = require('@playwright/test');

test('Measure actual Incident Detail scroll depth', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('\n[MEASURING] Opening fresh incident...');
  await page.goto('http://127.0.0.1:7860/incident?nexus_incident_id=nxs_0ca4b181fc19');
  await page.waitForLoadState('networkidle');

  const metrics = await page.evaluate(() => {
    const scrollHeight = document.documentElement.scrollHeight;
    const viewportHeight = window.innerHeight;
    const scrollRatio = (scrollHeight / viewportHeight).toFixed(2);

    console.log(`  Document scroll height: ${scrollHeight}px`);
    console.log(`  Viewport height: ${viewportHeight}px`);
    console.log(`  Scroll depth ratio: ${scrollRatio}x`);

    return { scrollHeight, viewportHeight, scrollRatio };
  });

  console.log(`\n[RESULT] Current Incident Detail scroll depth: ${metrics.scrollRatio}x`);
  console.log(`  (${metrics.scrollHeight}px / ${metrics.viewportHeight}px)`);

  await context.close();
});
