// Copy Cesium's static runtime (web workers, widgets CSS, assets) to
// public/cesium so the 3D engine can load them from CESIUM_BASE_URL.
// Runs before dev and build; the copy is not committed (see .gitignore).
import { cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const source = join(dirname(require.resolve("cesium/package.json")), "Build", "Cesium");
const target = join(process.cwd(), "public", "cesium");
const version = JSON.parse(readFileSync(require.resolve("cesium/package.json"), "utf8")).version;
const stamp = join(target, ".version");

if (existsSync(stamp) && readFileSync(stamp, "utf8") === version) {
  process.exit(0); // already copied for this version
}
mkdirSync(target, { recursive: true });
for (const dir of ["Workers", "ThirdParty", "Assets", "Widgets"]) {
  cpSync(join(source, dir), join(target, dir), { recursive: true });
}
writeFileSync(stamp, version);
console.log(`Copied Cesium ${version} assets to public/cesium`);
