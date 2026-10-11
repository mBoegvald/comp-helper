import type { Page } from "@playwright/test";
import { ADMIN, HOSTED } from "../playwright.config.ts";
import { expect, test } from "./fixtures.ts";

test.use({ baseURL: `http://127.0.0.1:${HOSTED}` });

const dialog = (page: Page) => page.getByRole("dialog");

async function signIn(page: Page, username: string, password: string) {
  await page.getByRole("button", { name: "Sign in" }).click();
  await dialog(page).getByLabel("Username").fill(username);
  await dialog(page).getByLabel("Password").fill(password);
  await dialog(page).getByRole("button", { name: "Sign in" }).click();
}

async function openDariusInLookup(page: Page) {
  await page.getByRole("tab", { name: "Lookup" }).click();
  await page.getByRole("button", { name: "Top", exact: true }).click();
  await page.getByLabel("Champion").fill("Darius");
  await expect(page.getByRole("heading", { name: /^Darius top: \d+ matchups$/ })).toBeVisible();
}

test("signed-out visitors can read but not edit", async ({ page }) => {
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await openDariusInLookup(page);
  await expect(page.getByRole("button", { name: "Edit notes" })).toHaveCount(0);
  await page.getByRole("tab", { name: "Data" }).click();
  await expect(page.locator("tbody tr", { hasText: "Top" }).filter({ visible: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Update" })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Admin" })).toHaveCount(0);
});

test("sign up as a contributor, then sign out", async ({ page }) => {
  const name = `tester${Date.now() % 100000}`;
  await page.getByRole("button", { name: "Sign in" }).click();
  await dialog(page).getByRole("button", { name: "Create an account" }).click();
  await dialog(page).getByLabel("Username").fill(name);
  await dialog(page).getByLabel("Password").fill("short");
  await dialog(page).getByRole("button", { name: "Create account" }).click();
  await expect(dialog(page).getByRole("alert")).toHaveText("Passwords are 10 to 200 characters.");

  await dialog(page).getByLabel("Password").fill("tester password");
  await dialog(page).getByRole("button", { name: "Create account" }).click();
  await expect(dialog(page)).toBeHidden();
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.cookie)).toBe(""); // the session cookie is HttpOnly
  await openDariusInLookup(page);
  await expect(page.getByRole("button", { name: "Edit notes" })).toHaveCount(0); // contributors do not edit
  await expect(page.getByRole("tab", { name: "Admin" })).toHaveCount(0);

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("a wrong password is refused", async ({ page }) => {
  await signIn(page, ADMIN.username, "not the password");
  await expect(dialog(page).getByRole("alert")).toHaveText("Wrong username or password.");
});

test("the admin can edit and block accounts", async ({ page }) => {
  // an account to block
  const name = `blockme${Date.now() % 100000}`;
  const made = await page.request.post("/api/signup", {
    data: { username: name, password: "victim password" },
    headers: { Origin: `http://127.0.0.1:${HOSTED}` },
  });
  expect(made.ok()).toBe(true);

  await signIn(page, ADMIN.username, ADMIN.password);
  await expect(page.getByText(`${ADMIN.username} (admin)`)).toBeVisible();
  await openDariusInLookup(page);
  await expect(page.getByRole("button", { name: "Edit notes" })).toBeVisible();
  await page.getByRole("tab", { name: "Data" }).click();
  await expect(page.getByRole("heading", { name: "Update" })).toBeVisible(); // hidden for everyone else

  await page.getByRole("tab", { name: "Admin" }).click();
  const row = page.locator("tbody tr", { hasText: name }).filter({ visible: true });
  await row.getByRole("button", { name: "Block" }).click();
  await expect(row.getByText("Blocked")).toBeVisible();
  await expect(page.locator("tbody tr", { hasText: ADMIN.username }).getByRole("button")).toHaveCount(0); // not yourself

  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, name, "victim password");
  await expect(dialog(page).getByRole("alert")).toHaveText("This account is blocked.");
});

test("the privacy page opens from the footer and names the contact", async ({ page }) => {
  await page.getByRole("contentinfo").getByRole("button", { name: "Privacy" }).click();
  await expect(page.getByRole("heading", { name: "Privacy", level: 2 })).toBeVisible();
  await expect(page.locator("main").getByText("privacy@example.org")).toBeVisible();
});

test("delete your account and its notes", async ({ page }) => {
  const name = `leaver${Date.now() % 100000}`;
  const origin = { Origin: `http://127.0.0.1:${HOSTED}` };
  // page.request shares the page's cookies: this signs the page in
  expect(
    (
      await page.request.post("/api/signup", { data: { username: name, password: "leaver password" }, headers: origin })
    ).ok(),
  ).toBe(true);
  const note = { role: "top", champion: "Darius", opponent: null, text: "Leaving soon", source: "" };
  expect((await page.request.post("/api/notes", { data: note, headers: origin })).ok()).toBe(true);
  await page.reload();

  await page.getByRole("tab", { name: "My account" }).click();
  await expect(page.getByText("Leaving soon")).toBeVisible();
  await page.getByRole("button", { name: "Delete my account…" }).click();
  await page.getByLabel("Your password, to confirm").fill("not my password");
  await page.getByRole("button", { name: "Delete my account", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Wrong password.");

  await page.getByLabel("Your password, to confirm").fill("leaver password");
  await page.getByRole("button", { name: "Delete my account", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Draft" })).toHaveAttribute("aria-selected", "true");

  await signIn(page, name, "leaver password");
  await expect(dialog(page).getByRole("alert")).toHaveText("Wrong username or password.");
  await dialog(page).getByRole("button", { name: "Close" }).click();
  await signIn(page, ADMIN.username, ADMIN.password);
  await page.getByRole("tab", { name: "Admin" }).click();
  await expect(page.getByText("Leaving soon")).toHaveCount(0); // gone from the review queue too
});

test("a link to a page you may not see goes to Draft, without a history entry to come back to", async ({ page }) => {
  const before = await page.evaluate(() => history.length);
  await page.goto("/?x#/admin");
  await expect(page.getByRole("tab", { name: "Draft" })).toHaveAttribute("aria-selected", "true");
  await expect(page).toHaveURL(/#\/draft$/);
  expect(await page.evaluate(() => history.length)).toBe(before + 1); // the link's own entry, now Draft
});

test("a forgotten password: the admin resets it, the user signs in and changes it", async ({ page }) => {
  const name = `forgetful${Date.now() % 100000}`;
  const made = await page.request.post("/api/signup", {
    data: { username: name, password: "lost password" },
    headers: { Origin: `http://127.0.0.1:${HOSTED}` },
  });
  expect(made.ok()).toBe(true);
  await page.request.post("/api/logout", { data: {}, headers: { Origin: `http://127.0.0.1:${HOSTED}` } });
  await page.reload();

  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(dialog(page).getByText("Forgot it? Ask the admin (privacy@example.org)")).toBeVisible();
  await dialog(page).getByRole("button", { name: "Close" }).click();

  await signIn(page, ADMIN.username, ADMIN.password);
  await page.getByRole("tab", { name: /^Admin/ }).click();
  const row = page.locator("tbody tr", { hasText: name }).filter({ visible: true });
  await row.getByRole("button", { name: "Reset password" }).click();
  await row.getByRole("button", { name: "Really reset?" }).click();
  const temp = await page.getByRole("status").filter({ hasText: name }).locator("code").textContent();
  expect(temp).toHaveLength(16);

  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, name, temp!);
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "My account" }).click();
  await page.getByRole("button", { name: "Change password…" }).click();
  await page.getByLabel("Current password").fill("not the one");
  await page.getByLabel("New password").fill("my own password");
  await page.getByRole("button", { name: "Change password", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Wrong password.");
  await page.getByLabel("Current password").fill(temp!);
  await page.getByLabel("New password").fill("my own password");
  await page.getByRole("button", { name: "Change password", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "password was changed" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, name, "my own password");
  await expect(page.getByText(name, { exact: true })).toBeVisible();
});
