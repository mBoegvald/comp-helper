import { test as base, expect } from "@playwright/test";

// Every test starts on a fresh page with nothing remembered, and without Riot's icon server
// (icons fall back to initials), so results do not depend on the internet.
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route(/ddragon\.leagueoflegends\.com/, (route) => route.abort());
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => {
      if (m.type() === "error" && m.text().includes("Content Security Policy")) errors.push(m.text()); // CSP blocked something
    });
    await page.goto("/");
    await use(page);
    expect(errors, "errors thrown in the page").toEqual([]);
  },
});

export { expect };
