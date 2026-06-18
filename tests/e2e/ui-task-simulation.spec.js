const { test, expect } = require("@playwright/test");

test.describe("UI Task Simulation - Scroll Action Measurement", () => {
  test("Task 1: Incident Detail - Find root cause", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001", { waitUntil: "networkidle" });
    
    console.log("\n=== TASK: Find root cause of incident ===");
    let scrollCount = 0;
    
    // Start at top
    console.log(`[Scroll ${scrollCount}] At top of page`);
    let foundRootCause = await page.evaluate(() => {
      const text = document.body.innerText;
      return text.includes("root cause") || text.includes("Root Cause");
    });
    console.log(`  → Root cause visible? ${foundRootCause}`);
    
    if (!foundRootCause) {
      // Scroll down
      scrollCount++;
      await page.evaluate(() => window.scrollBy(0, 1500));
      await page.waitForTimeout(300);
      console.log(`[Scroll ${scrollCount}] Scrolled 1500px down`);
      
      foundRootCause = await page.evaluate(() => {
        const text = document.body.innerText;
        return text.includes("root cause") || text.includes("Root Cause");
      });
      console.log(`  → Root cause visible? ${foundRootCause}`);
    }
    
    if (!foundRootCause) {
      scrollCount++;
      await page.evaluate(() => window.scrollBy(0, 1500));
      await page.waitForTimeout(300);
      console.log(`[Scroll ${scrollCount}] Scrolled 1500px down`);
      foundRootCause = await page.evaluate(() => {
        const text = document.body.innerText;
        return text.includes("root cause") || text.includes("Root Cause");
      });
      console.log(`  → Root cause visible? ${foundRootCause}`);
    }
    
    console.log(`\n✓ Task complete. Scroll actions needed: ${scrollCount}`);
    expect(foundRootCause).toBe(true);
  });

  test("Task 2: Incident Detail - Find GUARDIAN decision", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001", { waitUntil: "networkidle" });
    
    console.log("\n=== TASK: Find GUARDIAN approval decision ===");
    let scrollCount = 0;
    
    // Start at top
    console.log(`[Scroll ${scrollCount}] At top of page`);
    let foundGuardian = await page.evaluate(() => {
      const text = document.body.innerText;
      return text.includes("GUARDIAN") && text.includes("Completed");
    });
    console.log(`  → GUARDIAN decision visible? ${foundGuardian}`);
    
    if (!foundGuardian) {
      scrollCount++;
      await page.evaluate(() => window.scrollBy(0, 1500));
      await page.waitForTimeout(300);
      console.log(`[Scroll ${scrollCount}] Scrolled 1500px down`);
      foundGuardian = await page.evaluate(() => {
        const text = document.body.innerText;
        return text.includes("GUARDIAN") && text.includes("Completed");
      });
      console.log(`  → GUARDIAN decision visible? ${foundGuardian}`);
    }
    
    if (!foundGuardian) {
      scrollCount++;
      await page.evaluate(() => window.scrollBy(0, 1500));
      await page.waitForTimeout(300);
      console.log(`[Scroll ${scrollCount}] Scrolled 1500px down`);
      foundGuardian = await page.evaluate(() => {
        const text = document.body.innerText;
        return text.includes("GUARDIAN") && text.includes("Completed");
      });
      console.log(`  → GUARDIAN decision visible? ${foundGuardian}`);
    }
    
    console.log(`\n✓ Task complete. Scroll actions needed: ${scrollCount}`);
    expect(foundGuardian).toBe(true);
  });

  test("Task 3: Queue - Understand status in first viewport", async ({ page }) => {
    await page.goto("/queue", { waitUntil: "networkidle" });
    
    console.log("\n=== TASK: Understand 'where am I, what's next' from first viewport (no scroll) ===");
    
    const understood = await page.evaluate(() => {
      const text = document.body.innerText;
      // Check if first viewport tells user what to do
      return text.includes("command center") || text.includes("Command Center") || 
             text.includes("focused operating room");
    });
    
    console.log(`Viewport text contains navigation context? ${understood}`);
    console.log(`✓ Queue first-viewport understandability: ${understood ? "GOOD" : "POOR"}`);
    expect(understood).toBe(true);
  });

  test("Task 4: Incident Detail - Understand status in first viewport", async ({ page }) => {
    await page.goto("/incident?nexus_incident_id=INC001", { waitUntil: "networkidle" });
    
    console.log("\n=== TASK: Understand 'where am I, what's done, what's next' from first viewport (no scroll) ===");
    
    const firstViewport = await page.evaluate(() => {
      return document.body.innerText.substring(0, 2000);
    });
    
    console.log("First viewport content (first 2000 chars):");
    console.log("---");
    console.log(firstViewport);
    console.log("---");
    
    const hasIncidentInfo = firstViewport.includes("INC001") || firstViewport.includes("Timeout");
    const hasStatusInfo = firstViewport.includes("Guardian") || firstViewport.includes("Completed") || 
                          firstViewport.includes("Specialist crew");
    const hasActionGuidance = firstViewport.includes("replay") || firstViewport.includes("next");
    
    console.log(`\n✓ First viewport has:`);
    console.log(`  - Incident identification? ${hasIncidentInfo}`);
    console.log(`  - Agent/status info? ${hasStatusInfo}`);
    console.log(`  - Action guidance? ${hasActionGuidance}`);
    
    const firstViewportUnderstandable = hasIncidentInfo && hasStatusInfo && hasActionGuidance;
    console.log(`\n✓ Overall first-viewport understandability: ${firstViewportUnderstandable ? "GOOD" : "POOR"}`);
  });
});
