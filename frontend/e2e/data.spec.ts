import { expect, test } from "./fixtures.ts";

test.beforeEach(async ({ page }) => {
  await page.getByRole("tab", { name: "Data" }).click();
});

test("shows what the data covers", async ({ page }) => {
  const top = page.locator("tbody tr", { hasText: "Top" }).filter({ visible: true });
  await expect(top).toBeVisible();
  await expect(page.getByText("Win rates: Lolalytics 16.20 EMERALD+.")).toBeVisible();
  await expect(page.getByText("Idle")).toBeVisible();
  await expect(page.getByRole("button", { name: "Stop" })).toHaveCount(0);
});

test("long updates ask before they start", async ({ page }) => {
  const stage = page.locator(".stage", { hasText: "Fetch Reddit comments" });
  await stage.getByRole("button", { name: "Run" }).click();
  await expect(stage.getByText("This takes many hours")).toBeVisible();
  await stage.getByRole("button", { name: "Cancel" }).click();
  await expect(stage.getByText("Replies to the best threads")).toBeVisible();
});
