import { defineConfig } from "@playwright/test";

// Browser tests against the real Python server on a fresh copy of the fixture database (tests/e2e_server.py).
// On NixOS, Playwright's own browser download does not run: point CHROMIUM_PATH at nix's chromium instead.
export const LOCAL = 8811;

export default defineConfig({
  testDir: "e2e",
  workers: 1, // the tests share the servers and their databases
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${LOCAL}`,
    trace: "retain-on-failure",
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || undefined },
  },
  webServer: [
    {
      command: `python3 ../tests/e2e_server.py --port ${LOCAL}`,
      url: `http://127.0.0.1:${LOCAL}/api/meta`,
      reuseExistingServer: false,
    },
  ],
});
