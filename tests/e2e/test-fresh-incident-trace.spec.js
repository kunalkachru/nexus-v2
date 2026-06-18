const { test } = require("@playwright/test");

test("Watch TRACE completion on fresh incident", async ({ page }) => {
  console.log(`\n${"=".repeat(80)}`);
  console.log("🧪 FRESH INCIDENT SUBMISSION TEST");
  console.log(`${"=".repeat(80)}\n`);

  // Step 1: Go to inputs
  console.log(`📍 Step 1: Navigate to /inputs...`);
  await page.goto("http://127.0.0.1:7860/inputs", { waitUntil: "networkidle" });
  console.log(`✓ /inputs page loaded\n`);

  // Step 2: Find and click submit
  console.log(`🔍 Step 2: Finding submit button...`);
  const submitBtn = await page.locator("button:has-text('Submit')").first();
  const submitText = await submitBtn.textContent();
  console.log(`✓ Found button: "${submitText}"\n`);

  console.log(`🖱️  Step 3: Clicking submit...`);
  await submitBtn.click();
  console.log(`✓ Submit clicked\n`);

  // Step 3: Wait for incident to load (longer timeout)
  console.log(`⏳ Step 4: Waiting for incident page to load...`);
  try {
    await page.waitForNavigation({ waitUntil: "networkidle", timeout: 60000 });
    console.log(`✓ Page loaded\n`);
  } catch (e) {
    console.log(`⚠️ Navigation timeout, continuing anyway...\n`);
  }

  // Get the current URL
  const currentUrl = page.url();
  console.log(`📍 Current page: ${currentUrl}\n`);

  // Step 4: Monitor agent states
  console.log(`${"=".repeat(80)}`);
  console.log(`⏱️  MONITORING AGENT PROGRESSION`);
  console.log(`${"=".repeat(80)}\n`);

  const progression = [];
  let traceCompleted = false;
  let allCompleted = false;

  for (let second = 0; second < 30; second++) {
    const bodyText = await page.locator("body").textContent();

    // Extract all agent states using regex
    const agents = ["SENTINEL", "PRISM", "REPLICA", "TRACE", "FORGE", "GUARDIAN"];
    const states = {};

    agents.forEach((agent) => {
      const regex = new RegExp(`${agent}[\\s\\S]{0,150}?(Completed|Working now|Waiting|not_run|error)`, "i");
      const match = bodyText.match(regex);
      states[agent] = match ? match[1] : null;
    });

    progression.push({ second, states });

    // Print every second
    const line = `${second}s | SENTINEL: ${(states.SENTINEL || "?").padEnd(12)} | PRISM: ${(states.PRISM || "?").padEnd(12)} | REPLICA: ${(states.REPLICA || "?").padEnd(12)} | TRACE: ${(states.TRACE || "?").padEnd(12)} | FORGE: ${(states.FORGE || "?").padEnd(12)} | GUARDIAN: ${(states.GUARDIAN || "?").padEnd(12)}`;
    console.log(line);

    // Check completion conditions
    if (states.TRACE === "Completed") {
      traceCompleted = true;
    }

    if (
      states.SENTINEL === "Completed" &&
      states.PRISM === "Completed" &&
      states.REPLICA === "Completed" &&
      states.TRACE === "Completed" &&
      states.FORGE === "Completed" &&
      states.GUARDIAN === "Completed"
    ) {
      allCompleted = true;
      console.log(`\n✅ ALL AGENTS COMPLETED AT ${second}s!\n`);
      break;
    }

    // Break early if TRACE is stuck
    if (second > 20 && states.TRACE === "Working now" && states.FORGE === "Waiting") {
      console.log(`\n⚠️ TRACE APPEARS STUCK (20+ seconds in "Working now")\n`);
      break;
    }

    await page.waitForTimeout(1000);
  }

  console.log(`\n${"=".repeat(80)}`);
  console.log("📊 TEST RESULTS");
  console.log(`${"=".repeat(80)}\n`);

  const lastState = progression[progression.length - 1].states;
  console.log(`Final state at ${progression.length - 1}s:`);
  console.log(`  SENTINEL: ${lastState.SENTINEL || "unknown"}`);
  console.log(`  PRISM: ${lastState.PRISM || "unknown"}`);
  console.log(`  REPLICA: ${lastState.REPLICA || "unknown"}`);
  console.log(`  TRACE: ${lastState.TRACE || "unknown"}`);
  console.log(`  FORGE: ${lastState.FORGE || "unknown"}`);
  console.log(`  GUARDIAN: ${lastState.GUARDIAN || "unknown"}\n`);

  console.log(`Summary:`);
  console.log(`  TRACE completed: ${traceCompleted ? "✅ YES" : "❌ NO"}`);
  console.log(`  All agents completed: ${allCompleted ? "✅ YES" : "❌ NO"}`);
  console.log(`  Test duration: ${progression.length - 1}s\n`);

  // Take screenshot
  await page.screenshot({ path: "/tmp/fresh-incident-final.png" });
  console.log(`📸 Screenshot saved: /tmp/fresh-incident-final.png\n`);

  console.log(`${"=".repeat(80)}\n`);
});
