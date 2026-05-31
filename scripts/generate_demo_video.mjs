import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const BASE_URL = process.env.DEMO_BASE_URL || "http://127.0.0.1:7860";
const OUTPUT_DIR = path.resolve("artifacts/demo-video");
const VIDEO_DIR = path.join(OUTPUT_DIR, "playwright-video");
const PLAN_PATH = process.env.DEMO_SCENE_PLAN || path.join(OUTPUT_DIR, "scene_plan.json");

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function focusLocator(locator, block = "center", waitMs = 900) {
  const count = await locator.count();
  if (!count) {
    return 0;
  }
  const first = locator.first();
  await first.waitFor({ state: "visible", timeout: 8000 }).catch(() => {});
  await first.evaluate((node, blockArg) => {
    node.scrollIntoView({ behavior: "instant", block: blockArg, inline: "nearest" });
  }, block);
  await wait(waitMs);
  return waitMs;
}

async function pulse(locator, ms = 1800) {
  const count = await locator.count();
  if (!count) {
    return 0;
  }
  const first = locator.first();
  await first.waitFor({ state: "visible", timeout: 8000 }).catch(() => {});
  await first.evaluate((node) => {
    node.style.outline = "3px solid rgba(251, 191, 36, 0.95)";
    node.style.outlineOffset = "4px";
    node.style.transition = "outline 160ms ease";
  });
  await wait(ms);
  await first.evaluate((node) => {
    node.style.outline = "";
    node.style.outlineOffset = "";
  });
  return ms;
}

async function settleScene(sceneMs, consumedMs) {
  const remaining = Math.max(sceneMs - consumedMs, 1000);
  await wait(remaining);
}

async function recordDemo() {
  const plan = JSON.parse(await readFile(PLAN_PATH, "utf-8"));
  const [commandCenter, inputs, incident, training] = plan.scenes;

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

  let consumed = 0;

  await page.goto(`${BASE_URL}/queue`, { waitUntil: "networkidle" });
  consumed += 1200;
  await wait(1200);
  consumed += await pulse(page.getByRole("heading", { name: "Autonomous agents are already working the incident." }), 2200);
  consumed += await pulse(page.locator(".agent-crew-strip .crew-bot").first(), 2000);
  consumed += await pulse(page.locator(".queue-list .incident-btn").first(), 1800);
  await settleScene(commandCenter.video_duration_ms, consumed);

  consumed = 0;
  await page.goto(`${BASE_URL}/inputs`, { waitUntil: "networkidle" });
  consumed += 1200;
  await wait(1200);
  consumed += await pulse(page.getByRole("heading", { name: "Raw logs first." }), 2200);
  consumed += await pulse(page.locator("#rawLogInput"), 1800);
  consumed += await pulse(page.getByRole("button", { name: "Load example logs" }), 1400);
  await page.getByRole("button", { name: "Load example logs" }).click();
  consumed += 2200;
  await wait(2200);
  consumed += await pulse(page.locator("#rawDetectedService"), 1600);
  consumed += await pulse(page.locator("#rawDetectedSignature"), 1600);
  consumed += await pulse(page.getByRole("button", { name: "Submit raw logs" }), 1600);
  await settleScene(inputs.video_duration_ms, consumed);

  consumed = 0;
  await page.getByRole("button", { name: "Submit raw logs" }).click();
  await page.waitForURL(/\/incident\?[^#]*nexus_incident_id=nxs_[a-z0-9]+/i, { timeout: 20000 });
  await page.waitForLoadState("networkidle");
  consumed += 2200;
  await wait(2200);
  consumed += await focusLocator(page.locator(".hero"), "start", 900);
  consumed += await pulse(page.locator("#incidentTitle"), 2200);
  consumed += await pulse(page.locator("#threadSentinelCopy"), 1800);
  consumed += await pulse(page.locator("#threadPrismCopy"), 1800);
  consumed += await pulse(page.locator("#threadForgeCopy"), 1800);
  consumed += await pulse(page.locator("#threadGuardianCopy"), 1800);
  consumed += await focusLocator(page.locator(".byo-key-card"), "center", 1200);
  consumed += await pulse(page.locator(".byo-key-card"), 2200);
  consumed += await pulse(page.locator("#liveReasoningState"), 1600);
  consumed += await pulse(page.locator("#liveReasoningToggle"), 1800);
  consumed += await pulse(page.locator("#openaiApiKeyInput"), 2200);
  consumed += await pulse(page.locator("#openaiKeyStatus"), 2200);
  consumed += await focusLocator(page.locator(".guardian-gate-card"), "center", 1000);
  consumed += await pulse(page.getByRole("button", { name: "Approve runbook" }), 1800);
  await page.getByRole("button", { name: "Approve runbook" }).click();
  consumed += 2600;
  await wait(2600);
  consumed += await pulse(page.locator("#incidentHeroGuardian"), 2000);
  consumed += await pulse(page.locator("#incidentHeroExecution"), 2000);
  consumed += await pulse(page.locator("#resultBanner"), 2200);
  await settleScene(incident.video_duration_ms, consumed);

  consumed = 0;
  await page.getByRole("link", { name: "Learning & Controls" }).click();
  await page.waitForLoadState("networkidle");
  consumed += 1600;
  await wait(1600);
  consumed += await pulse(page.getByRole("heading", { name: "Learning stays visible. Dense artifacts stay quiet." }), 2200);
  consumed += await pulse(page.locator("#rewardCurve"), 2800);
  consumed += await pulse(page.locator("#agentStats"), 2200);
  consumed += await pulse(page.locator("#platformPolicyStatus"), 1800);
  consumed += await pulse(page.locator("#artifactSnapshots"), 1800);
  await settleScene(training.video_duration_ms, consumed);

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
