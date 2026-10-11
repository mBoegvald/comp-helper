import { ADMIN, HOSTED } from "../playwright.config.ts";
import { expect, test } from "./fixtures.ts";

// Nothing may push the page wider than a phone: wide tables scroll inside their panel instead.
test.use({ viewport: { width: 340, height: 700 } });

const pageWidth = (page: import("@playwright/test").Page) =>
  page.evaluate(() => document.documentElement.scrollWidth - innerWidth);

test("every tab fits a phone", async ({ page }) => {
  for (const hash of ["#/draft", "#/lookup/top/Darius/Garen", "#/data"]) {
    await page.goto(`/?phone${hash}`);
    await expect(page.locator("main")).toBeVisible();
    if (hash.includes("Garen")) await expect(page.getByRole("heading", { name: "Darius vs Garen" })).toBeVisible();
    expect(await pageWidth(page), hash).toBeLessThanOrEqual(0);
  }
});

test.describe("hosted", () => {
  test.use({ baseURL: `http://127.0.0.1:${HOSTED}` });

  test("the admin's tabs and pages fit a phone", async ({ page }) => {
    const r = await page.request.post("/api/login", {
      data: ADMIN,
      headers: { Origin: `http://127.0.0.1:${HOSTED}` },
    });
    expect(r.ok()).toBe(true);
    for (const hash of ["#/admin", "#/account", "#/privacy"]) {
      await page.goto(`/?phone${hash}`);
      await expect(page.getByRole("tab", { name: /^Admin/ })).toBeAttached();
      if (hash === "#/admin") await expect(page.getByRole("heading", { name: /^Accounts/ })).toBeVisible();
      expect(await pageWidth(page), hash).toBeLessThanOrEqual(0);
    }
  });
});
