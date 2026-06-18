const { test } = require("@playwright/test");

test("Locate OpenAI key input and take screenshot", async ({ page }) => {
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  // Find the OpenAI key input
  const keyInput = await page.locator("#openaiApiKeyInput");
  const isVisible = await keyInput.isVisible();
  
  console.log(`\n${"=".repeat(70)}`);
  console.log("🔑 OPENAI API KEY INPUT LOCATION");
  console.log(`${"=".repeat(70)}\n`);
  
  if (isVisible) {
    console.log(`✅ OpenAI key input IS VISIBLE on page\n`);
    
    // Get bounding box
    const box = await keyInput.boundingBox();
    console.log(`Location on page:`);
    console.log(`  X: ${box.x}px`);
    console.log(`  Y: ${box.y}px`);
    console.log(`  Size: ${box.width}x${box.height}px\n`);
    
    // Scroll to make it visible if needed
    await keyInput.scrollIntoViewIfNeeded();
    
    // Take screenshot of that area
    await page.screenshot({ 
      path: "/tmp/openai-key-location.png",
      clip: {
        x: Math.max(0, box.x - 50),
        y: Math.max(0, box.y - 100),
        width: box.width + 100,
        height: box.height + 150
      }
    });
    
    console.log(`📸 Screenshot saved showing the API key input field\n`);
    console.log(`${"=".repeat(70)}\n`);
    console.log(`HOW TO USE:\n`);
    console.log(`1. Scroll down in the "Agent Relay & Crew Details" section`);
    console.log(`2. Look for "Bring your own OpenAI key" card`);
    console.log(`3. Paste your OpenAI API key (sk-...) into the password field`);
    console.log(`4. Key is stored locally in browser, never sent to backend`);
    console.log(`5. Used only for live reasoning features\n`);
    console.log(`${"=".repeat(70)}\n`);
  } else {
    console.log(`⚠️ OpenAI key input NOT visible in first viewport`);
    console.log(`You need to scroll down to find it\n`);
  }
});
