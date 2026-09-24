// Copy the map engines' runtime files to public/ so the browser can load them:
// - Cesium's workers/assets/widgets -> public/cesium (CESIUM_BASE_URL)
// - MapLibre 6's worker and its shared chunk -> public/maplibre (setWorkerUrl).
//   Next.js emits the worker without maplibre-gl-shared.mjs, which it imports
//   by relative path, so the map would mount but never load a tile.
// Runs before dev and build; the copies are not committed (see .gitignore).
import { copyFileSync, cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const packageDir = (name) => dirname(require.resolve(`${name}/package.json`));
const versionOf = (name) => JSON.parse(readFileSync(join(packageDir(name), "package.json"), "utf8")).version;

function copyOnce(name, target, copy) {
  const version = versionOf(name);
  const stamp = join(target, ".version");
  if (existsSync(stamp) && readFileSync(stamp, "utf8") === version) return; // already copied
  mkdirSync(target, { recursive: true });
  copy(target);
  writeFileSync(stamp, version);
  console.log(`Copied ${name} ${version} runtime to ${target}`);
}

const publicDir = join(process.cwd(), "public");

copyOnce("cesium", join(publicDir, "cesium"), (target) => {
  const source = join(packageDir("cesium"), "Build", "Cesium");
  for (const dir of ["Workers", "ThirdParty", "Assets", "Widgets"]) {
    cpSync(join(source, dir), join(target, dir), { recursive: true });
  }
});

copyOnce("maplibre-gl", join(publicDir, "maplibre"), (target) => {
  const dist = join(packageDir("maplibre-gl"), "dist");
  for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
    copyFileSync(join(dist, file), join(target, file));
  }
});
