import { test, expect } from "@playwright/test";

test("signup, chat, logout flow", async ({ page }) => {
  const email = `user_${Date.now()}@example.com`;
  const password = "password123";

  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign up" }).click();

  await expect(page).toHaveURL("http://127.0.0.1:5173/");

  await page.getByPlaceholder("Ask about flood risk, AQI, traffic, power...").fill("Hello");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Stubbed response from agent.")).toBeVisible({ timeout: 15_000 });

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login/);
});
