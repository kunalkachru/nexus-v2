const { test } = require("@playwright/test");

test("Show OpenAI key input location", async ({ page }) => {
  await page.goto("http://127.0.0.1:7860/incident?nexus_incident_id=INC001", {
    waitUntil: "networkidle",
  });

  console.log(`\n${"=".repeat(70)}`);
  console.log("🔑 WHERE TO ENTER OPENAI KEY IN NEXUS");
  console.log(`${"=".repeat(70)}\n`);

  // Scroll down to find the API key input
  const keyInput = await page.locator("#openaiApiKeyInput");
  
  // Scroll to the element
  await keyInput.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  
  // Take full page screenshot to show context
  await page.screenshot({ path: "/tmp/openai-key-full.png" });
  
  console.log(`LOCATION: Agent Relay & Crew Details section\n`);
  console.log(`STEPS TO ENTER YOUR OPENAI KEY:\n`);
  console.log(`1. Scroll down on the incident detail page`);
  console.log(`2. Expand "Agent Relay & Crew Details" section (if collapsed)`);
  console.log(`3. Continue scrolling in that section`);
  console.log(`4. Look for "Bring your own OpenAI key" card`);
  console.log(`5. Find the password input field labeled "OpenAI API key"`);
  console.log(`6. Paste your key (starts with sk-)`);
  console.log(`7. Key is stored locally in your browser\n`);
  
  console.log(`KEY DETAILS:\n`);
  console.log(`- Input type: Password field (hidden text)`);
  console.log(`- Placeholder: sk-...`);
  console.log(`- Storage: Browser localStorage only (never sent to backend)`);
  console.log(`- Purpose: Used for live reasoning and real-time features`);
  console.log(`- Where to get key: https://platform.openai.com/api-keys\n`);
  
  console.log(`${"=".repeat(70)}\n`);
});
