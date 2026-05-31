import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const BASE_URL = process.env.DEMO_BASE_URL || "http://127.0.0.1:7860";
const OUTPUT_DIR = path.resolve("artifacts/demo-video");
const VIDEO_DIR = path.join(OUTPUT_DIR, "playwright-video");

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function pulse(page, locator, ms = 1400) {
  const count = await locator.count();
  if (!count) {
    return;
  }
  await locator.first().waitFor({ state: "visible", timeout: 8000 }).catch(() => {});
  await locator.first().evaluate((node) => {
    node.dataset.demoHighlight = "1";
    node.style.outline = "3px solid rgba(251, 191, 36, 0.95)";
    node.style.outlineOffset = "4px";
    node.style.transition = "outline 160ms ease";
  });
  await wait(ms);
  await locator.first().evaluate((node) => {
    node.style.outline = "";
    node.style.outlineOffset = "";
    delete node.dataset.demoHighlight;
  });
}

async function recordDemo() {
  await mkdir(VIDEO_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: VIDEO_DIR,
      size: { width: 1280, height: 720 },
    },
    colorScheme: "dark",
  });

  const page = await context.newPage();
  await page.addInitScript(() => {
    window.localStorage.setItem("nexus.live_reasoning", "0");
    window.localStorage.setItem("nexus.theme", "dark");
  });

  await page.goto(`${BASE_URL}/inputs`, { waitUntil: "networkidle" });
  await wait(1200);

  await pulse(page, page.getByRole("heading", { name: "Raw logs first." }));
  await pulse(page, page.getByRole("button", { name: "Load example logs" }), 1100);
  await page.getByRole("button", { name: "Load example logs" }).click();
  await wait(1800);

  await pulse(page, page.getByRole("button", { name: "Submit raw logs" }), 900);
  await page.getByRole("button", { name: "Submit raw logs" }).click();
  await page.waitForURL(/\/incident\?[^#]*nexus_incident_id=nxs_[a-z0-9]+/i, { timeout: 20000 });
  await page.waitForLoadState("networkidle");
  await wait(1800);

  await pulse(page, page.locator("#incidentTitle"), 1400);
  await pulse(page, page.locator("#threadSentinelCopy"), 1400);
  await pulse(page, page.locator("#threadPrismCopy"), 1300);
  await pulse(page, page.locator("#threadForgeCopy"), 1300);
  await pulse(page, page.locator("#threadGuardianCopy"), 1300);
  await pulse(page, page.locator("#openaiKeyStatus"), 1300);
  await pulse(page, page.getByRole("button", { name: "Approve runbook" }), 1100);
  await page.getByRole("button", { name: "Approve runbook" }).click();
  await wait(2600);

  await pulse(page, page.locator("#incidentHeroGuardian"), 1400);
  await pulse(page, page.locator("#incidentHeroExecution"), 1400);
  await pulse(page, page.locator("#resultBanner"), 1400);

  await page.getByRole("link", { name: "Learning & Controls" }).click();
  await page.waitForLoadState("networkidle");
  await wait(1700);

  await pulse(page, page.getByRole("heading", { name: "Learning stays visible. Dense artifacts stay quiet." }), 1400);
  await pulse(page, page.locator("#rewardCurve"), 1700);
  await pulse(page, page.locator("#agentStats"), 1600);
  await pulse(page, page.locator("#platformPolicyStatus"), 1200);
  await pulse(page, page.locator("#artifactSnapshots"), 1200);
  await wait(2200);

  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  await wait(800);

  const videoPath = await page.video().path();
  await context.close();
  await browser.close();
  return videoPath;
}

recordDemo()
  .then((videoPath) => {
    console.log(videoPath);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
