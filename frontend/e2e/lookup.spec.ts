import { expect, test } from "./fixtures.ts";

test.beforeEach(async ({ page }) => {
  await page.getByRole("tab", { name: "Lookup" }).click();
  await page.getByRole("button", { name: "Top", exact: true }).click();
  await page.getByLabel("Champion").fill("Darius");
  await expect(page.getByRole("heading", { name: /^Darius top: \d+ matchups$/ })).toBeVisible();
});

test("lists, filters and opens matchups", async ({ page }) => {
  const rows = page.locator("tbody tr").filter({ visible: true });
  await expect(rows).toHaveCount(2); // Aatrox (both directions) and Garen (from Garen's side); hidden tabs have tables too
  await page.getByLabel("Filter opponents").fill("aat");
  await expect(rows).toHaveCount(1);
  await rows.first().click();
  await expect(page.getByRole("heading", { name: "Darius vs Aatrox" })).toBeVisible();
  await expect(page.getByText("Darius mains on Aatrox")).toBeVisible();
  await expect(page.locator(".lane").getByText("Favored")).toBeVisible();
});

test("sorts by a column", async ({ page }) => {
  await page.getByRole("button", { name: "Opponent" }).click();
  await expect(page.locator("tbody tr").filter({ visible: true }).first()).toContainText("Aatrox");
  await page.getByRole("button", { name: /^Opponent/ }).click();
  await expect(page.locator("tbody tr").filter({ visible: true }).first()).toContainText("Garen");
});

test("edits champion notes and resets them to the defaults", async ({ page }) => {
  const summary = page.locator(".summary");
  const original = "The enemy is melee heavy and you want lane pressure";
  await expect(summary.getByText(original)).toBeVisible();

  await page.getByRole("button", { name: "Edit notes" }).click();
  await expect(page.getByLabel("Pick when")).toHaveAttribute("placeholder", `Default: ${original}`);
  await page.getByLabel("Pick when").fill("E2E pick when");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(summary.getByText("E2E pick when")).toBeVisible();

  await page.getByRole("button", { name: "Edit notes" }).click();
  await page.getByLabel("Pick when").fill("");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(summary.getByText(original)).toBeVisible();
});

test("edits a matchup label and tip, then removes them", async ({ page }) => {
  await page.locator("tbody tr", { hasText: "Garen" }).filter({ visible: true }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Result for Darius").selectOption("Favored");
  await page.getByLabel("Lane tip").fill("E2E tip vs Garen");
  await page.getByRole("button", { name: "Save" }).click();

  const notes = page.locator(".notes");
  await expect(notes.getByText("E2E tip vs Garen")).toBeVisible();
  await expect(notes.getByText("Hand label: Favored")).toBeVisible();
  await expect(
    page.locator("tbody tr", { hasText: "Garen" }).filter({ visible: true }).getByTitle("Has hand-written lane notes"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Result for Darius").selectOption("");
  await page.getByLabel("Lane tip").fill("");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(notes.getByText("E2E tip vs Garen")).toHaveCount(0);
});
