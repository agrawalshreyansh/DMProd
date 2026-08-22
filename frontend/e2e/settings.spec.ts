import { test, expect } from "@playwright/test";

test("sign up, save Gemini key, reload, key still shows as saved", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;

  await page.goto("/signup");
  await page.getByPlaceholder("Email").fill(email);
  await page.getByPlaceholder("Password").fill("correct-horse-battery-staple");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL("/dashboard");

  await page.getByRole("link", { name: "Settings" }).click();
  await expect(page).toHaveURL("/dashboard/settings");
  await expect(page.getByText("Not connected")).toBeVisible();

  await page.getByPlaceholder("Paste your Gemini API key").fill("sk-e2e-test-key");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Connected")).toBeVisible();

  await page.reload();
  await expect(page.getByText("Connected")).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL("/login");

  await page.goto("/dashboard");
  await expect(page).toHaveURL("/login");
});
