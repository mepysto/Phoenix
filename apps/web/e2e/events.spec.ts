import { test, expect } from "@playwright/test";

test.describe("Events Page", () => {
  test("should navigate to events page", async ({ page }) => {
    await page.goto("/events");

    await expect(
      page.getByRole("heading", { name: /Disaster Events/i }),
    ).toBeVisible();
  });

  test("should display event list or loading state", async ({ page }) => {
    await page.goto("/events");

    await expect(
      page.getByText(/earthquake|flood|wildfire|No events found/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test("should have working navigation from home to events", async ({
    page,
  }) => {
    await page.goto("/");

    await page.getByRole("link", { name: /Events/i }).click();

    await expect(page).toHaveURL(/\/events/);
    await expect(
      page.getByRole("heading", { name: /Disaster Events/i }),
    ).toBeVisible();
  });
});
