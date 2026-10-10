import { expect, test } from "./fixtures.ts";

test.beforeEach(async ({ page }) => {
  await page.getByRole("button", { name: "Top", exact: true }).click();
});

test("picks into the lane opponent", async ({ page }) => {
  await page.getByLabel("Enemy Top").fill("darius"); // lower case still finds Darius
  await expect(page.getByRole("heading", { name: "Best top picks into Darius" })).toBeVisible();
  // Aatrox is Unfavored into Darius (dNorm -3.2), so it is listed under Avoid
  const avoid = page.locator(".avoid");
  await expect(avoid.getByText("Aatrox")).toBeVisible();
  await expect(avoid.getByText("lane vs Darius")).toBeVisible();
});

test("flags names it does not know", async ({ page }) => {
  const slot = page.getByLabel("Enemy Jungle");
  await slot.fill("Notachamp");
  await expect(slot).toHaveAttribute("title", "Unknown champion name");
  await expect(slot).toHaveClass(/unknown/);
});

test("bans remove a champion from the picks", async ({ page }) => {
  const cards = page.locator(".cards").first();
  await expect(cards.getByText("Garen", { exact: true })).toBeVisible();
  const input = page.getByLabel("Unavailable (bans, fearless)");
  await input.fill("garen");
  await input.press("Enter");
  await expect(page.locator(".chip", { hasText: "Garen" })).toBeVisible(); // spelled as the champion
  await expect(cards.getByText("Garen", { exact: true })).toHaveCount(0);
});

test("remembers the draft and clears it", async ({ page }) => {
  await page.getByLabel("Enemy Top").fill("Darius");
  await expect(page.getByRole("heading", { name: "Best top picks into Darius" })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Enemy Top")).toHaveValue("Darius");
  await page.getByRole("button", { name: "Clear draft" }).click();
  await expect(page.getByLabel("Enemy Top")).toHaveValue("");
  await expect(page.getByRole("heading", { name: "Best top blind picks" })).toBeVisible();
});

test("a card opens to its lane and champion info, and links to Lookup", async ({ page }) => {
  await page.getByLabel("Enemy Top").fill("Darius");
  // Garen is Even into Darius, so it is a full card among the picks (Aatrox is only in the short Avoid list)
  const card = page.locator(".cards").first().locator("article", { hasText: "Garen" });
  await card.getByText("Lane notes, Reddit tips and champion info").click();
  await expect(card.getByText("No notes or Reddit tips for this matchup yet.")).toBeVisible();
  await expect(card.getByText("You need a simple, safe frontline")).toBeVisible();
  await card.getByRole("button", { name: "All matchups and notes →" }).click();
  await expect(page.getByRole("tab", { name: "Lookup" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByLabel("Champion")).toHaveValue("Garen");
});
