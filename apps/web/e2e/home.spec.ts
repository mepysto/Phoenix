import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  // The first-visit intro covers the map; dismiss it as a visitor would
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        sessionStorage.setItem("phoenix:intro-seen", "1");
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
    await expect(page.getByText("Layers & Filters")).toBeVisible();
    await expect(page.locator('[class*="maplibregl-map"]')).toBeVisible({
      timeout: 15000,
    });
  });

  test("should toggle between 2D and 3D view", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[class*="maplibregl-map"]', { timeout: 15000 });

    const toggleButton = page.getByRole("button", {
      name: /2D View|3D Globe/i,
    });
    await expect(toggleButton).toBeVisible();

    const initialText = await toggleButton.textContent();
    await toggleButton.click();
    const newText = await toggleButton.textContent();

    expect(newText).not.toBe(initialText);
  });

  test("should toggle basemap between dark and satellite", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[class*="maplibregl-map"]', { timeout: 15000 });

    const basemapButton = page.getByRole("button", { name: /Satellite|Dark/i });
    await expect(basemapButton).toBeVisible();

    await basemapButton.click();

    await expect(basemapButton).toBeVisible();
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
