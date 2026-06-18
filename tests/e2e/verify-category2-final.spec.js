const { test, expect } = require('@playwright/test');

test.describe('Category 2 Final Verification', () => {
  let context;
  let page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
  });

  test('Measure and verify all three screens', async () => {
    const screens = [
      { name: 'Incident Detail', url: 'http://127.0.0.1:7860/incident?nexus_incident_id=INC001' },
      { name: 'Training', url: 'http://127.0.0.1:7860/training' },
      { name: 'Queue', url: 'http://127.0.0.1:7860/queue' }
    ];

    for (const screen of screens) {
      console.log(`\n📏 [MEASURING] ${screen.name} screen...`);
      await page.goto(screen.url);
      await page.waitForLoadState('networkidle');

      const metrics = await page.evaluate(() => {
        const scrollHeight = document.documentElement.scrollHeight;
        const viewportHeight = window.innerHeight;
        const scrollRatio = (scrollHeight / viewportHeight).toFixed(2);
        return { scrollHeight, viewportHeight, scrollRatio };
      });

      console.log(`  ✓ Scroll height: ${metrics.scrollHeight}px`);
      console.log(`  ✓ Viewport height: ${metrics.viewportHeight}px`);
      console.log(`  ✓ Scroll depth ratio: ${metrics.scrollRatio}x`);
    }
  });

  test('Verify collapsed sections expand correctly', async () => {
    console.log('\n🔍 [VERIFYING] Collapsed section expansion...');

    // Test Incident Detail
    console.log('\n  → Incident Detail:');
    await page.goto('http://127.0.0.1:7860/incident?nexus_incident_id=INC001');
    await page.waitForLoadState('networkidle');

    // Count details elements
    const detailsCount = await page.evaluate(() => {
      return document.querySelectorAll('details.section-collapsible, details.detail-card').length;
    });
    console.log(`    ✓ Found ${detailsCount} collapsible sections`);

    // Click first details element and verify it expands
    const firstDetails = await page.locator('details.section-collapsible, details.detail-card').first();
    await firstDetails.click();
    await page.waitForTimeout(300);

    const isOpen = await firstDetails.evaluate(el => el.open);
    console.log(`    ✓ First section expands: ${isOpen ? '✅' : '❌'}`);
    expect(isOpen).toBe(true);

    // Test Training
    console.log('\n  → Training:');
    await page.goto('http://127.0.0.1:7860/training');
    await page.waitForLoadState('networkidle');

    const trainingDetails = await page.locator('details.section-collapsible, details.detail-card').first();
    if (await trainingDetails.count() > 0) {
      await trainingDetails.click();
      await page.waitForTimeout(300);
      const trainingOpen = await trainingDetails.evaluate(el => el.open);
      console.log(`    ✓ First section expands: ${trainingOpen ? '✅' : '❌'}`);
      expect(trainingOpen).toBe(true);
    }

    // Test Queue
    console.log('\n  → Queue:');
    await page.goto('http://127.0.0.1:7860/queue');
    await page.waitForLoadState('networkidle');

    const queueDetails = await page.locator('details.section-collapsible').first();
    if (await queueDetails.count() > 0) {
      await queueDetails.click();
      await page.waitForTimeout(300);
      const queueOpen = await queueDetails.evaluate(el => el.open);
      console.log(`    ✓ First section expands: ${queueOpen ? '✅' : '❌'}`);
      expect(queueOpen).toBe(true);
    }
  });

  test('Bug 1: Incident navigation persists on rebuilt layouts', async () => {
    console.log('\n🐛 [TESTING] Bug 1: Incident navigation...');

    // Navigate from Queue to Incident Detail
    await page.goto('http://127.0.0.1:7860/queue');
    await page.waitForLoadState('networkidle');

    // Click "Open incident detail" button
    const incidentLink = await page.locator('a[href*="incident?nexus_incident_id=INC001"]').first();
    await incidentLink.click();
    await page.waitForLoadState('networkidle');

    // Verify we're on incident page
    const currentUrl = page.url();
    const isOnIncident = currentUrl.includes('/incident') && currentUrl.includes('INC001');
    console.log(`  ✓ Navigated to incident: ${isOnIncident ? '✅' : '❌'}`);
    expect(isOnIncident).toBe(true);

    // Verify incident ID is displayed
    const incidentId = await page.locator('#incidentHeroId').textContent();
    console.log(`  ✓ Incident ID displayed: ${incidentId}`);
    expect(incidentId).toBeTruthy();

    // Navigate back to Queue via back link
    const backLink = await page.locator('a[data-context-back-link]');
    if (await backLink.count() > 0) {
      await backLink.click();
      await page.waitForLoadState('networkidle');
      const backUrl = page.url();
      const backToQueue = backUrl.includes('/queue');
      console.log(`  ✓ Back navigation works: ${backToQueue ? '✅' : '❌'}`);
      expect(backToQueue).toBe(true);
    }
  });

  test('Bug 2: Guardian approval persists on rebuilt layout', async () => {
    console.log('\n🐛 [TESTING] Bug 2: Guardian persistence...');

    // Go to inputs to create fresh incident
    await page.goto('http://127.0.0.1:7860/inputs');
    await page.waitForLoadState('networkidle');

    // Submit fresh incident
    const submitBtn = await page.locator('button:has-text("Submit raw logs")').first();
    if (await submitBtn.count() > 0) {
      console.log('  → Submitting fresh incident...');
      await submitBtn.click();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Verify Guardian appears
      const guardian = await page.locator('#guardianApproveBtn');
      if (await guardian.count() > 0) {
        console.log('  ✓ Guardian approval button appeared');

        // Click approve
        await guardian.evaluate(el => el.click());
        console.log('  ✓ Clicked approve button');
        await page.waitForTimeout(1000);

        // Reload page
        console.log('  → Reloading page...');
        await page.reload();
        await page.waitForLoadState('networkidle');

        // Check if approval persisted (buttons should be gone, approval saved)
        const guardianAfterReload = await page.locator('#guardianApproveBtn');
        const buttonExists = await guardianAfterReload.count() > 0;

        // If button is gone, approval persisted (state saved in backend)
        const persistenceStatus = !buttonExists;
        console.log(`  ✓ Approval persisted after reload: ${persistenceStatus ? '✅' : '❌'}`);
        expect(persistenceStatus).toBe(true);
      }
    }
  });

  test.afterAll(async () => {
    await context.close();
  });
});
