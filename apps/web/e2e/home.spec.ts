import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  // The first-visit intro covers the map; dismiss it as a visitor would
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        localStorage.setItem("phoenix:intro-seen", "1");
      } catch {
        // storage blocked: the intro test below covers dismissal by click
      }
    });
  });

  test("should load the main page with header and sidebar", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("tab", { name: "Disasters" })).toBeVisible();
    await expect(page.locator('[class*="maplibregl-map"]')).toBeVisible({
      timeout: 15000,
    });
  });

  test("should toggle between 2D and 3D view", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[class*="maplibregl-map"]', { timeout: 15000 });

    // Globe/flat, map/satellite and view modes live in the named "View" menu
    await page.getByRole("button", { name: "View", exact: true }).click();
    const flat = page.getByRole("menuitemradio", { name: "2D View" });
    await expect(flat).toHaveAttribute("aria-checked", "false");
    await flat.click();

    await page.getByRole("button", { name: "View", exact: true }).click();
    await expect(page.getByRole("menuitemradio", { name: "2D View" })).toHaveAttribute("aria-checked", "true");
  });

  test("should toggle basemap between dark and satellite", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[class*="maplibregl-map"]', { timeout: 15000 });

    await page.getByRole("button", { name: "View", exact: true }).click();
    await page.getByRole("menuitemradio", { name: "Satellite" }).click();

    await page.getByRole("button", { name: "View", exact: true }).click();
    await expect(page.getByRole("menuitemradio", { name: "Satellite" })).toHaveAttribute("aria-checked", "true");
  });

  test("should display event markers on the map", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[class*="maplibregl-map"]', { timeout: 15000 });

    await expect(page.getByText(/Active Events:/i)).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe("First-visit intro", () => {
  test("shows once and opens the map", async ({ page }) => {
    await page.goto("/");
    const intro = page.getByRole("dialog", { name: "Phoenix" });
    await expect(intro).toBeVisible();
    await page.getByRole("button", { name: "Open the map" }).click();
    await expect(intro).toBeHidden();
    await page.reload();
    await expect(page.locator('[class*="maplibregl-map"]')).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByRole("dialog", { name: "Phoenix" })).toHaveCount(0);
  });

  test("Escape closes it", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("dialog", { name: "Phoenix" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Phoenix" })).toBeHidden();
  });
});
