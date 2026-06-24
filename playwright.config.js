const { defineConfig, devices } = require("@playwright/test");

const browserBaseUrl = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:7860";

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  fullyParallel: false,
  reporter: [["html", { open: "never" }]],
  use: {
    baseURL: browserBaseUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "on",
    viewport: { width: 1440, height: 1100 },
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command:
          "python -m uvicorn server.app:app --host 127.0.0.1 --port 7860",
        url: "http://127.0.0.1:7860/health",
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
