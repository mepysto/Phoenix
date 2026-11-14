#!/usr/bin/env node
/**
 * Map rendering benchmark: frame times on the home map while the camera is
 * dragged, for the MapLibre globe (2D/3D) and optionally the Cesium engine.
 *
 *   pnpm --filter web perf:map                     # http://localhost:23100
 *   pnpm --filter web perf:map -- --url https://phoenix.example.org --headed --cesium
 *
 * CHROME_PATH=/path/to/chromium uses a specific browser build.
 *
 * Run it headed on real hardware for numbers that mean something: headless
 * Chromium renders WebGL in software, so its figures are a floor, useful only
 * to compare one commit with another on the same machine.
 */
import { chromium } from "@playwright/test";

const args = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith("--") ? args[i + 1] : fallback;
};
const URL_BASE = arg("url", "http://localhost:23100");
const SECONDS = Number(arg("seconds", "6"));
const HEADED = args.includes("--headed");
const WITH_CESIUM = args.includes("--cesium");

const pct = (sorted, p) => sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))];

/** Record frame intervals in the page while `act` runs */
async function measure(page, act) {
  await page.evaluate(() => {
    window.__frames = [];
    window.__longTasks = 0;
    let last = performance.now();
    const tick = (now) => {
      window.__frames.push(now - last);
      last = now;
      if (window.__recording) requestAnimationFrame(tick);
    };
    window.__recording = true;
    requestAnimationFrame(tick);
    new PerformanceObserver((list) => {
      window.__longTasks += list.getEntries().length;
    }).observe({ type: "longtask", buffered: false });
  });
  await act();
  return page.evaluate(() => {
    window.__recording = false;
    return { frames: window.__frames.slice(1), longTasks: window.__longTasks };
  });
}

/** Drag across the map in slow circles for `seconds` */
async function dragMap(page, seconds) {
  const box = await page.locator("canvas").first().boundingBox();
  if (!box) throw new Error("No map canvas found");
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  const end = Date.now() + seconds * 1000;
  await page.mouse.move(cx, cy);
  await page.mouse.down();
  for (let t = 0; Date.now() < end; t += 0.08) {
    await page.mouse.move(cx + Math.cos(t) * box.width * 0.2, cy + Math.sin(t) * box.height * 0.2);
  }
  await page.mouse.up();
}

function summarise(label, { frames, longTasks }) {
  const sorted = [...frames].sort((a, b) => a - b);
  const median = pct(sorted, 50);
  return {
    view: label,
    frames: frames.length,
    "median fps": +(1000 / median).toFixed(1),
    "p95 frame ms": +pct(sorted, 95).toFixed(1),
    "frames > 50 ms": frames.filter((f) => f > 50).length,
    "long tasks": longTasks,
  };
}

const browser = await chromium.launch({
  headless: !HEADED,
  executablePath: process.env.CHROME_PATH || undefined,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.addInitScript(() => sessionStorage.setItem("phoenix:intro-seen", "1"));
const results = [];

const started = Date.now();
await page.goto(URL_BASE + "/", { waitUntil: "domcontentloaded" });
await page.locator(".maplibregl-canvas").waitFor({ timeout: 60_000 });
await page.waitForTimeout(3000);
const loadMs = Date.now() - started;

results.push(summarise("globe (3D)", await measure(page, () => dragMap(page, SECONDS))));
await page.getByRole("button", { name: /2D View/i }).click();
await page.waitForTimeout(1500);
results.push(summarise("flat map (2D)", await measure(page, () => dragMap(page, SECONDS))));

if (WITH_CESIUM) {
  await page.getByRole("button", { name: /3D engine/i }).click();
  await page.locator(".cesium-widget canvas").waitFor({ timeout: 60_000 });
  await page.waitForTimeout(4000);
  results.push(summarise("Cesium", await measure(page, () => dragMap(page, SECONDS))));
}

const heap = await page.evaluate(() => performance.memory?.usedJSHeapSize ?? null);
await browser.close();

console.log(`\nMap ready in ${(loadMs / 1000).toFixed(1)} s${HEADED ? "" : " (headless, software WebGL)"}`);
console.table(results);
if (heap) console.log(`JS heap after run: ${(heap / 1048576).toFixed(0)} MB`);
