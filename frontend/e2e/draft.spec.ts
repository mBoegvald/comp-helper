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

test("champions can be picked with the keyboard", async ({ page }) => {
  const slot = page.getByRole("combobox", { name: "Enemy Top" });
  await slot.fill("dar");
  await expect(page.getByRole("option").first()).toHaveAccessibleName("Darius"); // the icon is hidden from readers
  await expect(slot).toHaveAttribute("aria-expanded", "true");
  await slot.press("Enter");
  await expect(slot).toHaveValue("Darius");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Best top picks into Darius" })).toBeVisible();
});

test("arrow keys move through the suggestions, and Tab picks and moves on", async ({ page }) => {
  const slot = page.getByRole("combobox", { name: "Enemy Top" });
  await slot.fill("ga");
  const options = page.getByRole("option");
  await expect(options.nth(1)).toBeVisible();
  await slot.press("ArrowDown");
  await expect(options.nth(1)).toHaveAttribute("aria-selected", "true");
  const second = (await options.nth(1).locator(".name").textContent())!;
  await slot.press("Tab");
  await expect(slot).toHaveValue(second);
  await expect(page.getByRole("combobox", { name: "Enemy Jungle" })).toBeFocused();
});

test("Escape closes the suggestions and keeps the text", async ({ page }) => {
  const slot = page.getByRole("combobox", { name: "Enemy Top" });
  await slot.fill("gar");
  await expect(page.getByRole("listbox")).toBeVisible();
  await slot.press("Escape");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(slot).toHaveValue("gar");
});

test("a suggestion can be clicked", async ({ page }) => {
  const slot = page.getByRole("combobox", { name: "Enemy Top" });
  await slot.fill("aat");
  await page.getByRole("option", { name: "Aatrox" }).click();
  await expect(slot).toHaveValue("Aatrox");
  await expect(slot).toBeFocused(); // clicking does not take the focus away
});

test("a ban can be picked with the keyboard", async ({ page }) => {
  const input = page.getByRole("combobox", { name: "Unavailable (bans, fearless)" });
  await input.fill("gare");
  await input.press("Enter");
  await expect(page.locator(".chip", { hasText: "Garen" })).toBeVisible();
  await expect(input).toHaveValue("");
});

test("a half-typed name does not change the picks", async ({ page }) => {
  const slot = page.getByRole("combobox", { name: "Enemy Top" });
  const asked = page.waitForResponse(
    (r) => r.url().includes("/api/recommend") && r.request().postData()!.includes('"ga"'),
  );
  await slot.fill("ga");
  await asked;
  await expect(page.getByRole("heading", { name: "Best top blind picks" })).toBeVisible();
  await expect(page.getByText(/into ga\b/)).toHaveCount(0);
  await slot.press("Escape");
  await expect(slot).toHaveClass(/unknown/); // still marked as not a champion

  await slot.fill("gar");
  await slot.press("Enter");
  await expect(page.getByRole("heading", { name: "Best top picks into Garen" })).toBeVisible();
});

test("draft links: a valid one loads, a broken one does not break the page", async ({ page }) => {
  const open = (draft: string) => page.goto(`/?link#draft=${encodeURIComponent(draft)}`); // "?" forces a real load
  await open('{"role":"top","enemy":{"top":"Darius"}}');
  await expect(page.getByRole("heading", { name: "Best top picks into Darius" })).toBeVisible();

  await open('{"role":"top","ally":null,"enemy":["x"],"unavailable":"Garen"}');
  await expect(page.getByRole("heading", { name: /^Best top / })).toBeVisible(); // the fixture fails on page errors
  await page.reload(); // and the broken values were not saved
  await expect(page.getByRole("combobox", { name: "Your Jungle" })).toBeVisible();
});
