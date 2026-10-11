import { expect, test } from "./fixtures.ts";

test("Back and Forward move between tabs", async ({ page }) => {
  await page.getByRole("tab", { name: "Lookup" }).click();
  await page.getByRole("tab", { name: "Data" }).click();
  await expect(page).toHaveURL(/#\/data$/);

  await page.goBack();
  await expect(page.getByRole("tab", { name: "Lookup" })).toHaveAttribute("aria-selected", "true");
  await page.goBack();
  await expect(page.getByRole("tab", { name: "Draft" })).toHaveAttribute("aria-selected", "true");
  await page.goForward();
  await expect(page.getByRole("tab", { name: "Lookup" })).toHaveAttribute("aria-selected", "true");
});

test("Back goes from a matchup to the champion before it, and a matchup can be linked", async ({ page }) => {
  await page.getByRole("tab", { name: "Lookup" }).click();
  await page.getByRole("button", { name: "Top", exact: true }).click();
  await page.locator("#lk-champ").fill("Darius");
  await expect(page).toHaveURL(/#\/lookup\/top\/Darius$/);
  await page.locator("tbody tr", { hasText: "Garen" }).filter({ visible: true }).click();
  await expect(page).toHaveURL(/#\/lookup\/top\/Darius\/Garen$/);
  await page.locator("#lk-champ").fill("Garen"); // right after: still its own entry
  await expect(page.getByRole("heading", { name: /^Garen top: / })).toBeVisible();

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Darius vs Garen" })).toBeVisible();
  await expect(page.locator("#lk-champ")).toHaveValue("Darius");
  await page.goBack();
  await expect(page.getByRole("heading", { name: /^Darius top: / })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Darius vs Garen" })).toHaveCount(0);

  await page.goto("/?fresh#/lookup/top/Darius/Garen"); // "?" forces a real load
  await expect(page.getByRole("heading", { name: "Darius vs Garen" })).toBeVisible();
});

test("names reached while typing do not each add an entry", async ({ page }) => {
  await page.getByRole("tab", { name: "Lookup" }).click();
  await page.getByRole("button", { name: "Top", exact: true }).click();
  const before = await page.evaluate(() => history.length);
  // like "Vi" on the way to "Viktor": a second name right after the first replaces it
  await page.locator("#lk-champ").fill("Darius");
  await expect(page).toHaveURL(/#\/lookup\/top\/Darius$/);
  await page.locator("#lk-champ").fill("Garen");
  await expect(page).toHaveURL(/#\/lookup\/top\/Garen$/);
  expect(await page.evaluate(() => history.length)).toBe(before + 1);
  await page.goBack();
  await expect(page).toHaveURL(/#\/lookup\/top$/);
});

test("a draft link opens the draft, and the address becomes the Draft tab", async ({ page }) => {
  await page.goto(`/?link#draft=${encodeURIComponent('{"role":"top","enemy":{"top":"Darius"}}')}`);
  await expect(page.getByRole("heading", { name: "Best top picks into Darius" })).toBeVisible();
  await expect(page).toHaveURL(/#\/draft$/);
});
