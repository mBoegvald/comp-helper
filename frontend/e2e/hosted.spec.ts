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
