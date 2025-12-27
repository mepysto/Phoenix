import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("should navigate between pages", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("banner")).toBeVisible();

    await page.getByRole("link", { name: /Events/i }).click();
    await expect(page).toHaveURL(/\/events/);

    await page.goto("/");
    await expect(page).toHaveURL("/");
  });

  test("should show 404 for unknown routes", async ({ page }) => {
    await page.goto("/unknown-page-xyz");

    await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
  });
});
