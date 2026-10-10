import type { Page } from "@playwright/test";
import { ADMIN, HOSTED } from "../playwright.config.ts";
import { expect, test } from "./fixtures.ts";

test.use({ baseURL: `http://127.0.0.1:${HOSTED}` });

const ORIGIN = { Origin: `http://127.0.0.1:${HOSTED}` };

/** Sign in (or sign up) through the API; the page shares the cookie. The UI for this is tested in hosted.spec.ts. */
async function as(page: Page, username: string, password: string, signUp = false) {
  const r = await page.request.post(signUp ? "/api/signup" : "/api/login", {
    data: { username, password },
    headers: ORIGIN,
  });
  expect(r.ok(), await r.text()).toBe(true);
  await page.reload();
}

const newName = (prefix: string) => `${prefix}${Date.now() % 1_000_000}`;

async function openLookup(page: Page, champion: string, opponent?: string) {
  await page.getByRole("tab", { name: "Lookup" }).click();
  await page.getByRole("button", { name: "Top", exact: true }).click();
  await page.getByLabel("Champion").fill(champion);
  await expect(page.getByRole("heading", { name: new RegExp(`^${champion} top: `) })).toBeVisible();
  if (opponent) {
    await page.locator("tbody tr", { hasText: opponent }).filter({ visible: true }).click();
    await expect(page.getByRole("heading", { name: `${champion} vs ${opponent}` })).toBeVisible();
  }
}

test("admin notes show at once, and admins can delete them", async ({ page }) => {
  await as(page, ADMIN.username, ADMIN.password);
  await openLookup(page, "Darius");
  const card = page.locator(".summary");
  await card.getByRole("button", { name: "+ Suggest a note" }).click();
  await card.getByLabel("Your note on Darius").fill("Hold W for the slow after your Q.");
  await card.getByRole("button", { name: "Add note" }).click();
  await expect(card.getByRole("status")).toHaveText("Your note was added.");
  const note = card.locator(".note", { hasText: "Hold W for the slow after your Q." });
  await expect(note).toContainText(ADMIN.username);

  await note.getByRole("button", { name: "Delete" }).click();
  await note.getByRole("button", { name: "Really delete?" }).click();
  await expect(note).toHaveCount(0);
});

test("a source is only a link when it is an http(s) URL", async ({ page }) => {
  await as(page, ADMIN.username, ADMIN.password);
  await openLookup(page, "Darius", "Garen");
  const panel = page.locator(".panel", { hasText: "Darius vs Garen" });
  for (const source of ["javascript:alert(1)", "https://www.reddit.com/r/DariusMains/"]) {
    await panel.getByRole("button", { name: "+ Suggest a note" }).click();
    await panel.getByLabel("Your note on Darius vs Garen").fill(`Note with source ${source}`);
    await panel.getByLabel("Source (optional)").fill(source);
    await panel.getByRole("button", { name: "Add note" }).click();
    await expect(panel.getByRole("status")).toHaveText("Your note was added.");
  }
  const plain = panel.locator(".note", { hasText: "javascript:alert(1)" });
  await expect(plain.getByRole("link")).toHaveCount(0);
  const linked = panel.locator(".note", { hasText: "Note with source https://" }).getByRole("link");
  await expect(linked).toHaveAttribute("href", "https://www.reddit.com/r/DariusMains/");
  await expect(linked).toHaveAttribute("rel", /nofollow/);
});

test("a contributor's note waits for review and shows under My notes", async ({ page }) => {
  await as(page, newName("writer"), "writer password", true);
  await openLookup(page, "Darius", "Garen");
  const panel = page.locator(".panel", { hasText: "Darius vs Garen" });
  await panel.getByRole("button", { name: "+ Suggest a note" }).click();
  await panel.getByLabel("Your note on Darius vs Garen").fill("Too short");
  await panel.getByRole("button", { name: "Send for review" }).click();
  await expect(panel.getByRole("alert")).toHaveText("Notes are 10 to 1000 characters.");

  await panel.getByLabel("Your note on Darius vs Garen").fill("Walk up when his Q is down, he cannot pull you.");
  await panel.getByRole("button", { name: "Send for review" }).click();
  await expect(panel.getByRole("status")).toContainText("shows up once an admin approves it");
  await expect(panel.getByText("Walk up when his Q is down")).toHaveCount(0); // not shown before review

  await page.getByRole("tab", { name: "My notes" }).click();
  const mine = page.locator(".mine article", { hasText: "Walk up when his Q is down" });
  await expect(mine).toContainText("Top · Darius vs Garen");
  await expect(mine.getByText("Waiting for review")).toBeVisible();
});

test("the admin fixes and approves one note, and rejects another with a reason", async ({ page }) => {
  const writer = newName("writer");
  await as(page, writer, "writer password", true);
  for (const text of [
    "Darius pulls you with E, so stay behin minions.",
    "Darius is just broken, ban him every game.",
  ]) {
    const r = await page.request.post("/api/notes", {
      data: { role: "top", champion: "Darius", opponent: text.includes("pulls") ? "Garen" : null, text, source: "" },
      headers: ORIGIN,
    });
    expect(r.ok(), await r.text()).toBe(true);
  }

  await as(page, ADMIN.username, ADMIN.password);
  const tab = page.getByRole("tab", { name: /^Admin/ });
  await expect(tab.locator(".badge")).toHaveText(/^[2-9]\d*$/); // at least these two wait
  await tab.click();
  const fix = page.locator("article", { hasText: "Top · Darius vs Garen" }).filter({ visible: true }).last();
  await expect(fix.getByLabel("Note (fix it before approving if needed)")).toHaveValue(/stay behin minions/);
  await fix
    .getByLabel("Note (fix it before approving if needed)")
    .fill("Darius pulls you with E, so stay behind minions.");
  await fix.getByRole("button", { name: "Approve" }).click();
  // newest last; the note text sits in an editable box, which is not page text, so go by the heading
  const ban = page.locator("article", { hasText: "Top · Darius (the champion)" }).filter({ visible: true }).last();
  await expect(ban.getByLabel("Note (fix it before approving if needed)")).toHaveValue(/ban him every game/);
  await ban.getByLabel("Reason for rejecting (optional)").fill("Not a tip.");
  await ban.getByRole("button", { name: "Reject" }).click();
  const queued = () =>
    page
      .getByLabel("Note (fix it before approving if needed)")
      .evaluateAll((boxes) => boxes.map((b) => (b as HTMLTextAreaElement).value).join("\n"));
  await expect.poll(queued).not.toContain("ban him every game"); // left the queue

  await page.request.post("/api/logout", { headers: ORIGIN });
  await page.reload();
  await openLookup(page, "Darius", "Garen"); // signed out: everyone sees approved notes
  const shown = page.locator(".note", { hasText: "stay behind minions" }).filter({ visible: true });
  await expect(shown).toContainText(writer);

  await as(page, writer, "writer password");
  await page.getByRole("tab", { name: "My notes" }).click();
  await expect(page.locator(".mine article", { hasText: "stay behind minions" }).getByText("Approved")).toBeVisible();
  const rejected = page.locator(".mine article", { hasText: "ban him every game" });
  await expect(rejected.getByText("Rejected")).toBeVisible();
  await expect(rejected).toContainText("reason: Not a tip.");
});
