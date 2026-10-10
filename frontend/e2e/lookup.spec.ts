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
  await expect(notes.getByText("Your label: Favored")).toBeVisible();
  await expect(
    page.locator("tbody tr", { hasText: "Garen" }).filter({ visible: true }).getByTitle("Has your lane notes"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Result for Darius").selectOption("");
  await page.getByLabel("Lane tip").fill("");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(notes.getByText("E2E tip vs Garen")).toHaveCount(0);
});

test("an open editor keeps unsaved text when the data reloads", async ({ page }) => {
  await page.getByRole("button", { name: "Edit notes" }).click();
  await page.getByLabel("Pick when").fill("Typed but not saved yet");

  // saving a matchup tip next to it reloads the data in every tab
  await page.locator("tbody tr", { hasText: "Garen" }).filter({ visible: true }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Lane tip").fill("E2E reload tip");
  const reloaded = page.waitForResponse((r) => r.url().includes("/api/champion?")); // debounced, so wait for it
  await page.locator("form", { hasText: "Lane tip" }).getByRole("button", { name: "Save" }).click();
  await expect(page.locator(".notes").getByText("E2E reload tip")).toBeVisible();
  await reloaded;

  await expect(page.getByLabel("Pick when")).toHaveValue("Typed but not saved yet");

  // clean up: drop the edit, remove the tip
  await page.locator("form", { hasText: "Pick when" }).getByRole("button", { name: "Cancel" }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Lane tip").fill("");
  await page.locator("form", { hasText: "Lane tip" }).getByRole("button", { name: "Save" }).click();
  await expect(page.locator(".notes").getByText("E2E reload tip")).toHaveCount(0);
});

test("looking up another champion closes the editor", async ({ page }) => {
  await page.getByRole("button", { name: "Edit notes" }).click();
  await expect(page.getByLabel("Pick when")).toBeVisible();
  await page.getByLabel("Champion").fill("Garen");
  await expect(page.getByRole("heading", { name: /^Garen top: \d+ matchups$/ })).toBeVisible();
  await expect(page.getByLabel("Pick when")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Edit notes" })).toBeVisible();
});

test("a champion can be picked with the keyboard", async ({ page }) => {
  const box = page.getByRole("combobox", { name: "Champion" });
  await box.fill("gar");
  await box.press("Enter");
  await expect(box).toHaveValue("Garen");
  await expect(page.getByRole("heading", { name: /^Garen top: \d+ matchups$/ })).toBeVisible();
});

test("rewording a tip keeps a label that agrees with the win rates", async ({ page }) => {
  await page.locator("tbody tr", { hasText: "Aatrox" }).filter({ visible: true }).click();
  await expect(page.locator(".lane").getByText("Favored")).toBeVisible(); // the data says Favored too
  const save = () => page.locator("form", { hasText: "Lane tip" }).getByRole("button", { name: "Save" }).click();

  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Result for Darius").selectOption("Favored");
  await page.getByLabel("Lane tip").fill("First wording");
  await save();
  await expect(page.locator(".notes").getByText("First wording")).toBeVisible();

  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByLabel("Result for Darius")).toHaveValue("Favored"); // starts from the saved label
  await page.getByLabel("Lane tip").fill("Second wording");
  await save();
  await expect(page.locator(".notes").getByText("Your label: Favored")).toBeVisible();

  await page.getByRole("button", { name: "Edit", exact: true }).click(); // clean up
  await page.getByLabel("Result for Darius").selectOption("");
  await page.getByLabel("Lane tip").fill("");
  await save();
  await expect(page.locator(".notes").getByText("Second wording")).toHaveCount(0);
});

test("a slow failure for an earlier matchup does not show on the current one", async ({ page }) => {
  await page.route(/\/api\/matchup\?.*b=Aatrox/, async (route) => {
    await new Promise((r) => setTimeout(r, 800));
    await route.fulfill({ status: 500, contentType: "application/json", body: '{"error":"old answer failed"}' });
  });
  await page.locator("tbody tr", { hasText: "Aatrox" }).filter({ visible: true }).click();
  await page.locator("tbody tr", { hasText: "Garen" }).filter({ visible: true }).click();
  await expect(page.getByRole("heading", { name: "Darius vs Garen" })).toBeVisible();
  await page.waitForTimeout(1200); // the failing answer for Aatrox has arrived by now
  await expect(page.getByText("old answer failed")).toHaveCount(0);
});
